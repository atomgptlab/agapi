---
title: Protein Suite
---

# Protein Suite

Three-in-one biomolecular structure tools: ESMFold for single-chain protein folding (Meta), OpenFold3 for protein-DNA complex prediction (NVIDIA NIM), and a full RCSB Protein Data Bank explorer with search and metadata for 200,000+ experimental structures. All in one browser app with interactive 3D viewers and PDB downloads.

[:material-open-in-new: Open App](https://atomgpt.org/protein){ .md-button .md-button--primary }

---

## Overview

The Protein Suite combines three previously separate apps (ESMFold, OpenFold3, and PDB Explorer) into a single tabbed interface:

- **🧬 ESMFold tab** — Paste any amino acid sequence (10–400 residues) and get a 3D PDB structure via Meta's ESM Atlas API. Inline NGL viewer renders the predicted fold with rainbow cartoon coloring.
- **🧪 OpenFold3 tab** — Predict protein-DNA complex structures via NVIDIA's NIM-hosted OpenFold3 (AlphaFold3 architecture). Provide a protein sequence plus two DNA strands.
- **🔍 PDB Explorer tab** — Search 200,000+ experimental structures from RCSB PDB by keyword or PDB ID. Inline Mol* 3D viewer, full polymer entity breakdown, sequences, crystallographic data.

!!! info "Data Sources"
    **ESMFold** — `api.esmatlas.com/foldSequence/v1/pdb/` (Meta AI).
    **OpenFold3** — `health.api.nvidia.com` (NVIDIA NIM / BioNeMo).
    **PDB Explorer** — `data.rcsb.org` and `search.rcsb.org` (RCSB Protein Data Bank).

!!! note "Legacy URLs"
    `/protein_fold` and `/pdb_explorer` are kept as 302 redirects to `/protein` (the PDB Explorer redirects to `/protein#pdb`). Existing bookmarks continue to work.

## Endpoints

### `POST /protein_fold/predict` — ESMFold (web UI, JSON)

Predict 3D structure from amino acid sequence. Returns PDB content, atom count, residue count, amino acid composition, and molecular weight.

```bash
curl -X POST "https://atomgpt.org/protein_fold/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQQQ"
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `sequence` | string | Amino acid sequence (standard one-letter codes: ACDEFGHIKLMNPQRSTVWY, 10–400 residues) |

**Response:**

| Field | Description |
|-------|-------------|
| `success` | Boolean status |
| `pdb_content` | Full PDB file content |
| `sequence` | Cleaned uppercase sequence |
| `sequence_length` | Number of residues |
| `num_atoms` | Total atoms in PDB |
| `num_residues` | Unique residue count |
| `composition` | Amino acid composition dict (e.g. `{"ALA": 5, "GLY": 3}`) |
| `molecular_weight` | Estimated molecular weight (Da) |

---

### `GET /protein_fold/query` — ESMFold (API key, plain text PDB)

Returns the raw PDB file as plain text.

```bash
curl "https://atomgpt.org/protein_fold/query?sequence=MKTAYIAKQRQISFVKSHFS&APIKEY=sk-XYZ" \
  -H "accept: text/plain" \
  --output structure.pdb
```

---

### `POST /openfold/predict` — Protein-DNA complex (web UI, JSON)

Predict a protein-DNA complex structure using NVIDIA NIM OpenFold3. Session-authenticated endpoint used by the web UI; no API key required.

```bash
curl -X POST "https://atomgpt.org/openfold/predict" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -H "accept: application/json" \
  -d '{
    "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGD",
    "dna1": "ATCGATCGATCG",
    "dna2": "CGATCGATCGAT"
  }'
```

| Field | Type | Description |
|-------|------|-------------|
| `protein_sequence` | string | Protein amino acid sequence (one-letter codes, ≥10 residues) |
| `dna1` | string | First DNA strand (A/C/G/T only) |
| `dna2` | string | Second DNA strand, typically complementary |

**Response:**

| Field | Description |
|-------|-------------|
| `success` | Boolean status |
| `pdb_content` | Full complex PDB (protein + DNA chains) |
| `protein_length` | Protein residue count |
| `dna1_length` | DNA strand 1 length (nt) |
| `dna2_length` | DNA strand 2 length (nt) |

!!! warning "Inference time"
    OpenFold3 complex prediction typically takes 1–3 minutes per request.

---

### `GET /openfold/query` — Protein-DNA complex (API key, plain text PDB)

```bash
curl "https://atomgpt.org/openfold/query?protein_sequence=MKTAYIAKQRQISFVKSHFS&dna1=ATCGATCG&dna2=CGATCGAT&APIKEY=sk-XYZ" \
  -H "accept: text/plain" \
  --output complex.pdb
```

| Param | Description |
|-------|-------------|
| `protein_sequence` | Protein amino acid sequence |
| `dna1` | First DNA strand sequence |
| `dna2` | Second DNA strand sequence |

Returns plain-text PDB of the predicted complex.

---

### `POST /pdb_explorer/search` — RCSB full-text search

Search RCSB PDB by keyword. Returns matching entries with title, experimental method, resolution, deposition date, and authors.

```bash
curl -X POST "https://atomgpt.org/pdb_explorer/search" \
  -H "Authorization: Bearer sk-XYZ" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "hemoglobin",
    "max_results": 20
  }'
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | required | Free-text search query (e.g. `"hemoglobin"`, `"CRISPR"`, `"kinase"`) |
| `max_results` | int | 20 | Number of results to return (max 50) |

