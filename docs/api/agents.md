---
title: AGAPI Agents
---

# AGAPI Agents

The AGAPI Agent uses natural language to orchestrate multi-step materials science workflows.

## Setup

```python
import os
from agapi.agents import AGAPIAgent

agent = AGAPIAgent(api_key=os.environ.get("AGAPI_KEY"))
```

## Natural Language Queries

```python
# Simple property lookup
agent.query_sync("What is the bandgap of Silicon?")

# Database search
agent.query_sync("Show me all MgB2 polymorphs")
agent.query_sync("Find materials with bulk modulus > 200 GPa")

# Comparisons
agent.query_sync("Compare bandgaps across BN, AlN, GaN, InN")

# Predictions
agent.query_sync("Predict properties of JVASP-1002 with ALIGNN")

# Characterization
agent.query_sync("Identify the phase from this XRD pattern for Silicon")
agent.query_sync("Analyze this STEM image of a GaN thin film")

# Literature
agent.query_sync("Find recent papers on perovskite solar cells on arXiv")
```

## Multi-Step Workflows

The agent chains multiple tools automatically:

```python
agent.query_sync("""
1. Find all GaN materials in JARVIS-DFT
2. Get POSCAR for the most stable one
3. Make a 2x1x1 supercell
4. Substitute one Ga with Al
5. Generate powder XRD pattern
6. Optimize structure with ALIGNN-FF
7. Predict properties with ALIGNN
""", max_context_messages=20, verbose=True)
```

```python
agent.query_sync("""
Create a GaN/AlN heterostructure interface:
1. Find GaN (most stable)
2. Find AlN (most stable)
3. Generate (001)/(001) interface
4. Show POSCAR
""", max_context_messages=20, verbose=True)
```

## Supported LLM Backends

Set `model` when initializing the agent:

```python
agent = AGAPIAgent(
    api_key=os.environ.get("AGAPI_KEY"),
    model="openai/gpt-oss-20b"
)
```

| Model | Notes |
|-------|-------|
| `openai/gpt-oss-20b` | Default. Text only. |
| `gemma-4-26b` | Vision-capable. |
| `nvidia/nemotron-3-ultra-550b-a55b` | Largest; slowest per step. |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Reasoning model. |

The served set changes over time — `GET https://atomgpt.org/api/models` is
authoritative. Don't point `model` at the `mcp.*` entries listed there: those
already run the agent loop server-side, so using one as an orchestrator nests
two agents. Reach those through the
[chat endpoint](chat-endpoint.md) instead.

## Architecture

AGAPI implements a modular architecture separating the **reasoning layer** (LLM brain) from the **execution layer** (scientific tools and databases) through a unified REST API interface.

```
┌──────────────────┐
│  Natural Language │  ← user prompt
└────────┬─────────┘
         ▼
┌──────────────────┐
│   LLM Backend    │  ← GPT-OSS / Llama / Gemini / DeepSeek
│  (Reasoning)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  AGAPI Functions │  ← query_by_formula, alignn_predict, ...
│  (Execution)     │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  AtomGPT.org API │  ← JARVIS-DFT, ALIGNN, ALIGNN-FF, ...
│  (Data + Models) │
└──────────────────┘
```

!!! info "AGAPI Name"
    **AGAPI (ἀγάπη)** is a Greek word meaning *unconditional love*.
