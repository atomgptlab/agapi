"""
Minimal but complete integration coverage for all
agapi.agents.functions

Real HTTP calls.
Requires AGAPI_KEY.

Run:
    pytest -v -s test_functions_full_minimal.py
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from agapi.agents.client import AGAPIClient
from agapi.agents.functions import *
import time
# pytest.skip("Temporarily disabled", allow_module_level=True)

# ---------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    key = os.getenv("AGAPI_KEY")
    if not key:
        pytest.skip("AGAPI_KEY not set")
    return AGAPIClient(api_key=key)


# ---------------------------------------------------------------------
# Primitive structures (≤10 atoms)
# ---------------------------------------------------------------------

SI_PRIM = """\
Si
1.0
0 2.734 2.734
2.734 0 2.734
2.734 2.734 0
Si
2
direct
0 0 0
0.25 0.25 0.25
"""

GAAS_PRIM = """\
GaAs
1.0
0 2.875 2.875
2.875 0 2.875
2.875 2.875 0
Ga As
1 1
direct
0 0 0
0.25 0.25 0.25
"""

SI_XRD = """\
28.44 1.00
47.30 0.55
56.12 0.30
"""

LICOO2_PRIM = """\
LiO2Co
1.0
2.719 -0.003 4.091
1.234 2.423 4.091
-0.004 -0.003 4.913
Li Co O
1 1 2
Cartesian
1.974 1.209 6.548
0.0 0.0 0.0
1.027 0.629 3.405
2.922 1.789 9.690
"""


# =====================================================================
# DATABASE
# =====================================================================

def test_query_by_formula(client):
    time.sleep(4)
    r = query_by_formula("Si", client)
    assert "error" not in r


def test_query_by_jid(client):
    time.sleep(4)
    r = query_by_jid("JVASP-1002", client)
    assert "error" not in r
    assert isinstance(r.get("POSCAR"), str)


def test_query_by_elements(client):
    time.sleep(4)
    r = query_by_elements("Si", client)
    assert "error" not in r


def test_query_by_property(client):
    time.sleep(4)
    r = query_by_property("bandgap", 0.1, 3.0,
                          elements="Si", api_client=client)
    assert "error" not in r


def test_find_extreme(client):
    time.sleep(4)
    r = find_extreme("bulk modulus", True,
                     elements="Si", api_client=client)
    assert "error" not in r


# =====================================================================
# ALIGNN + FF
# =====================================================================

def test_alignn_predict(client):
    time.sleep(4)
    r = alignn_predict(jid="JVASP-1002", api_client=client)
    assert r.get("status") == "success"


#def test_alignn_ff_relax(client):
#    time.sleep(4)
#    r = alignn_ff_relax(SI_PRIM, api_client=client)
#    assert r.get("status") == "success"


def test_alignn_ff_single_point(client):
    time.sleep(4)
    r = alignn_ff_single_point(SI_PRIM, api_client=client)
    assert "energy_eV" in r

"""
def test_alignn_ff_optimize(client):
    r = alignn_ff_optimize(SI_PRIM, steps=5, api_client=client)
    assert "final_poscar" in r


def test_alignn_ff_md(client):
    r = alignn_ff_md(SI_PRIM, steps=5, api_client=client)
    assert r.get("steps_completed") == 5