**Response:**

| Field | Description |
|-------|-------------|
| `query` | Echoed query string |
| `total` | Total matching entries in RCSB (may exceed `max_results`) |
| `results` | Array of `{pdb_id, title, method, resolution, deposition_date, authors, ...}` |

---

### `GET /pdb_explorer/entry/{pdb_id}` — Full RCSB entry metadata

Fetch detailed metadata for a single PDB entry: title, experimental method, resolution, R-factors, citation, unit cell, polymer entities (with sequences and organisms).

```bash
curl "https://atomgpt.org/pdb_explorer/entry/4HHB" \
  -H "Authorization: Bearer sk-XYZ"
```

**Response highlights:**

| Field | Description |
|-------|-------------|
| `pdb_id` | 4-character PDB identifier |
| `title` | Structure title |
| `method` | Experimental method (X-ray, NMR, EM, etc.) |
| `resolution` | Resolution in Å |
| `r_factor`, `r_free` | Refinement quality metrics |
| `cell` | Unit cell parameters `{a, b, c, alpha, beta, gamma}` |
| `spacegroup` | Crystallographic space group |
| `authors`, `journal`, `doi`, `pub_year` | Citation info |
| `polymers` | Array of polymer entities with sequence, length, organism, MW |

---

## Python Examples

=== "Fold a protein (ESMFold)"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/protein_fold/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "sequence": "KVFGRCELAAAMKRHGLDNYRGYSLGNWVCAAKFESNFNTQATNRNTDGSTDYGILQINSRWWCNDGRTPGSRNLCNIPCSALLSSDITASVNCAKKIVSDGNGMNAWVAWRNRCKGTDVQAWIRGCRL"
        },
    )
    data = response.json()
    if data["success"]:
        print(f"Residues: {data['num_residues']}")
        print(f"Atoms: {data['num_atoms']}")
        print(f"MW: {data['molecular_weight']:.0f} Da")
        with open("structure.pdb", "w") as f:
            f.write(data["pdb_content"])
        print("Saved structure.pdb")
    ```

=== "Get raw PDB (API key)"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/protein_fold/query",
        params={
            "sequence": "MKTAYIAKQRQISFVKSHFS",
            "APIKEY": "sk-XYZ",
        },
    )
    with open("peptide.pdb", "w") as f:
        f.write(response.text)
    ```

=== "Protein-DNA complex (OpenFold3)"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/openfold/predict",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "Content-Type": "application/json",
        },
        json={
            "protein_sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGD",
            "dna1": "ATCGATCGATCG",
            "dna2": "CGATCGATCGAT",
        },
        timeout=300,  # OpenFold3 inference can take 1-3 minutes
    )
    data = response.json()
    if data["success"]:
        print(f"Protein: {data['protein_length']} aa")
        print(f"DNA1: {data['dna1_length']} nt, DNA2: {data['dna2_length']} nt")
        with open("complex.pdb", "w") as f:
            f.write(data["pdb_content"])
        print("Saved protein-DNA complex PDB")
    ```

=== "Search RCSB PDB"

    ```python
    import requests

    response = requests.post(
        "https://atomgpt.org/pdb_explorer/search",
        headers={
            "Authorization": "Bearer sk-XYZ",
            "Content-Type": "application/json",
        },
        json={"query": "CRISPR Cas9", "max_results": 10},
    )
    data = response.json()
    print(f"Found {data['total']} total matches")
    for entry in data["results"]:
        res = entry.get("resolution")
        res_str = f"{res:.2f} Å" if res else "—"
        print(f"  {entry['pdb_id']}  {res_str}  {entry.get('title', '')[:60]}")
    ```

=== "Fetch PDB entry"

    ```python
    import requests

    response = requests.get(
        "https://atomgpt.org/pdb_explorer/entry/4HHB",
        headers={"Authorization": "Bearer sk-XYZ"},
    )
    entry = response.json()
    print(f"Title: {entry['title']}")
    print(f"Method: {entry['method']}, Resolution: {entry['resolution']} Å")
    print(f"Space group: {entry['spacegroup']}")
    print(f"Polymer entities: {len(entry['polymers'])}")
    for p in entry["polymers"]:
        print(f"  Entity {p['entity_id']}: {p['name']} "
              f"({p['length']} aa, {p['organism']})")
    ```

## AGAPI Agent [WIP]

```python
from agapi.agents import AGAPIAgent
import os

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))

# Fold a protein
response = agent.query_sync("Fold this protein sequence: MKTAYIAKQRQISFVKSHFS")
print(response)

# Look up a PDB structure
response = agent.query_sync("Tell me about PDB entry 4HHB")
print(response)
```

## References

- Z. Lin et al., *Science* **379**, 1123 (2023) — ESMFold [:material-link: DOI](https://doi.org/10.1126/science.ade2574)
- H.M. Berman et al., *Nucleic Acids Res.* **28**, 235 (2000) — RCSB PDB [:material-link: DOI](https://doi.org/10.1093/nar/28.1.235)
- [facebookresearch/esm](https://github.com/facebookresearch/esm)
- [NVIDIA NIM](https://developer.nvidia.com/nim) — OpenFold3 inference platform
- [RCSB PDB](https://www.rcsb.org) — Protein Data Bank
- [Mol* Viewer](https://molstar.org) — embedded 3D structure viewer
