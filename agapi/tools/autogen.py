"""Auto-generate MCP tools from declarative ``AppSpec`` entries.

The curated tools in ``manifest.TOOLS`` each have a hand-written Python ``impl``
in ``agents/functions.py``. That is the right shape for the ~28 high-traffic,
agent-critical tools (tuned descriptions, output shaping). It does **not** scale
to atomgpt.org's ~150 app routes.

This module closes that gap: it turns each ``app_specs.AppSpec`` into a manifest
``Tool`` whose ``impl`` is a generated HTTP proxy to the existing FastAPI route.
No per-app Python is written — the web app stays the single implementation, and
the tool is a thin, schema-typed front door over it.

Two public entry points:
  * ``build_tools(specs)``   → ``list[manifest.Tool]`` to merge into the catalog.
  * ``classify_route(info)`` → decide whether a *live* FastAPI route should
                               become a tool (the future auto-discovery filter;
                               this is what excludes HTML pages / auth / billing).

Scaling path: either keep appending ``AppSpec`` entries, or feed the FastAPI
app's OpenAPI through ``classify_route`` + a spec adapter — the registration
machinery below is identical either way.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Any, Callable

from agapi.tools.app_specs import AppSpec, Param


# ─── JSON-schema generation ──────────────────────────────────────────────────
def build_json_schema(spec: AppSpec) -> dict[str, Any]:
    """Build the OpenAI/MCP ``parameters`` object from an AppSpec's params.

    Path, query, body, and file params are all model-supplied, so they all
    appear as properties; ``location`` only affects how the proxy routes the
    value into the HTTP request, not the schema the model sees.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, p in spec.params.items():
        prop: dict[str, Any] = {"type": p.type}
        if p.description:
            prop["description"] = p.description
        if p.enum:
            prop["enum"] = list(p.enum)
        if p.type == "array" and p.items:
            prop["items"] = {"type": p.items}
        if p.default is not None:
            prop["default"] = p.default
        properties[name] = prop
        if p.required:
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


# ─── file handling for multipart endpoints ──────────────────────────────────
def _decode_file_arg(value: str) -> bytes:
    """Accept a base64 string or a ``data:...;base64,XXXX`` URL, return bytes."""
    if not isinstance(value, str):
        raise ValueError("file argument must be a base64 string or data: URL")
    if value.startswith("data:") and "," in value:
        value = value.split(",", 1)[1]
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError(f"could not base64-decode file argument: {e}") from e


def _proxy_multipart(
    client: Any, endpoint: str, data: dict[str, Any], files: dict[str, bytes]
) -> Any:
    """POST a multipart/form-data request, reusing the AGAPIClient's auth/base.

    AGAPIClient.request only speaks JSON/query, so file endpoints get this
    dedicated path. Form fields go in ``data``; decoded file bytes in ``files``.
    """
    import httpx

    url = f"{client.api_base}/{endpoint.lstrip('/')}"
    headers = {"Authorization": f"Bearer {client.api_key}"}
    form = dict(data)
    form.setdefault("APIKEY", client.api_key)
    file_payload = {
        name: (f"{name}.bin", content, "application/octet-stream")
        for name, content in files.items()
    }
    resp = httpx.post(
        url, data=form, files=file_payload, headers=headers, timeout=client.timeout
    )
    resp.raise_for_status()
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        return resp.json()
    return resp.text