"""

# =====================================================================
# BATTERY
# =====================================================================

def test_battery_predict_field_mapping():
    """Mock test: verifies response fields are mapped correctly without a live API call."""
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "success": True,
        "formula": "LiCoO2",
        "element": "Li",
        "spacegroup": "R-3m",
        "n_steps": 4,
        "compositions": [0.0, 0.25, 0.5, 0.75, 1.0],
        "voltages": [4.1, 3.9, 3.8, 3.7],
        "energies": [-10.1, -9.8, -9.5, -9.1],
        "gravimetric_capacity": 137.0,
        "volumetric_capacity": 710.0,
        "density": 5.18,
        "molar_mass": 97.87,
        "charge": 1,
        "result_text": "LiCoO2 cathode summary...",
    }

    mock_client = MagicMock()
    mock_client.api_base = "https://atomgpt.org"
    mock_client.api_key = "sk-test"
    mock_client.timeout = 120.0

    with patch("httpx.post", return_value=fake_response) as mock_post:
        r = battery_predict(LICOO2_PRIM, element="Li", api_client=mock_client)

    mock_post.assert_called_once()
    assert r["status"] == "success"
    assert r["formula"] == "LiCoO2"
    assert r["gravimetric_capacity"] == 137.0
    assert r["voltages"] == [4.1, 3.9, 3.8, 3.7]
    assert r["n_steps"] == 4


def test_battery_predict(client):
    time.sleep(4)
    r = battery_predict(LICOO2_PRIM, element="Li", api_client=client)
    assert r.get("status") == "success"
    assert isinstance(r.get("gravimetric_capacity"), (int, float))
    assert isinstance(r.get("voltages"), list) and len(r["voltages"]) > 0


# =====================================================================
# BANDSTRUCTURE
# =====================================================================

def test_slakonet_bandstructure(client):
    time.sleep(4)
    r = slakonet_bandstructure(SI_PRIM, api_client=client)
    assert r.get("status") == "success"


# =====================================================================
# INTERFACE
# =====================================================================

def test_generate_interface(client):
    time.sleep(4)
    r = generate_interface(SI_PRIM, GAAS_PRIM, api_client=client)
    assert r.get("status") == "success"


# =====================================================================
# STRUCTURE OPS (local)
# =====================================================================

def test_make_supercell():
    time.sleep(4)
    r = make_supercell(SI_PRIM, [2, 2, 1])
    assert r["supercell_atoms"] > r["original_atoms"]


def test_substitute_atom():
    time.sleep(4)
    r = substitute_atom(GAAS_PRIM, "Ga", "Al", 1)
    assert "Al" in r["new_formula"]


def test_create_vacancy():
    time.sleep(4)
    r = create_vacancy(GAAS_PRIM, "Ga", 1)
    assert r["new_atoms"] == r["original_atoms"] - 1


def test_generate_xrd_pattern():
    time.sleep(4)
    r = generate_xrd_pattern(SI_PRIM)
    assert r["formula"] == "Si"


# =====================================================================
# DIFFRACTGPT
# =====================================================================

def test_diffractgpt_predict(client):
    time.sleep(4)
    r = diffractgpt_predict("Si", "28.4(1.0),47.3(0.49)", client)
    assert isinstance(r, dict)


# =====================================================================
# PROTEIN
# =====================================================================

def test_protein_fold_validation(client):
    time.sleep(4)
    r = protein_fold("MKTAY", api_client=client)
    assert "error" in r


"""
def test_openfold_predict(client):
    seq = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVK"
    r = openfold_predict(seq, api_client=client)
    assert isinstance(r, dict)

"""

# =====================================================================
# PXRD / XRD
# =====================================================================

def test_pxrd_match(client):
    time.sleep(4)
    r = pxrd_match("Si", SI_XRD, api_client=client)
    assert isinstance(r, dict)


def test_xrd_analyze(client):
    time.sleep(4)
    r = xrd_analyze("Si", SI_XRD, api_client=client)
    assert isinstance(r, dict)

"""
def test_microscopygpt_analyze(client):
    r = microscopygpt_analyze("HRTEM image of Si lattice", api_client=client)
    assert isinstance(r, dict)
"""


# =====================================================================
# EXTERNAL DATABASES
# =====================================================================

def test_query_mp(client):
    r = query_mp("Si", limit=2, api_client=client)
    assert isinstance(r, dict)

"""
def test_query_oqmd(client):
    time.sleep(4)
    r = query_oqmd("Si", limit=2, api_client=client)
    assert isinstance(r, dict)

"""

# =====================================================================
# LITERATURE
# =====================================================================

def test_search_arxiv(client):
    r = search_arxiv("GaN", max_results=2, api_client=client)
    assert isinstance(r, dict)


def test_search_crossref(client):
    r = search_crossref("GaN", rows=2, api_client=client)
    assert isinstance(r, dict)


# =====================================================================
# META
# =====================================================================

"""
def test_list_jarvis_columns(client):
    r = list_jarvis_columns(client)
    assert isinstance(r, list)

"""
