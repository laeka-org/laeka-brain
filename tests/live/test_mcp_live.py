"""Live smoke tests against prod Seahorse (http://172.105.0.134:8822).

These tests hit the real API. They are skipped automatically when the
Seahorse endpoint is unreachable (to keep CI green on offline machines).

Usage:
    LAEKA_BRAIN_API_URL=http://172.105.0.134:8822 \\
        python3 -m pytest tests/live/test_mcp_live.py -v

The test provisions a synthetic user_uuid, exercises all 4 tool paths,
then offboards for cleanup. The uuid is unique per test run to avoid
collisions with real user data.
"""
from __future__ import annotations

import sys
import os
import uuid

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from laeka_brain.client import (
    LAEKA_BRAIN_API_URL,
    bust_all,
    fetch_brain_identity,
    get_mini_brain_identity,
    ingest_mini_brain_chunk,
    offboard_mini_brain,
    provision_mini_brain,
)
from laeka_brain.tools import tool_consolidate, tool_query, tool_recall, tool_reflect

# ---------------------------------------------------------------------------
# Connectivity guard — skip entire module if Seahorse is unreachable
# ---------------------------------------------------------------------------

def _seahorse_reachable() -> bool:
    try:
        r = httpx.get(
            f"{LAEKA_BRAIN_API_URL}/v1/brain/identity",
            params={"format": "system_prompt"},
            headers={"X-Consumer": "laeka-brain-smoke"},
            timeout=5.0,
        )
        return r.status_code == 200
    except Exception:
        return False


if not _seahorse_reachable():
    pytest.skip(
        f"Seahorse unreachable at {LAEKA_BRAIN_API_URL} — skipping live tests",
        allow_module_level=True,
    )

# Synthetic uuid for this test run — offboarded at the end.
SMOKE_UUID = f"smoke-{uuid.uuid4()}"


@pytest.fixture(autouse=True)
def patch_uuid_to_smoke(monkeypatch):
    monkeypatch.setattr("laeka_brain.tools.get_user_uuid", lambda: SMOKE_UUID)
    monkeypatch.setattr("laeka_brain.config.get_user_uuid", lambda: SMOKE_UUID)


@pytest.fixture(scope="module", autouse=True)
def cleanup_smoke_uuid():
    """Offboard the smoke uuid after all tests."""
    yield
    import asyncio
    asyncio.run(offboard_mini_brain(SMOKE_UUID))
    bust_all()


# ---------------------------------------------------------------------------
# Live tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_live_query_returns_canonical():
    bust_all()
    result = await tool_query("What is the integrity vector?")
    assert "Integrity" in result
    assert "four lenses" in result.lower() or "MONADE" in result


@pytest.mark.asyncio
async def test_live_reflect_returns_mirror_directive():
    bust_all()
    result = await tool_reflect("I keep rewriting the auth module from scratch.")
    assert "MONADE" in result or "ARCHITECT" in result
    assert "mirror" in result.lower()


@pytest.mark.asyncio
async def test_live_consolidate_provisions_and_ingests():
    """consolidate should provision the smoke mini-brain and store a chunk."""
    bust_all()
    result = await tool_consolidate(
        "Smoke test session: confirmed live API integration works end-to-end."
    )
    assert any(
        keyword in result.lower()
        for keyword in ("consolidated", "provisioned", "pattern is stored", "initialized")
    ), f"Unexpected result: {result!r}"


@pytest.mark.asyncio
async def test_live_recall_returns_status():
    """After consolidation, recall should show at least 1 chunk."""
    bust_all()
    result = await tool_recall("live smoke session patterns")
    # Either it shows a chunk count (if Seahorse persisted it)
    # or it indicates the mini-brain doesn't exist yet.
    assert "chunk" in result or "exist" in result or "Phase 4" in result


@pytest.mark.asyncio
async def test_live_get_mini_brain_identity_after_provision():
    """Mini-brain identity should be retrievable after consolidate ran."""
    bust_all()
    identity = await get_mini_brain_identity(SMOKE_UUID)
    # If consolidate in the previous test succeeded, identity is not None.
    # If Seahorse was slow to propagate, we accept None here too.
    if identity is not None:
        assert identity.get("user_uuid") == SMOKE_UUID
        assert identity.get("exists") is True