# ─── proxy impl factory ──────────────────────────────────────────────────────
def make_proxy_impl(spec: AppSpec) -> Callable[..., Any]:
    """Return the manifest ``Tool.impl`` for an AppSpec.

    Signature matches the AGAPI contract: the MCP handler injects ``api_client``
    and passes the model's arguments as kwargs. We route each declared param to
    its HTTP location (path / query / body / file), apply declared defaults for
    omitted optional params, and call the existing route.
    """

    def impl(api_client: Any = None, **kwargs: Any) -> Any:
        if api_client is None:
            raise RuntimeError(f"{spec.id}: api_client not injected")

        path = spec.http_path
        payload: dict[str, Any] = {}   # body (POST) or query (GET)
        files: dict[str, bytes] = {}

        for name, p in spec.params.items():
            if name in kwargs and kwargs[name] is not None:
                value = kwargs[name]
            elif p.default is not None:
                value = p.default
            else:
                continue  # omitted optional with no default
            if p.location == "path":
                path = path.replace("{" + name + "}", str(value))
            elif p.location == "file":
                files[name] = _decode_file_arg(value)
            else:  # body | query
                payload[name] = value

        endpoint = path.lstrip("/")
        if files:
            return _proxy_multipart(api_client, endpoint, payload, files)
        return api_client.request(
            endpoint, payload, method=spec.http_method.upper()
        )

    impl.__name__ = spec.id
    impl.__doc__ = spec.description
    return impl


# ─── render AppSpecs into manifest Tools ─────────────────────────────────────
def build_tools(specs: list[AppSpec]) -> list:
    """Render each AppSpec into a manifest ``Tool`` (MCP + GPT-Actions ready)."""
    # Deferred import avoids a circular import at module load (manifest imports
    # this module after defining Tool).
    from agapi.tools.manifest import Tool

    tools = []
    for spec in specs:
        tools.append(
            Tool(
                id=spec.id,
                category=spec.category,
                title=spec.title,
                description=spec.description,
                parameters=build_json_schema(spec),
                # File endpoints can't be expressed as a clean GPT-Actions
                # OpenAPI operation, so keep those MCP-only; the rest get both.
                surfaces=(("mcp",) if any(p.location == "file"
                          for p in spec.params.values())
                          else ("mcp", "gpt_actions")),
                http_method=spec.http_method,
                http_path=spec.http_path,
                impl=make_proxy_impl(spec),
                timeout_class=spec.timeout_class,
                notes="auto-generated from AppSpec",
            )
        )
    return tools


# ─── future auto-discovery: classify live FastAPI routes ─────────────────────
@dataclass(frozen=True)
class RouteInfo:
    """Minimal description of a FastAPI route, for the inclusion filter."""
    path: str
    method: str                      # "GET" | "POST" | ...
    response_class: str = ""         # e.g. "HTMLResponse", "JSONResponse", ""
    has_body_model: bool = False     # POST with a Pydantic body
    has_params: bool = False         # any path/query params


# Prefixes that are never tools (pages, auth, infra, docs, the MCP itself).
_EXCLUDED_PREFIXES = (
    "/auth", "/billing", "/quota", "/privacy", "/terms", "/docs", "/openapi",
    "/apps", "/connect", "/static", "/oauth", "/mcp", "/error", "/startup",
    "/gpt-actions", "/.well-known", "/health",
)
_PAGE_RESPONSES = ("HTMLResponse", "FileResponse", "RedirectResponse", "Response")


def classify_route(info: RouteInfo) -> tuple[bool, str]:
    """Decide whether a live route should become an MCP tool.

    Returns ``(include, reason)``. This is what makes auto-discovery safe:
    HTML pages, auth, billing, and parameterless landing routes are dropped;
    JSON compute endpoints (POST-with-body, or GET-with-params) are kept.
    """
    path = info.path
    method = info.method.upper()
    for pre in _EXCLUDED_PREFIXES:
        if path == pre or path.startswith(pre + "/") or path.startswith(pre):
            return False, f"excluded prefix {pre}"
    if info.response_class in _PAGE_RESPONSES:
        return False, f"page/non-JSON response ({info.response_class})"
    if method == "GET" and not info.has_params:
        return False, "GET with no params (likely a landing page)"
    if method == "POST" and not info.has_body_model and not info.has_params:
        return False, "POST with no inputs"
    if method not in ("GET", "POST"):
        return False, f"unsupported method {method}"
    return True, "compute endpoint"
