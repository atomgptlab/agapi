---
title: Chat Endpoint
---

# OpenAI-Compatible Chat Endpoint

Besides the per-app REST endpoints, AtomGPT.org serves an **OpenAI-compatible chat
API**. Any client that speaks the OpenAI chat protocol can talk to the AtomGPT
agent — no MCP support required.

```
https://atomgpt.org/api
```

Authentication is the same `sk-…` key used everywhere else:

```
Authorization: Bearer YOUR_API_KEY
```

Get one at [AtomGPT.org](https://atomgpt.org) → Settings → Account → API Keys.

## Models

`GET /api/models` returns the live list. The two `mcp.*` entries run the full
AtomGPT agent **server-side**, so the materials tools are already attached — the
client sees a plain chat model.

| Model | Backend | Tools | Notes |
|-------|---------|-------|-------|
| `mcp.gemma` | gemma-4-26b | yes | Vision-capable |
| `mcp.gptoss` | gpt-oss-20b | yes | Text only |
| `gemma-4-26b` | gemma-4-26b | no | Raw model |
| `openai/gpt-oss-20b` | gpt-oss-20b | no | Raw model |

## curl

```bash
curl https://atomgpt.org/api/chat/completions \
  -H "Authorization: Bearer $AGAPI_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "mcp.gemma", "stream": true,
       "messages": [{"role": "user", "content": "bandgap of GaN"}]}'
```

Both `stream: true` and `stream: false` are supported.

## Python (`openai` SDK)

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://atomgpt.org/api",
    api_key=os.environ.get("AGAPI_KEY"),
)

resp = client.chat.completions.create(
    model="mcp.gemma",
    messages=[{"role": "user", "content": "bandgap of GaN"}],
    timeout=300,
)
print(resp.choices[0].message.content)
```

## opencode

Add a provider to `~/.config/opencode/opencode.json`:

```json
{
  "provider": {
    "atomgpt": {
      "name": "AtomGPT",
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "baseURL": "https://atomgpt.org/api",
        "apiKey": "YOUR_SK_KEY_HERE"
      },
      "models": {
        "mcp.gemma": { "name": "AtomGPT Agent (materials)" }
      }
    }
  }
}
```

Then:

```bash
opencode --model atomgpt/mcp.gemma
```

The same block works for LibreChat, Continue, and anything else built on
`@ai-sdk/openai-compatible`.

## Timeouts

The agent completes its whole tool loop before answering. A question that
triggers ALIGNN-FF relaxation or a SlakoNet band structure can take a minute or
more, so set a generous client timeout and prefer streaming.

## Relation to `AGAPIAgent`

[`AGAPIAgent`](agents.md) is a client of this same endpoint — it points an
`AsyncOpenAI` instance at `https://atomgpt.org/api` and runs the tool loop
locally, in your process, which is what makes each step visible and scriptable.
The `mcp.*` models run that loop on the server instead. Use `AGAPIAgent` when you
want Python-level control; use this endpoint when you want an existing chat
client to reach the tools.
