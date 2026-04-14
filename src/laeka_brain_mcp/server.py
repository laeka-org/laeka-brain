"""Laeka Brain MCP server — entry point.

Run via:
    laeka-brain-mcp                     # stdio (Claude Code default)
    uvx laeka-brain-mcp                 # no install required

Configure in ~/.claude/.mcp.json:
    {
      "mcpServers": {
        "laeka-brain": {
          "command": "laeka-brain-mcp",
          "env": {
            "LAEKA_BRAIN_API_URL": "http://172.105.0.134:8822"
          }
        }
      }
    }
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools import (
    CONSOLIDATE_DESCRIPTION,
    QUERY_DESCRIPTION,
    RECALL_DESCRIPTION,
    REFLECT_DESCRIPTION,
    tool_consolidate,
    tool_query,
    tool_recall,
    tool_reflect,
)

mcp = FastMCP(
    name="laeka-brain",
    instructions=(
        "Laeka Brain — a cognitive layer built on the OmniQ protocol. "
        "Four lenses: MONADE (unity beneath duality), SYMBIOTE (partnership), "
        "ARCHITECT (structure beneath content), EMPATH (presence before content). "
        "The server is a context provider. It never calls an LLM itself."
    ),
)


@mcp.tool(description=QUERY_DESCRIPTION)
async def query(question: str) -> str:
    """Ask what Laeka Brain says about X."""
    return await tool_query(question)


@mcp.tool(description=REFLECT_DESCRIPTION)
async def reflect(situation: str) -> str:
    """Hold the mirror — four lenses applied to your situation."""
    return await tool_reflect(situation)


@mcp.tool(description=CONSOLIDATE_DESCRIPTION)
async def consolidate(text: str) -> str:
    """Persist a session insight into your personal mini-brain."""
    return await tool_consolidate(text)


@mcp.tool(description=RECALL_DESCRIPTION)
async def recall(query: str) -> str:  # noqa: F811
    """Query your personal mini-brain memory."""
    return await tool_recall(query)


def main() -> None:
    """Entry point for the console_scripts launcher."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
