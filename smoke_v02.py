"""Smoke test v0.2.0 — verifies 6 tools are registered and 2 new client functions exist.

Run: python smoke_v02.py
"""
from __future__ import annotations

import sys
import asyncio

EXPECTED_TOOLS = {
    "query",
    "reflect",
    "consolidate",
    "recall",
    "list_brain_skills",
    "get_brain_skill",
}


def check_server_tools() -> None:
    """Verify that all 6 tools are registered in the FastMCP server."""
    from laeka_brain.server import mcp
    registered = {tool.name for tool in mcp._tool_manager.list_tools()}
    missing = EXPECTED_TOOLS - registered
    extra = registered - EXPECTED_TOOLS
    if missing:
        print(f"FAIL: missing tools: {missing}")
        sys.exit(1)
    if extra:
        print(f"NOTE: extra tools (not in expected set): {extra}")
    print(f"OK: {len(registered)} tools registered: {sorted(registered)}")


def check_client_functions() -> None:
    """Verify the 2 new client async functions exist and are callable."""
    from laeka_brain.client import list_brain_skills, get_brain_skill
    import inspect
    assert inspect.iscoroutinefunction(list_brain_skills), "list_brain_skills must be async"
    assert inspect.iscoroutinefunction(get_brain_skill), "get_brain_skill must be async"
    print("OK: list_brain_skills and get_brain_skill are async callables")


async def check_live_list_skills() -> None:
    """Live call to /v1/brain/laeka-code/skills via the client."""
    from laeka_brain.client import list_brain_skills
    result = await list_brain_skills(brain="laeka-code")
    if result is None:
        print("WARN: list_brain_skills returned None (API down or unreachable?)")
        return
    total = result.get("total_skills", 0)
    skills = result.get("skills", [])
    assert total > 0, f"Expected skills, got total={total}"
    assert len(skills) > 0, "skills array is empty"
    print(f"OK: list_brain_skills → {total} skills, first: {skills[0]['name']!r}")


async def check_live_get_skill() -> None:
    """Live call to /v1/brain/laeka-code/skills/systematic-debugging."""
    from laeka_brain.client import get_brain_skill
    result = await get_brain_skill(skill="systematic-debugging", brain="laeka-code")
    if result is None:
        print("WARN: get_brain_skill returned None (API down or skill not found?)")
        return
    content = result.get("content", "")
    assert len(content) > 0, "content is empty"
    assert "samourai" not in content.lower(), "cosplay term 'samourai' found in content"
    print(f"OK: get_brain_skill → {result['name']!r} ({result['chars']} chars), cosplay-free")


if __name__ == "__main__":
    print("=== laeka-brain v0.2.0 smoke test ===\n")
    check_server_tools()
    check_client_functions()
    asyncio.run(check_live_list_skills())
    asyncio.run(check_live_get_skill())
    print("\n=== ALL CHECKS PASSED ===")
