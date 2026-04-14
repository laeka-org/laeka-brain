"""Tests for laeka_brain_mcp.tools — mocked client calls."""
from __future__ import annotations

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from laeka_brain_mcp import tools as brain_tools
from laeka_brain_mcp.tools import (
    tool_consolidate,
    tool_query,
    tool_recall,
    tool_reflect,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CANONICAL_STUB = "[LAEKA BRAIN CANONICAL v0.3-en — cache_control: ephemeral]\n\nIntegrity.\n\nThis word is my root."


@pytest.fixture(autouse=True)
def patch_user_uuid(monkeypatch, tmp_path):
    """Always use a synthetic user_uuid so tests never touch ~/.config."""
    uuid_file = tmp_path / "user_uuid"
    uuid_file.write_text("test-user-uuid-1234\n")
    monkeypatch.setattr(
        "laeka_brain_mcp.tools.get_user_uuid",
        lambda: "test-user-uuid-1234",
    )
    monkeypatch.setattr(
        "laeka_brain_mcp.config.get_user_uuid",
        lambda: "test-user-uuid-1234",
    )


# ---------------------------------------------------------------------------
# test_query_returns_canonical_context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_returns_canonical_context(monkeypatch):
    """tool_query returns canonical text + question directive."""
    monkeypatch.setattr(
        brain_tools, "fetch_brain_identity",
        lambda **kw: _async(CANONICAL_STUB),
    )
    result = await tool_query("What does integrity mean in code?")
    assert CANONICAL_STUB in result
    assert "What does integrity mean in code?" in result
    assert "four lenses" in result


# ---------------------------------------------------------------------------
# test_reflect_returns_canonical_with_lenses_directive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reflect_returns_canonical_with_lenses_directive(monkeypatch):
    """tool_reflect includes canonical + mirror directive with MONADE etc."""
    monkeypatch.setattr(
        brain_tools, "fetch_brain_identity",
        lambda **kw: _async(CANONICAL_STUB),
    )
    result = await tool_reflect("I keep rewriting the same module from scratch.")
    assert CANONICAL_STUB in result
    assert "MONADE" in result
    assert "ARCHITECT" in result
    assert "mirror" in result.lower()
    assert "Do not give advice" in result
    assert "I keep rewriting the same module from scratch." in result


# ---------------------------------------------------------------------------
# test_consolidate_provisions_then_ingests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consolidate_provisions_then_ingests(monkeypatch):
    """When mini-brain is absent (ingest → None, identity → None), it provisions then ingests."""
    ingest_calls = []

    async def _ingest_first_fails_then_ok(**kw):
        ingest_calls.append(kw)
        if len(ingest_calls) == 1:
            return None  # simulate 404 on first attempt
        return {"ingested": True, "doc_id": "some-uuid"}

    async def _identity_none(user_uuid):
        return None  # mini-brain not provisioned

    async def _provision_ok(user_uuid):
        return {"provisioned": True, "client_id": "mini-brain-test", "user_uuid": user_uuid}

    monkeypatch.setattr(brain_tools, "ingest_mini_brain_chunk", _ingest_first_fails_then_ok)
    monkeypatch.setattr(brain_tools, "get_mini_brain_identity", _identity_none)
    monkeypatch.setattr(brain_tools, "provision_mini_brain", _provision_ok)

    result = await tool_consolidate("Solved the auth naming friction today.")
    assert "Mini-brain initialized" in result or "provisioned" in result.lower()
    assert len(ingest_calls) == 2  # first attempt + retry after provision


# ---------------------------------------------------------------------------
# test_consolidate_idempotent_when_mini_brain_exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consolidate_idempotent_when_mini_brain_exists(monkeypatch):
    """When mini-brain exists, consolidate succeeds on first ingest call."""
    ingest_calls = []

    async def _ingest_ok(**kw):
        ingest_calls.append(kw)
        return {"ingested": True, "doc_id": "abc-uuid"}

    monkeypatch.setattr(brain_tools, "ingest_mini_brain_chunk", _ingest_ok)
    # provision/identity should NOT be called.
    monkeypatch.setattr(
        brain_tools, "provision_mini_brain",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("provision called unexpectedly")),
    )

    result = await tool_consolidate("Refactored the ingestion pipeline cleanly.")
    assert "Consolidated" in result
    assert len(ingest_calls) == 1  # no retry


# ---------------------------------------------------------------------------
# test_recall_returns_chunks_count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recall_returns_chunks_count(monkeypatch):
    """tool_recall shows chunk count and born_on when mini-brain exists."""
    async def _identity_ok(user_uuid):
        return {
            "user_uuid": user_uuid,
            "client_id": "mini-brain-test",
            "born_on": "2026-04-14T10:00:00+00:00",
            "parent": "laeka-brain-core",
            "parent_version": "v0.3-en",
            "private_chunks_count": 7,
            "exists": True,
        }

    monkeypatch.setattr(brain_tools, "get_mini_brain_identity", _identity_ok)
    result = await tool_recall("What did I learn about auth modules?")
    assert "7 private chunks" in result
    assert "2026-04-14" in result
    assert "What did I learn about auth modules?" in result
    assert "Phase 4" in result


@pytest.mark.asyncio
async def test_recall_no_mini_brain(monkeypatch):
    """tool_recall gracefully handles unprovisionned mini-brain."""
    async def _identity_none(user_uuid):
        return None

    monkeypatch.setattr(brain_tools, "get_mini_brain_identity", _identity_none)
    result = await tool_recall("anything")
    assert "doesn't exist" in result or "not exist" in result or "doesn't exist" in result


# ---------------------------------------------------------------------------
# test_user_uuid_persists_to_xdg_config
# ---------------------------------------------------------------------------

def test_user_uuid_persists_to_xdg_config(tmp_path):
    """get_user_uuid writes and re-reads the same UUID from XDG config dir.

    Uses a subprocess so the XDG env var is clean — avoids autouse monkeypatch
    interference with the config module.
    """
    import subprocess, sys

    script = f"""
import os, sys
os.environ["XDG_CONFIG_HOME"] = {str(tmp_path)!r}
sys.path.insert(0, {str(os.path.join(os.path.dirname(__file__), '..', 'src'))!r})
import laeka_brain_mcp.config as config_mod
uuid1 = config_mod.get_user_uuid()
uuid2 = config_mod.get_user_uuid()
assert len(uuid1) == 36, f"bad uuid: {{uuid1!r}}"
assert uuid1 == uuid2, "uuid changed between calls"
uuid_file = os.path.join({str(tmp_path)!r}, "laeka-brain-mcp", "user_uuid")
assert os.path.exists(uuid_file), "file not created"
stored = open(uuid_file).read().strip()
assert stored == uuid1, f"stored {{stored!r}} != {{uuid1!r}}"
print("OK", uuid1)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("OK ")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import asyncio

def _async(value):
    """Return a coroutine that immediately returns value."""
    async def _coro(**kw):
        return value
    return _coro()
