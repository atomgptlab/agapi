TOOLS_SCHEMA = [
    # -------------------------------------------------------------------------
    # JARVIS-DFT
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "query_by_formula",
            "description": "Get all polymorphs of a chemical formula from JARVIS-DFT (e.g., SiC, GaN, MgB2)",
            "parameters": {
                "type": "object",
                "properties": {
                    "formula": {
                        "type": "string",
                        "description": "Chemical formula",
                    }
                },
                "required": ["formula"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_by_elements",
            "description": "Find materials containing specific elements (e.g., 'Si,C')",
            "parameters": {
                "type": "object",
                "properties": {
                    "elements": {
                        "type": "string",
                        "description": "Comma-separated elements",
                    }
                },
                "required": ["elements"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_by_jid",
            "description": "Get detailed info for a JARVIS ID (e.g., 'JVASP-1002')",
            "parameters": {
                "type": "object",
                "properties": {
                    "jid": {"type": "string", "description": "JARVIS ID"}
                },
                "required": ["jid"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_by_property",
            "description": "Find materials by property range (e.g., bandgap 2-3 eV)",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_name": {"type": "string"},
                    "min_val": {"type": "number"},
                    "max_val": {"type": "number"},
                    "elements": {"type": "string"},
                },
                "required": ["property_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_extreme",
            "description": "Find material with max/min property value",
            "parameters": {
                "type": "object",
                "properties": {
                    "property_name": {"type": "string"},
                    "maximize": {"type": "boolean"},
                    "elements": {"type": "string"},
                    "formula": {"type": "string"},
                    "constraint_property": {"type": "string"},
                    "min_constraint": {"type": "number"},
                    "max_constraint": {"type": "number"},
                },
                "required": ["property_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_jarvis_columns",
            "description": (
                "Return all column/property names available in the JARVIS-DFT database. "
                "Call this first when you are unsure which property name to pass to "
                "query_by_property or find_extreme."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    # -------------------------------------------------------------------------
    # Structure manipulation
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "make_supercell",
            "description": (
                "Create a supercell from a POSCAR structure by replicating the unit cell. "
                "Use this to create larger simulation cells for defect studies or interface calculations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string",
                    },
                    "scaling_matrix": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": (
                            "List of 3 integers [nx, ny, nz] for supercell dimensions. "
                            "Example: [2,1,1] creates 2×1×1 supercell."
                        ),
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
                "required": ["poscar", "scaling_matrix"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "substitute_atom",
            "description": (
                "Substitute (replace) atoms in a structure. For example, replace Ga with Al "
                "to study doping or alloy formation. Useful for creating substitutional defects "
                "or alloy structures."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string",
                    },
                    "element_from": {
                        "type": "string",
                        "description": "Element to replace (e.g., 'Ga', 'Si', 'N')",
                    },
                    "element_to": {
                        "type": "string",
                        "description": "Element to substitute with (e.g., 'Al', 'Ge', 'P')",
                    },
                    "num_substitutions": {
                        "type": "integer",
                        "description": "Number of atoms to substitute (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["poscar", "element_from", "element_to"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_vacancy",
            "description": (
                "Create vacancy defects by removing atoms from a structure. Useful for studying "
                "point defects, defect formation energies, or creating porous structures."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string",
                    },
                    "element": {
                        "type": "string",
                        "description": "Element to remove to create vacancy (e.g., 'Ga', 'Si', 'O')",
                    },
                    "num_vacancies": {
                        "type": "integer",
                        "description": "Number of atoms to remove (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["poscar", "element"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # ALIGNN property prediction
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "alignn_predict",
            "description": (
                "Predict material properties using ALIGNN machine learning models. "
                "Predicts formation energy, bandgap (OptB88vdW and MBJ), elastic moduli "
                "(bulk and shear), piezoelectric properties, and superconducting critical "
                "temperature. Accepts either a POSCAR structure string or a JARVIS-ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": (
                            "POSCAR format structure string. Required if jid is not provided."
                        ),
                    },
                    "jid": {
                        "type": "string",
                        "description": (
                            "JARVIS-ID (e.g., 'JVASP-1002'). If provided the structure is "
                            "fetched from JARVIS and poscar is ignored."
                        ),
                    },
                },
                "required": ["poscar"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # ALIGNN force field
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "alignn_ff_single_point",
            "description": (
                "Evaluate energy, forces, and stress for a structure using ALIGNN-FF "
                "without relaxing it. Atom limit: 50 (server-enforced). "
                "Use this to quickly assess energetics of an as-provided structure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string (max 50 atoms)",
                    }
                },
                "required": ["poscar"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "alignn_ff_relax",
            "description": (
                "Relax a crystal structure using the ALIGNN force field (legacy endpoint). "
                "For full trajectory data and optimizer control, prefer alignn_ff_optimize."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string",
                    },
                    "fmax": {
                        "type": "number",
                        "description": "Force convergence criterion in eV/Å (default: 0.05)",
                        "default": 0.05,
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Maximum optimization steps (default: 150)",
                        "default": 150,
                    },
                },
                "required": ["poscar"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "alignn_ff_optimize",
            "description": (
                "Relax a crystal structure using the ALIGNN force field with full trajectory "
                "output. Returns converged flag, final POSCAR, energy history, and max-force "
                "history. Atom limit: 100 (server-enforced). Supports FIRE, BFGS, and LBFGS "
                "optimizers and optional cell relaxation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string (max 100 atoms)",
                    },
                    "fmax": {
                        "type": "number",
                        "description": "Force convergence criterion in eV/Å (default: 0.05)",
                        "default": 0.05,
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Maximum optimization steps (default: 200)",
                        "default": 200,
                    },
                    "optimizer": {
                        "type": "string",
                        "enum": ["FIRE", "BFGS", "LBFGS"],
                        "description": "Optimization algorithm (default: 'FIRE')",
                        "default": "FIRE",
                    },
                    "relax_cell": {
                        "type": "boolean",
                        "description": "Whether to also relax cell vectors (default: true)",
                        "default": True,
                    },
                },
                "required": ["poscar"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "alignn_ff_md",
            "description": (
                "Run NVE molecular dynamics using the ALIGNN force field. Returns trajectory "
                "frames, energy vs time, and temperature vs time. Atom limit: 50 "
                "(server-enforced). Useful for studying thermal stability or diffusion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string (max 50 atoms)",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Initial temperature in Kelvin (default: 300)",
                        "default": 300.0,
                    },
                    "timestep": {
                        "type": "number",
                        "description": "MD timestep in femtoseconds (default: 0.5)",
                        "default": 0.5,
                    },
                    "steps": {
                        "type": "integer",
                        "description": "Number of MD steps (default: 50)",
                        "default": 50,
                    },
                    "interval": {
                        "type": "integer",
                        "description": "Frame save interval in steps (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["poscar"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # SlakoNet
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "slakonet_bandstructure",
            "description": (
                "Calculate electronic band structure and density of states using the SlakoNet "
                "tight-binding model. Returns band gap, VBM, CBM values AND a band structure "
                "plot image. Works best for structures with ≤10 atoms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string",
                    },
                    "energy_range_min": {
                        "type": "number",
                        "description": "Minimum energy for plot in eV (default: -8.0)",
                        "default": -8.0,
                    },
                    "energy_range_max": {
                        "type": "number",
                        "description": "Maximum energy for plot in eV (default: 8.0)",
                        "default": 8.0,
                    },
                },
                "required": ["poscar"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # XRD / DiffractGPT
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_xrd_pattern",
            "description": (
                "Generate a powder XRD pattern from a crystal structure. Simulates the XRD "
                "experiment and returns peak positions (2θ), relative intensities, and "
                "d-spacings. Returns a DiffractGPT-compatible description and a markdown "
                "peak table. Useful for comparing theoretical vs experimental patterns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string",
                    },
                    "wavelength": {
                        "type": "number",
                        "description": (
                            "X-ray wavelength in Å. Common values: 1.54184 (Cu Kα, default), "
                            "1.54056 (Cu Kα1), 0.71073 (Mo Kα)."
                        ),
                        "default": 1.54184,
                    },
                    "num_peaks": {
                        "type": "integer",
                        "description": "Number of strongest peaks to report (default: 20)",
                        "default": 20,
                    },
                    "theta_range": {
                        "type": "array",
                        "description": "2-theta range in degrees [min, max] (default: [0, 90])",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                },
                "required": ["poscar"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diffractgpt_predict",
            "description": (
                "Predict a crystal structure from XRD peaks using DiffractGPT. "
                "Peaks must be provided in the format '2theta(intensity),...' "
                "e.g. '30.42(1.0),49.02(0.49)'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "formula": {
                        "type": "string",
                        "description": "Chemical formula of the material",
                    },
                    "peaks": {
                        "type": "string",
                        "description": "XRD peaks as '2theta(intensity),...' e.g. '30.42(1.0),49.02(0.49)'",
                    },
                },
                "required": ["formula", "peaks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pxrd_match",
            "description": (
                "Match an experimental powder XRD pattern against the JARVIS-DFT database "
                "using cosine similarity. Provide two-column data (2theta intensity, one pair "
                "per line, space-separated). Returns the best-matching POSCAR from the database."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Chemical formula or element string (e.g. 'LaB6', 'Si')",
                    },
                    "pattern_data": {
                        "type": "string",
                        "description": (
                            "Two-column XRD data as a string: '2theta intensity\\n...'. "
                            "One pair per line, space-separated. "
                            "Example: '21.38 0.69\\n30.42 1.0\\n37.44 0.31'"
                        ),
                    },
                    "wavelength": {
                        "type": "number",
                        "description": "X-ray wavelength in Å (default: 1.54184 = Cu Kα)",
                        "default": 1.54184,
                    },
                },
                "required": ["query", "pattern_data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "xrd_match",
            "description": (
                "Match an experimental XRD pattern to the JARVIS-DFT database (legacy endpoint). "
                "For cosine-similarity matching prefer pxrd_match; "
                "for combined pattern-matching + DiffractGPT analysis use xrd_analyze."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "formula": {"type": "string"},
                    "xrd_pattern": {"type": "string"},
                },
                "required": ["formula", "xrd_pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "xrd_analyze",
            "description": (
                "Full XRD analysis pipeline: match an experimental pattern against JARVIS-DFT "
                "and optionally run DiffractGPT structure prediction. Returns best match, "
                "top-5 matches, similarity score, and (if method includes 'diffractgpt') a "
                "predicted POSCAR. method can be 'pattern_matching', 'diffractgpt', or 'both'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "formula": {
                        "type": "string",
                        "description": "Chemical formula (e.g. 'LaB6', 'Si,Ge')",
                    },
                    "xrd_data": {
                        "type": "string",
                        "description": (
                            "Two-column XRD data as a string: '2theta intensity\\n...'. "
                            "One pair per line, space-separated."
                        ),
                    },
                    "wavelength": {
                        "type": "number",
                        "description": "X-ray wavelength in Å (default: 1.54184)",
                        "default": 1.54184,
                    },
                    "method": {
                        "type": "string",
                        "enum": ["pattern_matching", "diffractgpt", "both"],
                        "description": "Analysis method (default: 'pattern_matching')",
                        "default": "pattern_matching",
                    },
                },
                "required": ["formula", "xrd_data"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # MicroscopyGPT
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "microscopygpt_analyze",
            "description": (
                "Analyze a microscopy image (STEM/TEM/SEM) using MicroscopyGPT to predict "
                "crystal structure, identify defects, or estimate elemental composition. "
                "Accepts PNG, JPG, or TIFF images. Returns predicted structure, confidence, "
                "and defect information."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Local path to the microscopy image file (PNG, JPG, TIFF)",
                    },
                    "formula": {
                        "type": "string",
                        "description": "Chemical formula hint to guide prediction (e.g. 'MoS2', 'GaN')",
                    },
                },
                "required": ["image_path", "formula"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # Intermat – heterostructure interface generation
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "generate_interface",
            "description": (
                "Generate a heterostructure interface between two materials (film on substrate). "
                "Creates the interface by matching lattice parameters and stacking the specified "
                "crystal surfaces."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "film_poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string for the film material (top layer)",
                    },
                    "substrate_poscar": {
                        "type": "string",
                        "description": "POSCAR format structure string for the substrate material (bottom layer)",
                    },
                    "film_indices": {
                        "type": "string",
                        "description": (
                            "Miller indices for the film surface, format: 'h_k_l' with underscores. "
                            "Common: '0_0_1' (001), '1_1_1' (111), '1_0_0' (100)."
                        ),
                        "default": "0_0_1",
                    },
                    "substrate_indices": {
                        "type": "string",
                        "description": "Miller indices for the substrate surface, format: 'h_k_l' with underscores.",
                        "default": "0_0_1",
                    },
                    "film_thickness": {
                        "type": "number",
                        "description": "Film layer thickness in Å (default: 16, typical: 10–30)",
                        "default": 16,
                    },
                    "substrate_thickness": {
                        "type": "number",
                        "description": "Substrate layer thickness in Å (default: 16, typical: 10–30)",
                        "default": 16,
                    },
                    "separation": {
                        "type": "number",
                        "description": "Interface separation distance in Å (default: 2.5, typical: 2.0–3.0)",
                        "default": 2.5,
                    },
                    "max_area": {
                        "type": "number",
                        "description": "Maximum interface area in Å². Larger values allow more lattice mismatch (default: 300).",
                        "default": 300,
                    },
                },
                "required": ["film_poscar", "substrate_poscar"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # Protein / biology
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "protein_fold",
            "description": (
                "Predict the 3D structure of a protein from its amino acid sequence using "
                "ESMFold AI. Returns a PDB format structure with atomic coordinates. "
                "Accepts sequences of 10–400 amino acids."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "string",
                        "description": (
                            "Amino acid sequence in one-letter codes: "
                            "A R N D C Q E G H I L K M F P S T W Y V. "
                            "Remove any whitespace or line breaks before passing."
                        ),
                    }
                },
                "required": ["sequence"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "openfold_predict",
            "description": (
                "Predict a protein-DNA complex 3D structure using NVIDIA OpenFold3. "
                "Accepts a protein amino acid sequence and two DNA strand sequences "
                "(sense and antisense). Returns a PDB format structure of the complex."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "protein_sequence": {
                        "type": "string",
                        "description": "Protein amino acid sequence in one-letter codes",
                    },
                    "dna1": {
                        "type": "string",
                        "description": "First (sense) DNA strand sequence",
                    },
                    "dna2": {
                        "type": "string",
                        "description": "Second (antisense / complementary) DNA strand sequence",
                    },
                },
                "required": ["protein_sequence", "dna1", "dna2"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # External databases
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "query_mp",
            "description": (
                "Fetch crystal structures from the Materials Project via the OPTIMADE API. "
                "Returns structures with POSCAR, formation energy, and related properties."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "formula": {
                        "type": "string",
                        "description": "Reduced chemical formula (e.g. 'MoS2', 'Al2O3')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 500)",
                        "default": 10,
                    },
                },
                "required": ["formula"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_oqmd",
            "description": (
                "Fetch crystal structures from the Open Quantum Materials Database (OQMD) "
                "via the OPTIMADE API. Returns structures with POSCAR and energetics."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "formula": {
                        "type": "string",
                        "description": "Reduced chemical formula (e.g. 'MoS2', 'Fe2O3')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 500)",
                        "default": 10,
                    },
                },
                "required": ["formula"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # Literature search
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "search_arxiv",
            "description": (
                "Search arXiv preprints for materials science literature. "
                "Returns title, authors, abstract summary, and submission date. "
                "Use for recent/preprint research; use search_crossref for published journals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search string (e.g. 'GaN bandgap DFT', 'ALIGNN neural network')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10, max: 100)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_crossref",
            "description": (
                "Search published journal articles via the Crossref API. "
                "Returns title, authors, DOI, journal, and publication date. "
                "Use for peer-reviewed literature; use search_arxiv for preprints."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search string (e.g. 'silicon bandgap experiment')",
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of results to return (default: 10, max: 100)",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    # -------------------------------------------------------------------------
    # Battery cathode prediction (ALIGNN-FF)
    # -------------------------------------------------------------------------
    {
        "type": "function",
        "function": {
            "name": "battery_predict",
            "description": (
                "Predict battery cathode voltage profile and theoretical capacity "
                "for an intercalation electrode. Sequentially removes the intercalating "
                "ion from a supercell, computes energy at each step with ALIGNN-FF, "
                "and builds a voltage vs. ion-fraction curve. Returns voltages, "
                "gravimetric and volumetric capacities, density, molar mass, and "
                "energies at each composition step. The input POSCAR must already "
                "contain the intercalating ion (e.g. LiCoO2 for Li-ion)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "poscar": {
                        "type": "string",
                        "description": "VASP POSCAR string of the cathode structure (must contain the intercalating ion).",
                    },
                    "element": {
                        "type": "string",
                        "description": "Intercalating ion: 'Li', 'Na', 'K', 'Mg', 'Ca', or 'Zn'.",
                        "default": "Li",
                    },
                    "model": {
                        "type": "string",
                        "description": "ALIGNN-FF model variant: 'default' or 'wt01'.",
                        "default": "default",
                    },
                },
                "required": ["poscar"],
            },
        },
    },
]
