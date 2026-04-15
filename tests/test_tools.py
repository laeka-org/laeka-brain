"""Tests for laeka_brain.tools — mocked client calls."""
from __future__ import annotations

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from laeka_brain import tools as brain_tools
from laeka_brain.tools import (
    tool_consolidate,
    tool_query,
    tool_recall,
    tool_reflect,
)

# ---------------------------------------------------------------------------
# Shared helpers / stubs
# ---------------------------------------------------------------------------

def _make_search_response(results, total=10):
    """Build a minimal /v1/brain/mini/search response dict."""
    return {
        "results": results,
        "query": "test-query",
        "user_uuid": "test-user-uuid-1234",
        "total_chunks_in_brain": total,
    }


def _make_hit(score=0.87, text="Some stored insight about auth modules.", sector="session_consolidation", doc_type="pattern_observation", created_at="2026-04-14T10:00:00+00:00"):
    return {
        "doc_id": "test-doc-id",
        "text": text,
        "score": score,
        "doc_type": doc_type,
        "circle": 2,
        "sector": sector,
        "created_at": created_at,
    }


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
        "laeka_brain.tools.get_user_uuid",
        lambda: "test-user-uuid-1234",
    )
    monkeypatch.setattr(
        "laeka_brain.config.get_user_uuid",
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
    """When satellite is absent (ingest → None, identity → None), it provisions then ingests."""
    ingest_calls = []

    async def _ingest_first_fails_then_ok(**kw):
        ingest_calls.append(kw)
        if len(ingest_calls) == 1:
            return None  # simulate 404 on first attempt
        return {"ingested": True, "doc_id": "some-uuid"}

    async def _identity_none(user_uuid):
        return None  # satellite not provisioned

    async def _provision_ok(user_uuid):
        return {"provisioned": True, "client_id": "satellite-test", "user_uuid": user_uuid}

    monkeypatch.setattr(brain_tools, "ingest_satellite_chunk", _ingest_first_fails_then_ok)
    monkeypatch.setattr(brain_tools, "get_satellite_identity", _identity_none)
    monkeypatch.setattr(brain_tools, "provision_satellite", _provision_ok)

    result = await tool_consolidate("Solved the auth naming friction today.")
    assert "Satellite initialized" in result or "provisioned" in result.lower()
    assert len(ingest_calls) == 2  # first attempt + retry after provision


# ---------------------------------------------------------------------------
# test_consolidate_idempotent_when_mini_brain_exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consolidate_idempotent_when_mini_brain_exists(monkeypatch):
    """When satellite exists, consolidate succeeds on first ingest call."""
    ingest_calls = []

    async def _ingest_ok(**kw):
        ingest_calls.append(kw)
        return {"ingested": True, "doc_id": "abc-uuid"}

    monkeypatch.setattr(brain_tools, "ingest_satellite_chunk", _ingest_ok)
    # provision/identity should NOT be called.
    monkeypatch.setattr(
        brain_tools, "provision_satellite",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("provision called unexpectedly")),
    )

    result = await tool_consolidate("Refactored the ingestion pipeline cleanly.")
    assert "Consolidated" in result
    assert len(ingest_calls) == 1  # no retry


# ---------------------------------------------------------------------------
# test_recall_* — Phase 5a semantic search
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recall_calls_search_endpoint(monkeypatch):
    """tool_recall calls search_satellite with the user's query."""
    calls = []

    async def _search(user_uuid, query, k):
        calls.append({"user_uuid": user_uuid, "query": query, "k": k})
        return _make_search_response([_make_hit()])

    monkeypatch.setattr(brain_tools, "search_satellite", _search)
    await tool_recall("What did I learn about auth modules?")

    assert len(calls) == 1
    assert calls[0]["query"] == "What did I learn about auth modules?"
    assert calls[0]["user_uuid"] == "test-user-uuid-1234"
    assert calls[0]["k"] == 5


