"""Declarative specs for atomgpt.org *app* endpoints exposed as MCP tools.

This is the scalable counterpart to the hand-written curated tools in
``manifest.TOOLS``. atomgpt.org has ~150 FastAPI app routes; reimplementing
each as a Python function in ``agents/functions.py`` does not scale and would
duplicate logic that already lives in the web app. Instead we *declare* each
compute endpoint here and let ``autogen.build_tools`` generate a manifest
``Tool`` whose ``impl`` is a thin HTTP proxy to the existing route (via
``AGAPIClient``). Adding an app tool = append one ``AppSpec`` below.

Only **compute** endpoints belong here. HTML pages, auth, billing, and landing
routes are intentionally excluded — see ``autogen.classify_route`` for the
filter that enforces this when we later auto-discover from the live route table.

This file is the prototype set (one clean JSON endpoint, one path-param GET,
one multipart file upload). Scaling to all apps is "append more AppSpec entries"
or "auto-emit them from the FastAPI OpenAPI" — no changes to the machinery.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ParamLocation = Literal["body", "query", "path", "file"]


@dataclass(frozen=True)
class Param:
    """One tool parameter. Maps to a JSON-schema property AND tells the proxy
    where to put the value in the outgoing HTTP request."""
    type: str = "string"                 # json-schema type: string|number|integer|boolean|array
    description: str = ""
    required: bool = False
    default: Any = None
    location: ParamLocation = "body"     # body -> JSON/Form, query -> ?p=, path -> {p}, file -> multipart
    enum: tuple[str, ...] | None = None
    items: str | None = None             # element type when type == "array"


@dataclass(frozen=True)
class AppSpec:
    """One atomgpt.org compute endpoint, declared once, rendered to a Tool."""
    id: str                              # MCP tool name (unique)
    category: str                        # key into categories.CATEGORIES
    title: str
    description: str                     # what the model reads to decide to call it
    http_path: str                       # may contain {param} path templating
    http_method: Literal["get", "post"] = "post"
    params: dict[str, Param] = field(default_factory=dict)
    timeout_class: Literal["fast", "medium", "slow"] = "medium"
    page_path: str | None = None         # the HTML page (NOT a tool; used by /connect links)


# ─── prototype catalog (3 representative shapes) ─────────────────────────────
APP_SPECS: list[AppSpec] = [
    # 1) Clean JSON predict endpoint — POST body, JSON out.
    AppSpec(
        id="equation_of_state",
        category="thermo",
        title="Equation of state (E–V curve)",
        description=(
            "Compute the energy–volume equation of state for a material using "
            "ALIGNN-FF. Provide either a JARVIS id (jid, e.g. 'JVASP-1002') or a "
            "POSCAR string. Returns fitted bulk modulus and the E–V data."
        ),
        http_method="post",
        http_path="/eos/run",
        params={
            "jid": Param("string", "JARVIS-DFT id, e.g. 'JVASP-1002'.", location="body"),
            "poscar": Param("string", "POSCAR text (alternative to jid).", location="body"),
            "eos": Param("string", "EOS fit form.", default="birch_murnaghan",
                         enum=("birch_murnaghan", "vinet", "murnaghan"), location="body"),
            "n_vol": Param("integer", "Number of volume points.", default=11, location="body"),
            "span": Param("number", "Fractional volume span around equilibrium.",
                          default=0.10, location="body"),
        },
        timeout_class="slow",
        page_path="/eos",
    ),

    # 2) Path-param GET — demonstrates URL templating.
    AppSpec(
        id="elastic_tensor_data",
        category="mechanical",
        title="Elastic tensor for a JARVIS id",
        description=(
            "Fetch the full DFT elastic stiffness tensor (Cij) and derived moduli "
            "for a specific JARVIS-DFT material id."
        ),
        http_method="get",
        http_path="/elastic_tensor/data/{jid}",
        params={
            "jid": Param("string", "JARVIS-DFT id, e.g. 'JVASP-1002'.",
                         required=True, location="path"),
        },
        timeout_class="fast",
        page_path="/elastic_tensor",
    ),

    # 3) Multipart file upload — demonstrates file handling.
    AppSpec(
        id="microscopy_structure_from_image",
        category="characterize",
        title="Predict atomic structure from a STEM image",
        description=(
            "Given a microscopy (STEM) image and a chemical formula, predict the "
            "atomic structure (lattice + coordinates) with MicroscopyGPT. The image "
            "must be supplied as a base64 string or a data: URL."
        ),
        http_method="post",
        http_path="/microscopy/predict",
        params={
            "image": Param("string", "STEM image as base64 (or data: URL).",
                           required=True, location="file"),
            "formula": Param("string", "Chemical formula, e.g. 'Si2O4'.",
                             required=True, location="body"),
        },
        timeout_class="medium",
        page_path="/microscopy",
    ),
]
