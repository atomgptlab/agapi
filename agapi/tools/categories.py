"""Human-readable category metadata for the tool registry.

Used by the /connect docs page and any other UI that wants to group tools.
The `order` field controls display order. Categories without entries are
silently skipped at render time.

To add a category: append a key here and reference it from one or more
Tool(...) entries in manifest.py.
"""

CATEGORIES: dict[str, dict] = {
    "db_query": {
        "label": "Database queries",
        "description": "Search the JARVIS-DFT database (80,000+ DFT-calculated materials).",
        "order": 1,
    },
    "ml_predict": {
        "label": "ML predictions",
        "description": "Property predictions (ALIGNN), force-field relaxation (ALIGNN-FF), tight-binding band structure (SlakoNet).",
        "order": 2,
    },
    "manipulate": {
        "label": "Structure manipulation",
        "description": "Build supercells, substitute atoms, create vacancies. Always relax after editing.",
        "order": 3,
    },
    "characterize": {
        "label": "Characterization (XRD)",
        "description": "Generate theoretical XRD patterns, match experimental patterns to the database, and predict structures from XRD with DiffractGPT.",
        "order": 4,
    },
    "build": {
        "label": "Build (interfaces)",
        "description": "Generate film/substrate heterostructure interfaces.",
        "order": 5,
    },
    "bio": {
        "label": "Bio / proteins",
        "description": "ESMFold protein structure prediction from amino acid sequence.",
        "order": 6,
    },
    # ── auto-generated app categories (see app_specs.py) ────────────────────
    "thermo": {
        "label": "Thermodynamics",
        "description": "Equation of state, phase stability, and thermodynamic properties.",
        "order": 7,
    },
    "mechanical": {
        "label": "Mechanical properties",
        "description": "Elastic tensors, moduli, and mechanical-stability data.",
        "order": 8,
    },
}


def ordered_categories() -> list[str]:
    """Return category keys in display order."""
    return sorted(CATEGORIES, key=lambda c: CATEGORIES[c].get("order", 999))
