"""Single-source-of-truth registry for AGAPI tools.

Every surface that exposes tools to an LLM (MCP server, ChatGPT Custom GPT
Actions OpenAPI, the /connect documentation page, the SYSTEM_PROMPT
catalog) reads from `manifest.TOOLS`. Add a new tool by appending one
`Tool(...)` entry there — every surface picks it up on next restart.

See `manifest.Tool` for the entry shape and `categories.CATEGORIES` for
the human-readable group labels used by docs and the /connect page.
"""
from .manifest import TOOLS, Tool, by_id, for_surface
from .categories import CATEGORIES, ordered_categories

__all__ = [
    "TOOLS",
    "Tool",
    "by_id",
    "for_surface",
    "CATEGORIES",
    "ordered_categories",
]
