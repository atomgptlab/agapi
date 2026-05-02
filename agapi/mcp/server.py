"""
agapi.mcp.server — Model Context Protocol server exposing the AGAPI
materials-science toolkit as MCP tools.

So Claude (and any other MCP client) can call the same 16 functions that
power AGAPIAgent, without reinventing schemas, HTTP clients, or system
prompts.

Design principle: zero duplication. We import:
  - `agapi.agents.functions.*`        → the actual tool implementations
  - `agapi.agents.schema.TOOLS_SCHEMA` → authoritative OpenAI-format JSON schemas
  - `agapi.agents.client.AGAPIClient`  → HTTP client with auth + retry
  - `agapi.agents.agent.SYSTEM_PROMPT` → battle-tested system prompt (passed
    to MCP as server `instructions`, so Claude inherits AGAPI's workflow
    guidance, bandgap-reporting rules, and tool-chaining logic)

Run:
    pip install "agapi[mcp]"
    export AGAPI_KEY=sk-...

    python -m agapi.mcp                              # stdio (Claude Desktop)
    uvicorn agapi.mcp.server:app --port 8765         # remote Streamable HTTP
    agapi-mcp                                        # console script (stdio)
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.tools.base import Tool
from mcp.server.fastmcp.utilities.func_metadata import (
    ArgModelBase,
    FuncMetadata,
)

# ─── reuse everything from agapi ─────────────────────────────────────────────
import agapi
from agapi.agents import functions as agapi_functions
from agapi.agents.client import AGAPIClient
from agapi.agents.config import AgentConfig
from agapi.agents.schema import TOOLS_SCHEMA
from agapi.agents.agent import SYSTEM_PROMPT

# Near the top of the file, after imports
from contextvars import ContextVar

# Per-request client, set by the Open WebUI MCP auth middleware. When unset
# (e.g. running under `python -m agapi.mcp` in stdio mode), tool handlers
# fall back to the module-level _agapi_client built from env vars.
_request_client: ContextVar[AGAPIClient | None] = ContextVar(
    "_request_client", default=None
)

# ─── config ──────────────────────────────────────────────────────────────────
API_KEY = os.environ.get("AGAPI_KEY")  # or AgentConfig.DEFAULT_API_KEY
# print("API_KEY",API_KEY)
API_BASE = os.environ.get("AGAPI_BASE") or AgentConfig.API_BASE
# print("API_BASE",API_BASE)
TIMEOUT = int(os.environ.get("AGAPI_TIMEOUT", AgentConfig.DEFAULT_TIMEOUT))

# Single shared AGAPI client, injected into every call as `api_client=...`
# (matches the contract in AGAPIAgent._execute_function)
_agapi_client = AGAPIClient(
    api_key=API_KEY, api_base=API_BASE, timeout=TIMEOUT
)

# ─── MCP server ──────────────────────────────────────────────────────────────
# AGAPI's SYSTEM_PROMPT becomes the MCP server `instructions`. Claude surfaces
# this to the model when tools are loaded, so the same workflow guidance that
# AGAPIAgent depends on flows through to Claude automatically.
mcp = FastMCP(name="atomgpt", instructions=SYSTEM_PROMPT)

# Configure DNS-rebinding protection for the streamable_http transport.
# When this app is mounted behind cloudflared at atomgpt.org, the inbound
# Host header is "atomgpt.org" — without this allowlist, FastMCP's
# transport_security middleware rejects it with 421 "Invalid Host header".
# Bearer-token auth in the parent middleware already gates the endpoint, so
# this is purely about teaching MCP which Host values to accept.
from mcp.server.transport_security import TransportSecuritySettings as _TSS
mcp.settings.transport_security = _TSS(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "atomgpt.org",
        "www.atomgpt.org",
        "127.0.0.1",
        "127.0.0.1:8080",
        "127.0.0.1:8765",
        "localhost",
        "localhost:8080",
        "localhost:8765",
    ],
    allowed_origins=[
        "https://atomgpt.org",
        "https://www.atomgpt.org",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8765",
        "http://127.0.0.1:8765",
    ],
)

# ─── function registry ───────────────────────────────────────────────────────
# Mirrors AGAPIAgent._execute_function exactly. Explicit (not dir()-based) so
# internal helpers added to functions.py never leak out as tools.
FUNCTION_REGISTRY: dict[str, Callable] = {
    "query_by_formula": agapi_functions.query_by_formula,
    "query_by_elements": agapi_functions.query_by_elements,
    "query_by_jid": agapi_functions.query_by_jid,
    "query_by_property": agapi_functions.query_by_property,
    "find_extreme": agapi_functions.find_extreme,
    "alignn_predict": agapi_functions.alignn_predict,
    "alignn_ff_relax": agapi_functions.alignn_ff_relax,
    "slakonet_bandstructure": agapi_functions.slakonet_bandstructure,
    "diffractgpt_predict": agapi_functions.diffractgpt_predict,
    "xrd_match": agapi_functions.xrd_match,
    "generate_xrd_pattern": agapi_functions.generate_xrd_pattern,
    "generate_interface": agapi_functions.generate_interface,
    "make_supercell": agapi_functions.make_supercell,
    "substitute_atom": agapi_functions.substitute_atom,
    "create_vacancy": agapi_functions.create_vacancy,
    "protein_fold": agapi_functions.protein_fold,
}

# Index AGAPI's OpenAI-format schemas by function name.
# TOOLS_SCHEMA items look like:
#   {"type": "function",
#    "function": {"name": ..., "description": ..., "parameters": {...}}}
_SCHEMA_BY_NAME: dict[str, dict] = {
    item["function"]["name"]: item["function"] for item in TOOLS_SCHEMA
}


# ─── response-size guard ─────────────────────────────────────────────────────
# Claude caps MCP tool responses at ~25K tokens. AGAPI results can blow past
# that (full materials lists, base64 band-structure PNGs, long POSCARs). We
# mirror the truncation logic from AGAPIAgent.query so nothing accidentally
# bloats Claude's context.

_MAX_RESULT_CHARS = 20_000
_PRIORITY_KEYS = (
    "status",
    "message",
    "error",
    "formula",
    "jid",
    "num_atoms",
    "band_gap_eV",
    "vbm_eV",
    "cbm_eV",
    "relaxed_poscar",
    "modified_poscar",
    "supercell_poscar",
    "poscar",
    "peaks",
    "num_peaks_found",
    "num_peaks_reported",
    "description",
    "wavelength",
    "pdb_structure",
    "materials",
    "results",
    "total",
)
_POSCAR_KEYS = (
    "relaxed_poscar",
    "modified_poscar",
    "supercell_poscar",
    "poscar",
)


def _truncate_poscar(text: str, head: int = 10, tail: int = 5) -> str:
    lines = str(text).splitlines()
    if len(lines) <= head + tail + 1:
        return text
    return "\n".join(lines[:head] + ["... (truncated) ..."] + lines[-tail:])


def _shrink(result: Any) -> Any:
    """Fit an AGAPI result comfortably in an MCP tool response."""
    if not isinstance(result, dict):
        return result

    raw = json.dumps(result, default=str)
    if len(raw) <= _MAX_RESULT_CHARS:
        if "image_base64" in result:
            # base64 PNGs waste tokens with no benefit in chat
            result = {
                **result,
                "image_base64": "<omitted — view on atomgpt.org>",
            }
        return result

    shrunk: dict[str, Any] = {
        k: result[k] for k in _PRIORITY_KEYS if k in result
    }

    for k in _POSCAR_KEYS:
        if (
            k in shrunk
            and isinstance(shrunk[k], str)
            and len(shrunk[k]) > 2000
        ):
            shrunk[k] = _truncate_poscar(shrunk[k])

    if (
        isinstance(shrunk.get("materials"), list)
        and len(shrunk["materials"]) > 25
    ):
        full = shrunk["materials"]
        shrunk["materials"] = full[:25]
        shrunk["_note"] = (
            f"Showing first 25 of {len(full)} materials. "
            "Narrow your query (extra filters, property ranges) to see more."
        )

    if "image_base64" in result:
        shrunk["image_base64"] = "<omitted — view on atomgpt.org>"

    return shrunk


# ─── passthrough validation ──────────────────────────────────────────────────
# FastMCP normally builds a pydantic model from the Python function signature
# and validates incoming arguments against it. That doesn't work for AGAPI
# tools because our handlers use `**kwargs` — pydantic interprets this as a
# required field literally named `kwargs`, which breaks every call.
#
# The authoritative schema already lives in TOOLS_SCHEMA and gets sent to the
# client (Claude). JSON-schema validation happens on the client side before
# the request ever reaches us. So we bypass server-side pydantic validation
# entirely and pass the raw dict straight through to the AGAPI function.


class _PassthroughArgs(ArgModelBase):
    """Stand-in for the pydantic arg-model FastMCP normally builds.

    Inherits from ArgModelBase (a pydantic BaseModel subclass) to satisfy
    FuncMetadata's type check on `arg_model`. The actual validation is
    bypassed because we override `call_fn_with_arg_validation` in
    `_PassthroughMetadata` below — model_validate is never called on this
    class in practice.

    `model_config = {"extra": "allow"}` means pydantic will accept any keys
    without raising, which keeps things safe even on the unlikely code path
    where someone calls model_validate directly.
    """

    model_config = {"extra": "allow"}


class _PassthroughMetadata(FuncMetadata):
    """FuncMetadata that skips pydantic validation for AGAPI tools.

    AGAPI functions take arbitrary kwargs documented by TOOLS_SCHEMA; we pass
    the client's dict straight through without re-validating. Malformed input
    surfaces as exceptions inside the function itself, which our wrapper
    catches and returns as a clean error dict.
    """

    model_config = {"arbitrary_types_allowed": True}

    async def call_fn_with_arg_validation(
        self,
        fn,
        fn_is_async,
        arguments_to_validate,
        arguments_to_pass_directly,
    ):
        merged = dict(arguments_to_pass_directly or {})
        if isinstance(arguments_to_validate, dict):
            merged.update(arguments_to_validate)
        if fn_is_async:
            return await fn(**merged)
        return fn(**merged)


# ─── handler factory ─────────────────────────────────────────────────────────
def _make_mcp_handler(func: Callable, name: str) -> Callable:
    """Wrap an AGAPI function as an async MCP tool handler.

    AGAPI functions are synchronous and can block on HTTP calls lasting
    minutes (ALIGNN-FF relaxation, SlakoNet band structure, protein folding).
    We run them in a worker thread via anyio so the MCP event loop stays
    responsive and other tool calls can proceed concurrently.
    """

    async def handler(**kwargs: Any) -> dict[str, Any]:
        # kwargs["api_client"] = _agapi_client
        kwargs["api_client"] = _request_client.get() or _agapi_client
        try:
            result = await anyio.to_thread.run_sync(lambda: func(**kwargs))
        except Exception as e:
            return {"error": f"{name} failed: {type(e).__name__}: {e}"}
        return _shrink(result)

    handler.__name__ = name
    handler.__doc__ = (func.__doc__ or "").strip() or _SCHEMA_BY_NAME.get(
        name, {}
    ).get("description", "")
    return handler


# ─── tool registration ───────────────────────────────────────────────────────
def _register_all_tools() -> list[str]:
    """Build and register one Tool per AGAPI function.

    We build Tool objects directly instead of using mcp.add_tool() so we can
    inject our passthrough FuncMetadata. The authoritative schema comes from
    AGAPI's TOOLS_SCHEMA — never from Python signature introspection.
    """
    registered: list[str] = []
    for name, func in FUNCTION_REGISTRY.items():
        spec = _SCHEMA_BY_NAME.get(name)
        if spec is None:
            print(f"⚠ skipping {name}: not in TOOLS_SCHEMA")
            continue

        handler = _make_mcp_handler(func, name)
        parameters = spec.get(
            "parameters", {"type": "object", "properties": {}}
        )

        tool = Tool(
            fn=handler,
            name=name,
            title=None,
            description=spec.get("description", ""),
            parameters=parameters,
            fn_metadata=_PassthroughMetadata(arg_model=_PassthroughArgs),
            is_async=True,
            context_kwarg=None,
            annotations=None,
        )
        mcp._tool_manager._tools[name] = tool  # type: ignore[attr-defined]
        registered.append(name)
    return registered


_REGISTERED = _register_all_tools()
print(
    f"✓ atomgpt-mcp {agapi.__version__} registered "
    f"{len(_REGISTERED)} tools: {', '.join(_REGISTERED)}"
)


# ─── entry points ────────────────────────────────────────────────────────────
# Remote connector (Claude web / mobile):  uvicorn agapi.mcp.server:app --port 8765
# Local stdio (Claude Desktop):             python -m agapi.mcp
#
# Serve the JSON-RPC endpoint at the app root ("/"). When this app is mounted
# at /mcp by OpenWebUI, the final public URL is atomgpt.org/mcp (not /mcp/mcp).
mcp.settings.streamable_http_path = "/"
app = mcp.streamable_http_app()

# Older FastMCP versions ignore `mcp.settings.streamable_http_path` and leave
# the streamable_http endpoint at `/mcp`. When this app is mounted under
# `/mcp` by OpenWebUI, that places the real endpoint at `/mcp/mcp`. Patch the
# route in-place so it always serves at `/`, regardless of FastMCP version.
import re as _re

for _r in app.routes:
    if getattr(_r, "path", None) == "/mcp":
        _r.path = "/"
        _r.path_regex = _re.compile("^/$")
        _r.path_format = "/"
        break

if __name__ == "__main__":
    mcp.run()