@pytest.mark.asyncio
async def test_recall_formats_results_as_markdown(monkeypatch):
    """tool_recall formats hits as numbered markdown with score, sector, doc_type, created."""
    hit = _make_hit(score=0.92, text="Auth naming friction is really a module boundary problem.", sector="session_consolidation", doc_type="pattern_observation", created_at="2026-04-10T08:00:00+00:00")

    async def _search(user_uuid, query, k):
        return _make_search_response([hit], total=5)

    monkeypatch.setattr(brain_tools, "search_satellite", _search)
    result = await tool_recall("auth modules")

    assert "Found **1 result**" in result
    assert "[score 0.92]" in result
    assert "Auth naming friction" in result
    assert "sector: session_consolidation" in result
    assert "doc_type: pattern_observation" in result
    assert "2026-04-10" in result
    assert "5 total chunks" in result


@pytest.mark.asyncio
async def test_recall_handles_404_gracefully(monkeypatch):
    """tool_recall falls back cleanly when search endpoint returns None (404 / not provisioned)."""
    async def _search_none(user_uuid, query, k):
        return None  # simulates 404 or network error

    async def _identity_none(user_uuid):
        return None  # satellite not provisioned

    monkeypatch.setattr(brain_tools, "search_satellite", _search_none)
    monkeypatch.setattr(brain_tools, "get_satellite_identity", _identity_none)

    result = await tool_recall("patterns about naming")
    assert "doesn't exist" in result or "not exist" in result


@pytest.mark.asyncio
async def test_recall_handles_empty_results(monkeypatch):
    """tool_recall handles search response with empty results list."""
    async def _search(user_uuid, query, k):
        return _make_search_response([], total=12)

    monkeypatch.setattr(brain_tools, "search_satellite", _search)
    result = await tool_recall("something obscure nobody ever stored")

    assert "No matches found" in result
    assert "something obscure nobody ever stored" in result
    assert "12" in result


@pytest.mark.asyncio
async def test_recall_includes_score_in_output(monkeypatch):
    """tool_recall includes the relevance score in the formatted output."""
    async def _search(user_uuid, query, k):
        return _make_search_response([
            _make_hit(score=0.75),
            _make_hit(score=0.61, text="A second insight."),
        ], total=20)

    monkeypatch.setattr(brain_tools, "search_satellite", _search)
    result = await tool_recall("anything")

    assert "[score 0.75]" in result
    assert "[score 0.61]" in result
    assert "Found **2 results**" in result


@pytest.mark.asyncio
async def test_recall_truncates_long_text_snippets(monkeypatch):
    """tool_recall truncates text snippets to 200 chars and appends ellipsis."""
    long_text = "A" * 250

    async def _search(user_uuid, query, k):
        return _make_search_response([_make_hit(text=long_text)])

    monkeypatch.setattr(brain_tools, "search_satellite", _search)
    result = await tool_recall("long text test")

    # The truncated text should appear with ellipsis, not the full 250 chars.
    assert "A" * 200 in result
    assert "A" * 201 not in result
    assert "…" in result


@pytest.mark.asyncio
async def test_recall_fallback_shows_chunk_count_when_search_unavailable(monkeypatch):
    """When search returns None but satellite exists, fallback shows chunk count."""
    async def _search_none(user_uuid, query, k):
        return None

    async def _identity_ok(user_uuid):
        return {
            "private_chunks_count": 7,
            "born_on": "2026-04-14T10:00:00+00:00",
        }

    monkeypatch.setattr(brain_tools, "search_satellite", _search_none)
    monkeypatch.setattr(brain_tools, "get_satellite_identity", _identity_ok)

    result = await tool_recall("auth patterns")
    assert "auth patterns" in result
    assert "7 private chunk" in result
    assert "semantic search isn't deployed yet" in result or "No matches found" in result


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
import laeka_brain.config as config_mod
uuid1 = config_mod.get_user_uuid()
uuid2 = config_mod.get_user_uuid()
assert len(uuid1) == 36, f"bad uuid: {{uuid1!r}}"
assert uuid1 == uuid2, "uuid changed between calls"
uuid_file = os.path.join({str(tmp_path)!r}, "laeka-brain", "user_uuid")
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
