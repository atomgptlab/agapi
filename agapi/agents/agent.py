# agapi/agents/agent.py
import json
from typing import Dict, Any, Union
import asyncio
from openai import AsyncOpenAI

from .config import AgentConfig
from .client import AGAPIClient
from .schema import TOOLS_SCHEMA
from .functions import (
    query_by_formula,
    query_by_elements,
    query_by_jid,
    query_by_property,
    find_extreme,
    alignn_predict,
    alignn_ff_relax,
    slakonet_bandstructure,
    diffractgpt_predict,
    xrd_match,
    generate_xrd_pattern,
    generate_interface,
    make_supercell,
    substitute_atom,
    create_vacancy,
    protein_fold,
    battery_predict,
)


SYSTEM_PROMPT = """You are a materials science AI assistant with access to computational tools for materials discovery, structure prediction, property calculations, and protein folding.

**DATABASES:**
- JARVIS-DFT: 80,000+ DFT-calculated materials (3D bulk crystals, 2D materials, molecules)
- Materials properties: formation energy, bandgap (MBJ, OptB88vdW), elastic moduli, dielectric constants, magnetic moments, superconducting Tc, and 70+ other properties
- Coverage: Elements, compounds, alloys across periodic table

**COMPUTATIONAL TOOLS:**

1. **ALIGNN (ML Property Predictions)**
   - Formation energy per atom (eV/atom)
   - Bandgap: MBJ and OptB88vdW functionals (eV)
   - Elastic properties: bulk modulus, shear modulus (GPa)
   - Dielectric properties: piezoelectric coefficients
   - Superconducting critical temperature Tc (K)
   - All predictions in <1 second per structure
   - Max structure size: 50 atoms

2. **ALIGNN-FF (Force Field Relaxation)**
   - Full structure optimization (atomic positions + cell parameters)
   - Fast relaxation (typically 1-3 minutes)
   - Returns: relaxed POSCAR with optimized geometry
   - Max structure size: 50 atoms
   - Use before property predictions for modified structures

3. **SlakoNet (Tight-Binding Band Structure)**
   - Electronic band structure calculation
   - Returns: Band structure plot (PNG), bandgap (eV), VBM (eV), CBM (eV)
   - Includes k-point path, total DOS, atom-projected DOS
   - Max structure size: 50 atoms
   - Typical calculation time: 30-60 seconds
   - Note: Tight-binding often overestimates bandgaps vs DFT

4. **DiffractGPT (XRD → Structure)**
   - Inverse design: predict crystal structure from powder XRD pattern
   - Input: chemical formula + XRD peaks (2θ, intensity)
   - Output: Predicted atomic structure (POSCAR)
   - Uses generative AI trained on crystallographic database

5. **Intermat (Heterostructure Interfaces)**
   - Create 2D/3D interfaces between two materials
   - Input: Two POSCARs + Miller indices for each surface
   - Output: Optimized interface structure
   - Parameters: film/substrate thickness, separation, lattice matching tolerance
   - Use cases: Semiconductor junctions, 2D heterostructures, epitaxy

6. **XRD Pattern Matching**
   - Match experimental powder XRD to JARVIS-DFT database
   - Input: Experimental 2θ vs intensity data
   - Output: Best matching materials from database
   - Uses cosine similarity for pattern comparison

7. **ESMFold (Protein Structure Prediction)**
   - Predict 3D protein structure from amino acid sequence
   - Input: One-letter amino acid sequence (A,R,N,D,C,Q,E,G,H,I,L,K,M,F,P,S,T,W,Y,V)
   - Output: PDB format structure file with atomic coordinates
   - Length: 10-400 amino acids
   - AI-based prediction, no MSA required
   - Typical prediction time: 30-90 seconds

8. **XRD Pattern Generation**
   - Generate theoretical powder XRD pattern from crystal structure
   - Input: POSCAR structure + wavelength (default: Cu K-alpha = 1.54184 Å)
   - Output: Peak positions (2θ), relative intensities, d-spacings
   - Returns DiffractGPT-compatible description
   - Use cases: Predict XRD before synthesis, compare theory vs experiment, phase identification

**STRUCTURE MANIPULATION TOOLS:**

1. **make_supercell(poscar, scaling_matrix)**
   - Create supercells by replicating unit cell
   - scaling_matrix: [nx, ny, nz] e.g., [2,1,1] doubles a-direction
   - Essential for defect studies (use ≥2x2x2 for point defects)
   - Returns: supercell POSCAR, atom counts, formula

2. **substitute_atom(poscar, element_from, element_to, num_substitutions)**
   - Replace specific atoms (e.g., Ga→Al for doping, alloying)
   - Substitutes first occurrence(s) of element_from
   - Returns: modified POSCAR, substituted indices, before/after formulas
   - Use cases: Doping, alloy formation, cation/anion substitution

3. **create_vacancy(poscar, element, num_vacancies)**
   - Remove atoms to create vacancy defects
   - Removes first occurrence(s) of specified element
   - Returns: modified POSCAR, removed indices, atom counts
   - Use cases: Point defects, vacancy complexes, non-stoichiometry

**CRITICAL BANDGAP REPORTING RULES:**
- ALWAYS prefer MBJ bandgap (mbj_bandgap) - it's more accurate for semiconductors
- Only use OptB88vdW bandgap (optb88vdw_bandgap) if MBJ is not available
- When reporting bandgaps, ALWAYS indicate which method: "3.2 eV (MBJ)" or "2.8 eV (OptB88vdW)"
- For common semiconductors (Si, GaN, GaAs, etc.), MBJ values are near-experimental quality
- SlakoNet provides tight-binding estimates (often overestimates by 20-50%)
- If comparing methods, explicitly state: "ALIGNN-MBJ: X eV, ALIGNN-OptB88vdW: Y eV, SlakoNet: Z eV"

**STRUCTURE MANIPULATION WORKFLOWS:**

**Workflow 1: Simple Doping Study**
1. Query database for base material (e.g., "Find GaN")
2. Get POSCAR for most stable structure
3. Make supercell (e.g., 2x2x2 for dilute doping)
4. Substitute atoms (e.g., Ga→Al for one site)
5. Relax with ALIGNN-FF
6. Predict properties with ALIGNN
7. Compare bandgap: pristine vs doped

**Workflow 2: Vacancy Defect Study**
1. Query database for material
2. Get POSCAR
3. Make larger supercell (≥2x2x2 to minimize periodic image interactions)
4. Create vacancy (remove one atom)
5. Relax with ALIGNN-FF (very important - atoms rearrange around vacancy)
6. Predict properties with ALIGNN
7. Calculate band structure with SlakoNet
8. Compare with pristine: formation energy change, bandgap change

**Workflow 3: Heterostructure/Interface**
1. Find two compatible materials (film and substrate)
2. Get POSCARs for both
3. Generate interface with Intermat (specify Miller indices, thicknesses)
4. Relax interface with ALIGNN-FF
5. Predict interfacial properties with ALIGNN
6. Calculate electronic structure with SlakoNet

**Workflow 4: XRD Structure Solution**
1. Parse experimental XRD data (2θ, intensity)
2. Option A: Match to database (fast, if structure is known)
3. Option B: Use DiffractGPT to generate new structure (for unknown phases)
4. Validate: Calculate XRD from predicted structure, compare to experiment
5. Relax predicted structure with ALIGNN-FF
6. Predict properties with ALIGNN

**Workflow 5: Protein Structure Analysis**
1. Take amino acid sequence
2. Predict structure with ESMFold
3. Analyze PDB output: secondary structure, folding, domains
4. Can be saved as PDB file for visualization in PyMOL/Chimera


**XRD WORKFLOWS:**

**Forward Direction (Structure → XRD):**
1. Get structure (from database or file)
2. Generate XRD pattern with `generate_xrd_pattern`
3. Analyze peak positions and intensities
4. Compare with experimental data if available

**Inverse Direction (XRD → Structure):**
1. Input experimental XRD pattern
2. Option A: Match to database with `xrd_match`
3. Option B: Predict structure with DiffractGPT
4. Validate by generating XRD from predicted structure

**Round-trip Validation:**
1. Start with known structure
2. Generate XRD pattern
3. Feed to DiffractGPT or database matching
4. Compare reconstructed structure with original

**EXAMPLE QUERIES YOU CAN ANSWER:**

**Database Queries:**
- "Find all materials containing Ga and N"
- "Find semiconductors with bandgap between 2-3 eV"
- "What's the most stable polymorph of SiC?"
- "Find 2D materials with high mobility"
- "Get the elastic moduli of diamond"

**Property Predictions:**
- "Predict properties of this POSCAR: [paste POSCAR]"
- "What's the bandgap of Al₀.₂₅Ga₀.₇₅N alloy?"
- "Calculate band structure for wurtzite GaN"

**Structure Modifications:**
- "Create GaN with one Ga vacancy in a 2x2x2 supercell, relax it, and predict properties"
- "Make Al-doped GaN (10% Al), optimize, and calculate band structure"
- "Generate a GaN/AlN interface and predict its properties"

**Materials Discovery:**
- "Find materials similar to GaN but with higher thermal conductivity"
- "What's the bandgap trend in the series: GaN, GaP, GaAs, GaSb?"
- "Compare MBJ vs OptB88vdW bandgaps for III-V semiconductors"

**Protein Folding:**
- "Predict the structure of this protein: MKTAYIAK..."
- "Fold this enzyme sequence and show the structure"
- "Generate PDB file for antibody sequence"

**KEY OPERATIONAL RULES:**

1. **Always report totals**: "Found 15 GaN structures in database" (not just "Found GaN")

2. **Bandgap precision**: Always include method label and round appropriately
   - Example: "3.28 eV (MBJ)" or "2.94 eV (OptB88vdW)"

3. **Defect workflow order**: ALWAYS create supercell FIRST, then modify
   - ❌ Wrong: vacancy → supercell
   - ✅ Correct: supercell → vacancy

4. **Structure size limits**:
   - ALIGNN predictions: ≤50 atoms
   - ALIGNN-FF relaxation: ≤50 atoms (larger = timeout risk)
   - SlakoNet: ≤50 atoms
   - For larger systems: Use supercell only if needed for defects

5. **Always relax after modification**: 
   - After substitution: ALWAYS relax with ALIGNN-FF
   - After vacancy creation: ALWAYS relax with ALIGNN-FF
   - Atoms rearrange significantly around defects

6. **Tool chaining logic**: Plan multi-step workflows
   - Database query → get POSCAR → supercell → modify → relax → predict → plot
   - Don't skip steps: Each output feeds the next input

7. **Timeout handling**: If ALIGNN-FF times out (large structure):
   - Try smaller supercell (e.g., 2x1x1 instead of 2x2x2)
   - Or skip relaxation and note this limitation in response

8. **Protein sequences**: 
   - Clean input (remove spaces, numbers, special characters)
   - Validate: only standard amino acids (ARNDCQEGHILKMFPSTWYV)
   - Length: 10-400 amino acids

9. **XRD data format**:
   - First line: formula (optionally with wavelength: "LaB6;1.54184")
   - Subsequent lines: "2theta intensity" (space-separated)

10. **Comparison studies**: When comparing methods, present results clearly:
```
    Bandgap comparison for Al₀.₂₅Ga₀.₇₅N:
    - Database (pristine GaN):  3.08 eV (MBJ)
    - ALIGNN (MBJ):             4.23 eV
    - ALIGNN (OptB88vdW):       3.87 eV  
    - SlakoNet (tight-binding): 6.11 eV
    
    Analysis: Alloying increases gap vs pristine GaN. SlakoNet overestimates 
    (typical for TB methods). ALIGNN-MBJ most reliable for this alloy.
```

**RESPONSE FORMATTING:**
- Be concise but complete
- Use tables for multi-property results
- Always cite which tool/method produced each result
- For errors: Explain clearly and suggest alternatives
- For successful workflows: Summarize key findings at the end

**LIMITATIONS TO COMMUNICATE:**
- "ALIGNN predictions are ML-based estimates, not ab initio DFT"
- "SlakoNet uses tight-binding, which typically overestimates gaps"
- "Relaxation with ALIGNN-FF is approximate; for publication, use DFT (VASP, QE)"
- "ESMFold predictions are AI-based; validate experimentally for critical applications"
- "Database queries limited to JARVIS-DFT materials (pre-computed)"

**WHAT YOU CANNOT DO:**
- Run ab initio DFT calculations (only ML predictions and tight-binding)
- Access materials beyond JARVIS-DFT database
- Predict protein-ligand binding or molecular dynamics
- Synthesize materials or provide experimental protocols
- Access real-time literature (knowledge cutoff: January 2025)


**TOOL CALLING BEST PRACTICES:**

1. **Never call the same tool multiple times with identical arguments**
   - If a tool returns truncated data, use the summary fields (peak_table, description, etc.)
   - Don't retry hoping for different results - move forward with available data

2. **Use data from tool results, not training knowledge**
   - If tool returns 8 peaks, report those 8 peaks - don't add 2 more from memory
   - If uncertain about data quality, mention it but don't fabricate data

3. **For XRD pattern generation:**
   - Call once per structure
   - Use 'peaks' list for accurate data
   - Use 'peak_table' for formatted display
   - Use 'description' for DiffractGPT-compatible format
   - Don't add Miller indices unless explicitly calculated

You are helpful, accurate, and scientifically rigorous. When uncertain, say so. Always prioritize correct methodology over speed."""


