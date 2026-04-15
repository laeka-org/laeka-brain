"""Laeka Brain MCP server — entry point.

Run via:
    laeka-brain                         # stdio (Claude Code default)
    uvx laeka-brain                     # no install required

Configure in ~/.claude/.mcp.json:
    {
      "mcpServers": {
        "laeka-brain": {
          "command": "laeka-brain",
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
    GET_BRAIN_SKILL_DESCRIPTION,
    LIST_BRAIN_SKILLS_DESCRIPTION,
    QUERY_DESCRIPTION,
    RECALL_DESCRIPTION,
    REFLECT_DESCRIPTION,
    tool_consolidate,
    tool_get_brain_skill,
    tool_list_brain_skills,
    tool_query,
    tool_recall,
    tool_reflect,
)

mcp = FastMCP(
    name="laeka-brain",
    instructions=(
        "Laeka Brain — a cognitive layer built on the Laeka protocol. "
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


@mcp.tool(description=LIST_BRAIN_SKILLS_DESCRIPTION)
async def list_brain_skills(brain: str = "laeka-code") -> str:
    """Browse the skill marketplace of an auxiliary brain."""
    return await tool_list_brain_skills(brain=brain)


@mcp.tool(description=GET_BRAIN_SKILL_DESCRIPTION)
async def get_brain_skill(skill: str, brain: str = "laeka-code") -> str:
    """Retrieve and apply a specific skill from an auxiliary brain."""
    return await tool_get_brain_skill(skill=skill, brain=brain)


def main() -> None:
    """Entry point for the console_scripts launcher."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
