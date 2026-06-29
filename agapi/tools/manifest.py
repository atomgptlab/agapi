"""Tool registry — single source of truth for what AGAPI exposes to LLMs.

Each `Tool(...)` declaration carries everything every downstream surface
needs to register, document, or call the tool:

  - `id` / `description` / `parameters`        → MCP + GPT Actions schemas
  - `http_method` / `http_path`                → OpenAPI generator
  - `impl`                                      → MCP server function dispatch
  - `surfaces`                                  → which surfaces expose it
  - `category`                                  → /connect grouping + docs
  - `timeout_class`                             → ChatGPT 45s exclusion logic

Adding a new tool = append one entry. Removing or renaming = touch only this
file. Surfaces never hard-code names again.

`parameters` is looked up from `agapi.agents.schema.TOOLS_SCHEMA` for the 16
tools that already have entries there — keeps schemas in one place during
the initial migration. New tools without a schema.py entry can pass
`parameters={...}` inline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from agapi.agents import functions as agapi_functions
from agapi.agents.schema import TOOLS_SCHEMA

# Index schema.py by tool name so manifest entries can pull parameters by id.
_SCHEMA_BY_NAME: dict[str, dict] = {
    item["function"]["name"]: item["function"]
    for item in TOOLS_SCHEMA
}


def _params_for(tool_id: str) -> dict[str, Any]:
    """Look up the parameter schema from schema.py. Empty dict if not present."""
    spec = _SCHEMA_BY_NAME.get(tool_id)
    if not spec:
        return {"type": "object", "properties": {}}
    return spec.get("parameters", {"type": "object", "properties": {}})


def _desc_for(tool_id: str, fallback: str = "") -> str:
    spec = _SCHEMA_BY_NAME.get(tool_id)
    if not spec:
        return fallback
    return spec.get("description", fallback)


Surface = Literal["mcp", "gpt_actions", "public_http"]
TimeoutClass = Literal["fast", "medium", "slow"]
# fast    : <1s  — DB lookups, schema fetches
# medium  : <30s — ALIGNN forward, XRD generate, supercell, etc.
# slow    : ≥30s — ALIGNN-FF relaxation, SlakoNet, protein folding
#                  (excluded from ChatGPT due to 45s edge timeout)


@dataclass(frozen=True)
class Tool:
    # ── identity ────────────────────────────────────────────────────────
    id: str                                  # internal id, also MCP tool name
    category: str                            # key into categories.CATEGORIES
    title: str                               # human-readable label

    # ── description & params ────────────────────────────────────────────
    description: str = ""                    # auto-filled from schema.py if blank
    parameters: dict = field(default_factory=dict)  # OpenAI tool-call format

    # ── distribution ────────────────────────────────────────────────────
    surfaces: tuple[Surface, ...] = ("mcp", "gpt_actions", "public_http")

    # ── HTTP backing (drives OpenAPI generation) ────────────────────────
    http_method: Literal["get", "post"] = "post"
    http_path: str = ""                      # e.g. "/jarvis_dft/query"

    # ── Python impl (drives MCP dispatch) ───────────────────────────────
    impl: Callable | None = None

    # ── operational hints ───────────────────────────────────────────────
    timeout_class: TimeoutClass = "medium"
    max_atoms: int | None = None
    notes: str = ""                          # caveats shown in docs


# ─── the catalog ────────────────────────────────────────────────────────────
# 16 tools, mirroring agapi.mcp.server.FUNCTION_REGISTRY. Order here is the
# order they appear in /connect and in the SYSTEM_PROMPT tool catalog.

TOOLS: list[Tool] = [
    # ── Database queries ────────────────────────────────────────────────
    # Five logical tools, all backed by POST /jarvis_dft/query. The MCP
    # server registers them as five distinct named tools (the model picks
    # which one to call based on intent); the GPT Actions OpenAPI collapses
    # them to one operation because OpenAPI keys ops by (path, method).
    Tool(
        id="query_by_formula",
        category="db_query",
        title="Query by formula",
        description=_desc_for("query_by_formula"),
        parameters=_params_for("query_by_formula"),
        http_method="post",
        http_path="/jarvis_dft/query",
        impl=agapi_functions.query_by_formula,
        timeout_class="fast",
    ),
    Tool(
        id="query_by_elements",
        category="db_query",
        title="Query by elements",
        description=_desc_for("query_by_elements"),
        parameters=_params_for("query_by_elements"),
        http_method="post",
        http_path="/jarvis_dft/query",
        impl=agapi_functions.query_by_elements,
        timeout_class="fast",
    ),
    Tool(
        id="query_by_jid",
        category="db_query",
        title="Query by JARVIS ID",
        description=_desc_for("query_by_jid"),
        parameters=_params_for("query_by_jid"),
        http_method="post",
        http_path="/jarvis_dft/query",
        impl=agapi_functions.query_by_jid,
        timeout_class="fast",
    ),
    Tool(
        id="query_by_property",
        category="db_query",
        title="Query by property range",
        description=_desc_for("query_by_property"),
        parameters=_params_for("query_by_property"),
        http_method="post",
        http_path="/jarvis_dft/query",
        impl=agapi_functions.query_by_property,
        timeout_class="fast",
    ),
    Tool(
        id="find_extreme",
        category="db_query",
        title="Find extreme value",
        description=_desc_for("find_extreme"),
        parameters=_params_for("find_extreme"),
        http_method="post",
        http_path="/jarvis_dft/query",
        impl=agapi_functions.find_extreme,
        timeout_class="fast",
    ),

    # ── ML predictions ──────────────────────────────────────────────────
    Tool(
        id="alignn_predict",
        category="ml_predict",
        title="ALIGNN property prediction",
        description=_desc_for("alignn_predict"),
        parameters=_params_for("alignn_predict"),
        http_method="get",
        http_path="/alignn/query",
        impl=agapi_functions.alignn_predict,
        timeout_class="fast",
        max_atoms=50,
        notes="MBJ bandgap is more accurate than OptB88vdW for semiconductors.",
    ),
    Tool(
        id="alignn_ff_relax",
        category="ml_predict",
        title="ALIGNN-FF relaxation",
        description=_desc_for("alignn_ff_relax"),
        parameters=_params_for("alignn_ff_relax"),
        http_method="post",
        http_path="/alignn_ff/query",
        impl=agapi_functions.alignn_ff_relax,
        timeout_class="slow",  # ⚠ excluded from ChatGPT (45s cap)
        max_atoms=50,
        notes="Always relax after substitution/vacancy. May exceed 45s for big cells.",
    ),
    Tool(
        id="slakonet_bandstructure",
        category="ml_predict",
        title="SlakoNet band structure",
        description=_desc_for("slakonet_bandstructure"),
        parameters=_params_for("slakonet_bandstructure"),
        http_method="post",
        http_path="/slakonet/bandstructure",
        impl=agapi_functions.slakonet_bandstructure,
        timeout_class="slow",
        max_atoms=50,
        notes="Tight-binding overestimates bandgaps; prefer ALIGNN-MBJ.",
    ),
    Tool(
        id="battery_predict",
        category="ml_predict",
        title="Battery cathode voltage profile",
        description=_desc_for("battery_predict"),
        parameters=_params_for("battery_predict"),
        http_method="post",
        http_path="/battery/predict",
        impl=agapi_functions.battery_predict,
        timeout_class="slow",  # ⚠ sequential ALIGNN-FF energies; may exceed 45s
        notes="Structure must contain the intercalating ion (e.g. LiCoO2). Pass jid or poscar.",
    ),

    # ── Structure manipulation ──────────────────────────────────────────
    Tool(
        id="make_supercell",
        category="manipulate",
        title="Make supercell",
        description=_desc_for("make_supercell"),
        parameters=_params_for("make_supercell"),
        http_method="post",
        http_path="/structure_visualizer/supercell",
        impl=agapi_functions.make_supercell,
        timeout_class="fast",
        notes="Always supercell BEFORE creating vacancies/substitutions.",
    ),
    Tool(
        id="substitute_atom",
        category="manipulate",
        title="Substitute atom",
        description=_desc_for("substitute_atom"),
        parameters=_params_for("substitute_atom"),
        http_method="post",
        http_path="/structure_visualizer/substitution",
        impl=agapi_functions.substitute_atom,
        timeout_class="fast",
        notes="After substitution: relax with alignn_ff_relax.",
    ),
    Tool(
        id="create_vacancy",
        category="manipulate",
        title="Create vacancy",
        description=_desc_for("create_vacancy"),
        parameters=_params_for("create_vacancy"),
        http_method="post",
        http_path="/structure_visualizer/vacancy",
        impl=agapi_functions.create_vacancy,
        timeout_class="fast",
        notes="After vacancy: relax with alignn_ff_relax — atoms rearrange.",
    ),

    # ── XRD characterization ────────────────────────────────────────────
    Tool(
        id="diffractgpt_predict",
        category="characterize",
        title="DiffractGPT (XRD → structure)",
        description=_desc_for("diffractgpt_predict"),
        parameters=_params_for("diffractgpt_predict"),
        http_method="get",
        http_path="/diffractgpt/query",
        impl=agapi_functions.diffractgpt_predict,
        timeout_class="medium",
    ),
    Tool(
        id="xrd_match",
        category="characterize",
        title="Match XRD to JARVIS-DFT",
        description=_desc_for("xrd_match"),
        parameters=_params_for("xrd_match"),
        http_method="post",
        http_path="/xrd/analyze",
        impl=agapi_functions.xrd_match,
        timeout_class="medium",
    ),
    Tool(
        id="generate_xrd_pattern",
        category="characterize",
        title="Generate XRD pattern from POSCAR",
        description=_desc_for("generate_xrd_pattern"),
        parameters=_params_for("generate_xrd_pattern"),
        http_method="post",
        http_path="/xrd/generate",
        impl=agapi_functions.generate_xrd_pattern,
        timeout_class="fast",
    ),

    # ── Heterostructures ────────────────────────────────────────────────
    Tool(
        id="generate_interface",
        category="build",
        title="Build heterostructure interface",
        description=_desc_for("generate_interface"),
        parameters=_params_for("generate_interface"),
        http_method="get",
        http_path="/generate_interface",
        impl=agapi_functions.generate_interface,
        timeout_class="medium",
    ),

    # ── Protein folding ─────────────────────────────────────────────────
    Tool(
        id="protein_fold",
        category="bio",
        title="ESMFold protein structure",
        description=_desc_for("protein_fold"),
        parameters=_params_for("protein_fold"),
        http_method="get",
        http_path="/protein_fold/query",
        impl=agapi_functions.protein_fold,
        timeout_class="slow",
        notes="10-400 residues, standard 20 amino acids. May exceed 45s for long sequences.",
    ),
]


# ─── auto-generated app tools (scalable long-tail) ──────────────────────────
# The curated tools above are hand-written, native Python impls. The app
# endpoints below are *declared* in app_specs.py and rendered to Tools by
# autogen.build_tools (each impl is a thin HTTP proxy to the existing FastAPI
# route). Add more by appending an AppSpec there — or by auto-emitting specs
# from the live FastAPI OpenAPI — with zero changes to this file or server.py.
from agapi.tools.autogen import build_tools as _build_app_tools  # noqa: E402
from agapi.tools.app_specs import APP_SPECS as _APP_SPECS  # noqa: E402

TOOLS = TOOLS + _build_app_tools(_APP_SPECS)


# ─── helpers used by every renderer ─────────────────────────────────────────

_BY_ID: dict[str, Tool] = {t.id: t for t in TOOLS}


def by_id(tool_id: str) -> Tool | None:
    """Look up a tool by id."""
    return _BY_ID.get(tool_id)


def for_surface(surface: Surface) -> list[Tool]:
    """Return tools that should appear on the given surface, in catalog order."""
    return [t for t in TOOLS if surface in t.surfaces]