class AGAPIAgent:
    """
    Unified AGAPI Agent with all computational tools.

    Usage:
        agent = AGAPIAgent()
        result = agent.query_sync("Find SiC and predict with ALIGNN")
    """

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        temperature: float = None,
        max_iterations: int = None,
        timeout: int = None,
        api_base: str = None,
        system_prompt: str = None,
    ):
        self.api_key = api_key or AgentConfig.DEFAULT_API_KEY
        self.model = model or AgentConfig.DEFAULT_MODEL
        self.temperature = (
            temperature
            if temperature is not None
            else AgentConfig.DEFAULT_TEMPERATURE
        )
        self.max_iterations = (
            max_iterations or AgentConfig.DEFAULT_MAX_ITERATIONS
        )
        self.timeout = timeout or AgentConfig.DEFAULT_TIMEOUT
        self.api_base = api_base or AgentConfig.API_BASE
        self.system_prompt = system_prompt or SYSTEM_PROMPT

        self.agapi_client = AGAPIClient(
            api_key=self.api_key, timeout=self.timeout, api_base=self.api_base
        )
        self.openai_client = AsyncOpenAI(
            base_url=f"{self.api_base}/api", api_key=self.api_key
        )

        # Store tool results for access after query
        self.last_tool_results = []

    def _display_image(self, result: dict, verbose: bool = False):
        """Helper to display band structure image in Jupyter"""
        try:
            from IPython.display import display, Image, HTML
            import base64

            # Decode image
            image_data = base64.b64decode(result["image_base64"])

            # Create styled header with properties
            band_gap = result.get("band_gap_eV", "N/A")
            vbm = result.get("vbm_eV", "N/A")
            cbm = result.get("cbm_eV", "N/A")

            # Clean up band_gap if it's a list string
            if isinstance(band_gap, str) and "[" in band_gap:
                try:
                    import ast

                    band_gap_list = ast.literal_eval(band_gap)
                    if (
                        isinstance(band_gap_list, list)
                        and len(band_gap_list) > 0
                    ):
                        band_gap = f"{band_gap_list[0]:.4f}"
                except:
                    pass

            html = f"""
<div style="border: 3px solid #4CAF50; border-radius: 12px; padding: 20px; margin: 15px 0; max-width: 100%; background: linear-gradient(to bottom, #f8fff8, #ffffff);">
    <h3 style="margin-top: 0; color: #4CAF50; display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 1.5em;">📊</span> Band Structure Plot
    </h3>
    <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
        <tr style="background: #f0f0f0;">
            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd; font-weight: 600;">Quantity</th>
            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd; font-weight: 600;">Value</th>
        </tr>
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Band gap</strong></td>
            <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee; font-weight: 600; color: #2196F3;">{band_gap} eV</td>
        </tr>
        <tr style="background: #fafafa;">
            <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>Valence-band maximum (VBM)</strong></td>
            <td style="padding: 10px; text-align: right; border-bottom: 1px solid #eee; font-weight: 600; color: #FF5722;">{vbm} eV</td>
        </tr>
        <tr>
            <td style="padding: 10px;"><strong>Conduction-band minimum (CBM)</strong></td>
            <td style="padding: 10px; text-align: right; font-weight: 600; color: #9C27B0;">{cbm} eV</td>
        </tr>
    </table>
</div>
"""
            display(HTML(html))

            # Display image
            display(Image(data=image_data, format="png", width=800))

            if verbose:
                print(f"✓ Displayed band structure image")

        except ImportError:
            if verbose:
                print(
                    "⚠ Not in Jupyter environment - image cannot be displayed"
                )
                print(
                    f"  Image data available as base64 (length: {len(result.get('image_base64', ''))} chars)"
                )
        except Exception as e:
            if verbose:
                print(f"✗ Error displaying image: {str(e)}")

    async def query(
        self,
        query: str,
        verbose: bool = False,
        return_dict: bool = False,
        show_tool_results: bool = False,
        use_tools: bool = True,
        auto_display_images: bool = False,
        max_context_messages: int = 20,  # NEW: Limit message history
    ) -> Union[str, Dict[str, Any]]:
        """
        Execute query (async)

        Args:
            query: Natural language query
            verbose: Print debug info
            return_dict: If True, return raw dict data instead of text
            show_tool_results: If True, append raw tool results to response
            use_tools: If False, disable tool calling (direct LLM response only)
            auto_display_images: If True, automatically display SlakoNet images
            max_context_messages: Maximum messages to keep in context (default: 20)

        Returns:
            str: Formatted text response (default)
            dict: Raw data dictionary (if return_dict=True)
        """
        # Use different system prompt when tools are disabled
        if use_tools:
            system_prompt = self.system_prompt
        else:
            system_prompt = """You are a materials science AI assistant with extensive knowledge of materials properties, computational methods, and DFT calculations.

    When answering questions about materials properties:
    - Provide answers based on your training knowledge
    - Include typical experimental or computational values when known
    - Mention uncertainty or ranges when appropriate
    - Explain which computational methods (DFT, GW, hybrid functionals) typically give which results
    - For common materials (Si, GaN, SiC, diamond, graphene, etc.), provide well-known literature values

    You do NOT have access to databases or computational tools in this mode - answer only from your extensive training knowledge of materials science."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        self.last_tool_results = []  # Reset for new query
        tool_call_history = []  # Track all tool calls

        for iteration in range(self.max_iterations):
            if verbose:
                print(f"[Iteration {iteration + 1}/{self.max_iterations}]")

            # 🎯 CRITICAL FIX: Truncate messages if too long
            if len(messages) > max_context_messages:
                # Keep system message + last N messages
                messages = [messages[0]] + messages[
                    -(max_context_messages - 1) :
                ]
                if verbose:
                    print(f"  [Truncated context to {len(messages)} messages]")

            try:
                # Prepare API call parameters
                api_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                }

                # Add tools only if use_tools=True
                if use_tools:
                    api_params["tools"] = TOOLS_SCHEMA
                    api_params["tool_choice"] = "auto"

                response = await self.openai_client.chat.completions.create(
                    **api_params
                )

                message = response.choices[0].message

                # If no tool calls OR tools disabled, return final response
                if not message.tool_calls or not use_tools:
                    final_response = (
                        message.content
                        if message.content
                        else "No response generated."
                    )

                    # Auto-display images if requested
                    if auto_display_images and self.last_tool_results:
                        for tool_result in self.last_tool_results:
                            if (
                                isinstance(tool_result, dict)
                                and "image_base64" in tool_result
                            ):
                                self._display_image(
                                    tool_result, verbose=verbose
                                )

                    # Optionally append tool results
                    if show_tool_results and tool_call_history:
                        final_response += "\n\n" + "=" * 70 + "\n"
                        final_response += "RAW TOOL RESULTS:\n"
                        final_response += "=" * 70 + "\n"
                        for i, call in enumerate(tool_call_history, 1):
                            final_response += (
                                f"\n[Tool Call {i}] {call['function_name']}\n"
                            )
                            final_response += f"Arguments: {json.dumps(call['arguments'], indent=2)}\n"
                            # Truncate large results
                            result_str = json.dumps(call["result"], indent=2)
                            if len(result_str) > 1000:
                                result_str = (
                                    result_str[:1000] + "\n... (truncated)"
                                )
                            final_response += f"Result: {result_str}\n"
                            final_response += "-" * 70 + "\n"

                    # Return dict or text
                    if return_dict:
                        if len(self.last_tool_results) == 1:
                            result = self.last_tool_results[0]
                        elif len(self.last_tool_results) > 1:
                            result = {"results": self.last_tool_results}
                        else:
                            try:
                                result = json.loads(message.content)
                            except:
                                result = {"response": message.content}

                        if show_tool_results:
                            result["tool_call_history"] = tool_call_history

                        return result
                    else:
                        return final_response

                messages.append(message)

                # Process tool calls (only if use_tools=True)
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name

                    if verbose:
                        print(f"  Calling: {function_name}")

                    try:
                        function_args = json.loads(
                            tool_call.function.arguments
                        )
                    except json.JSONDecodeError as e:
                        result = {"error": f"Invalid JSON: {str(e)}"}
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(result),
                            }
                        )
                        continue

                    result = self._execute_function(
                        function_name, function_args
                    )

                    # Store result
                    self.last_tool_results.append(result)

                    # Track tool call history
                    tool_call_history.append(
                        {
                            "function_name": function_name,
                            "arguments": function_args,
                            "result": result,
                        }
                    )

                    if verbose and "error" in result:
                        print(f"  Error: {result['error']}")

                    # 🎯 CRITICAL FIX: Truncate large tool results before adding to messages
                    result_str = json.dumps(result)
                    if len(result_str) > 10000:  # Limit to 10K chars
                        # Keep only essential fields
                        truncated = {}
                        for key in [
                            "status",
                            "message",
                            "error",
                            "formula",
                            "jid",
                            "band_gap_eV",
                            "vbm_eV",
                            "cbm_eV",
                            "num_atoms",
                            "relaxed_poscar",
                            "modified_poscar",
                            "supercell_poscar",
                            "peaks",
                            "num_peaks_found",
                            "num_peaks_reported",
                            "description",
                            "wavelength",
                            "pdb_structure",
                        ]:
                            if key in result:
                                truncated[key] = result[key]

                        # For large POSCARs, truncate to first/last few lines
                        for key in [
                            "relaxed_poscar",
                            "modified_poscar",
                            "supercell_poscar",
                        ]:
                            if (
                                key in truncated
                                and len(str(truncated[key])) > 2000
                            ):
                                poscar_lines = str(truncated[key]).splitlines()
                                truncated[key] = "\n".join(
                                    poscar_lines[:10]
                                    + ["..."]
                                    + poscar_lines[-5:]
                                )

                        result_str = json.dumps(truncated)
                        if verbose:
                            print(
                                f"  [Truncated result from {len(json.dumps(result))} to {len(result_str)} chars]"
                            )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_str,
                        }
                    )

            except Exception as e:
                if (
                    "max_tokens" in str(e).lower()
                    or "context" in str(e).lower()
                ):
                    # Context too long - try to recover
                    if verbose:
                        print(f"  [Context length error, reducing history]")
                    # Drastically reduce context
                    messages = [messages[0]] + messages[-5:]
                    continue

                if return_dict:
                    return {"error": str(e)}
                else:
                    return f"Error: {str(e)}"

        if return_dict:
            result = (
                {"results": self.last_tool_results}
                if self.last_tool_results
                else {"error": "Max iterations reached"}
            )
            if show_tool_results:
                result["tool_call_history"] = tool_call_history
            return result
        else:
            return "Query completed."

    def query_sync(
        self,
        query: str,
        verbose: bool = True,
        render_html: bool = False,
        html_style: str = "bootstrap",
        max_show: int = 20,
        return_dict: bool = False,
        show_tool_results: bool = False,
        use_tools: bool = True,
        auto_display_images: bool = False,
        max_context_messages: int = 20,
    ) -> Union[str, Dict[str, Any]]:
        """
        Execute query (sync) with optional HTML rendering or dict return.

        Parameters
        ----------
        query : str
            User query to the agent.
        verbose : bool
            Show iteration debug prints.
        render_html : bool
            If True, render result as HTML in Jupyter/Colab (overrides return_dict).
        html_style : str
            "bootstrap" (default) or "css" (minimal inline css).
        max_show : int
            Max rows to show when converting materials list to a table.
        return_dict : bool
            If True (and render_html=False), return raw dict data instead of text.
        show_tool_results : bool
            If True, include raw tool results in response.
        use_tools : bool
            If False, disable tool calling (direct LLM response only).
        auto_display_images : bool
            If True, automatically display SlakoNet band structure images.

        Returns
        -------
        Union[str, Dict[str, Any]]
            Text response (default), dict (if return_dict=True), or displays HTML (if render_html=True)
        """

        # Helper functions
        def materials_to_markdown(materials: list, show: int = None) -> str:
            try:
                from tabulate import tabulate
            except ImportError:
                return json.dumps(materials, indent=2)

            if not materials:
                return "No materials found."

            cols = [
                "jid",
                "formula",
                "spg_symbol",
                "formation_energy_peratom",
                "bulk_modulus_kv",
                "bandgap",
                "bandgap_source",
                "mbj_bandgap",
                "optb88vdw_bandgap",
                "ehull",
            ]
            cols = [c for c in cols if any(c in m for m in materials)]
            mats = materials[:show] if show else materials

            rows = []
            for m in mats:
                row = []
                for c in cols:
                    v = m.get(c, "")
                    if isinstance(v, float):
                        row.append(f"{v:.4g}")
                    elif v is None:
                        row.append("")
                    else:
                        row.append(str(v))
                rows.append(row)

            headers = [c.replace("_", " ").title() for c in cols]
            return tabulate(rows, headers=headers, tablefmt="github")

        def envelope_to_markdown(
            envelope: Union[str, dict], max_show: int = None
        ) -> str:
            if isinstance(envelope, str):
                if any(
                    marker in envelope
                    for marker in ["#", "**", "|", "```", "\n-"]
                ):
                    return envelope
                else:
                    return f"**Response:**\n\n{envelope}"

            if isinstance(envelope, dict):
                if "materials" in envelope:
                    header = (
                        f"**Found {len(envelope['materials'])} materials**\n\n"
                    )
                    table = materials_to_markdown(
                        envelope.get("materials", []), show=max_show
                    )
                    return header + table
                elif "results" in envelope and isinstance(
                    envelope["results"], list
                ):
                    parts = []
                    for i, res in enumerate(envelope["results"], 1):
                        if isinstance(res, dict) and "materials" in res:
                            parts.append(f"## Result {i}\n\n")
                            parts.append(
                                materials_to_markdown(
                                    res["materials"], show=max_show
                                )
                            )
                        else:
                            parts.append(
                                f"## Result {i}\n\n```json\n{json.dumps(res, indent=2)}\n```"
                            )
                    return "\n\n".join(parts)
                elif "response" in envelope:
                    return envelope["response"]
                else:
                    return f"```json\n{json.dumps(envelope, indent=2)}\n```"

            return str(envelope)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                try:
                    import nest_asyncio

                    nest_asyncio.apply()
                    envelope = loop.run_until_complete(
                        self.query(
                            query,
                            verbose,
                            return_dict,
                            show_tool_results,
                            use_tools,
                            auto_display_images,
                            max_context_messages,
                        )
                    )
                except ImportError:
                    raise RuntimeError(
                        "Install nest_asyncio for Jupyter support"
                    )
            else:
                envelope = loop.run_until_complete(
                    self.query(
                        query,
                        verbose,
                        return_dict,
                        show_tool_results,
                        use_tools,
                        auto_display_images,
                        max_context_messages,
                    )
                )
        except RuntimeError:
            envelope = asyncio.run(
                self.query(
                    query,
                    verbose,
                    return_dict,
                    show_tool_results,
                    use_tools,
                    auto_display_images,
                    max_context_messages,
                )
            )
        # If rendering HTML is requested
        if render_html:
            try:
                from IPython.display import HTML, display
                import markdown as mdlib
            except Exception:
                return envelope

            md_text = envelope_to_markdown(envelope, max_show)
            md_text = (
                md_text.replace("\u202f", " ")
                .replace("\u2212", "-")
                .replace("\u2013", "-")
                .replace("\u2014", "-")
            )

            html_body = mdlib.markdown(
                md_text, extensions=["tables", "fenced_code"]
            )

            if html_style == "bootstrap":
                bootstrap = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
.agapi-card { 
    max-width: 960px; 
    margin: 20px auto; 
    padding: 20px;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
.agapi-card table { width: 100%; margin: 1em 0; }
.agapi-card table th, .agapi-card table td { vertical-align: middle; padding: 8px 12px; }
</style>
"""
                html_body = html_body.replace(
                    "<table>",
                    '<table class="table table-sm table-striped table-hover">',
                )
                full_html = (
                    f"{bootstrap}<div class='agapi-card'>{html_body}</div>"
                )
            else:
                css = """
<style>
.agapi-wrap { max-width: 900px; margin: 20px auto; padding: 20px; }
.agapi-wrap table { width: 100%; border-collapse: collapse; margin: 1em 0; }
</style>
"""
                full_html = f"{css}<div class='agapi-wrap'>{html_body}</div>"

            try:
                display(HTML(full_html))
                return envelope
            except Exception:
                return envelope

        return envelope

    def _execute_function(
        self, function_name: str, function_args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool function"""

        # 🎯 SANITIZE function name - remove special tokens
        function_name = function_name.split("<|")[
            0
        ]  # Remove <|channel|>, <|endoftext|>, etc.
        function_name = function_name.split("|>")[0]  # Remove |> suffix
        function_name = function_name.strip()

        function_args["api_client"] = self.agapi_client

        functions = {
            "query_by_formula": query_by_formula,
            "query_by_elements": query_by_elements,
            "query_by_jid": query_by_jid,
            "query_by_property": query_by_property,
            "find_extreme": find_extreme,
            "alignn_predict": alignn_predict,
            "alignn_ff_relax": alignn_ff_relax,
            "slakonet_bandstructure": slakonet_bandstructure,
            "diffractgpt_predict": diffractgpt_predict,
            "xrd_match": xrd_match,
            "generate_xrd_pattern": generate_xrd_pattern,
            "generate_interface": generate_interface,
            "make_supercell": make_supercell,
            "substitute_atom": substitute_atom,
            "create_vacancy": create_vacancy,
            "protein_fold": protein_fold,
            "battery_predict": battery_predict,
        }

        func = functions.get(function_name)
        if func:
            return func(**function_args)
        else:
            # More helpful error message
            available = ", ".join(functions.keys())
            return {
                "error": f"Unknown function: '{function_name}'. Available: {available}"
            }


# Add these functions at the END of agent.py (after the AGAPIAgent class)


async def run_agent_query(
    query: str,
    api_key: str = None,
    model: str = None,
    temperature: float = None,
    verbose: bool = False,
    return_dict: bool = False,
    show_tool_results: bool = False,
    use_tools: bool = True,
    auto_display_images: bool = False,
) -> Union[str, Dict[str, Any]]:
    """
    Async convenience function to run a query without creating an agent instance.

    Args:
        query: Natural language query
        api_key: API key (optional, uses default from config)
        model: Model name (optional, uses default)
        temperature: Temperature (optional, uses default)
        verbose: Print debug info
        return_dict: Return dict instead of text
        show_tool_results: Include raw tool results
        use_tools: Enable/disable tool calling
        auto_display_images: Automatically display SlakoNet images

    Returns:
        str or dict: Query result

    Example:
        result = await run_agent_query("Find SiC materials")
    """
    agent = AGAPIAgent(api_key=api_key, model=model, temperature=temperature)
    return await agent.query(
        query,
        verbose=verbose,
        return_dict=return_dict,
        show_tool_results=show_tool_results,
        use_tools=use_tools,
        auto_display_images=auto_display_images,
    )


def run_agent_query_sync(
    query: str,
    api_key: str = None,
    model: str = None,
    temperature: float = None,
    verbose: bool = False,
    render_html: bool = False,
    html_style: str = "bootstrap",
    max_show: int = 20,
    return_dict: bool = False,
    show_tool_results: bool = False,
    use_tools: bool = True,
    auto_display_images: bool = False,
) -> Union[str, Dict[str, Any]]:
    """
    Sync convenience function to run a query without creating an agent instance.

    Args:
        query: Natural language query
        api_key: API key (optional, uses default from config)
        model: Model name (optional, uses default)
        temperature: Temperature (optional, uses default)
        verbose: Print debug info
        render_html: Render as HTML in Jupyter
        html_style: "bootstrap" or "css"
        max_show: Max rows in tables
        return_dict: Return dict instead of text
        show_tool_results: Include raw tool results
        use_tools: Enable/disable tool calling
        auto_display_images: Automatically display SlakoNet images

    Returns:
        str or dict: Query result

    Example:
        result = run_agent_query_sync("Find SiC materials")
    """
    agent = AGAPIAgent(api_key=api_key, model=model, temperature=temperature)
    return agent.query_sync(
        query,
        verbose=verbose,
        render_html=render_html,
        html_style=html_style,
        max_show=max_show,
        return_dict=return_dict,
        show_tool_results=show_tool_results,
        use_tools=use_tools,
        auto_display_images=auto_display_images,
    )
