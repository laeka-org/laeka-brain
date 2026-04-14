"""Tests for laeka_brain.client — mocked HTTP."""
from __future__ import annotations

import json
import pytest
import httpx

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from laeka_brain import client as brain_client
from laeka_brain.client import (
    bust_all,
    fetch_brain_identity,
    get_mini_brain_identity,
    ingest_mini_brain_chunk,
    offboard_mini_brain,
    provision_mini_brain,
    _FALLBACK_IDENTITY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _MockTransport(httpx.MockTransport):
    """Thin wrapper keeping the response queue ordered."""


def _make_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    idx = 0
    responses_list = responses

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal idx
        if idx >= len(responses_list):
            raise AssertionError(f"Unexpected request: {request.url}")
        resp = responses_list[idx]
        idx += 1
        return resp

    return httpx.MockTransport(handler)


def _json_resp(data: dict, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        headers={"Content-Type": "application/json"},
        content=json.dumps(data).encode(),
    )


def _text_resp(text: str, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status,
        headers={"Content-Type": "text/plain"},
        content=text.encode(),
    )


# ---------------------------------------------------------------------------
# test_client_handles_seahorse_down_gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_handles_seahorse_down_gracefully(monkeypatch):
    """When Seahorse is unreachable, fetch_brain_identity returns fallback."""
    bust_all()

    # Patch AsyncClient to raise a connection error.
    original_init = httpx.AsyncClient.__init__

    class _FailingClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, *a, **kw):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "AsyncClient", _FailingClient)
    result = await fetch_brain_identity()
    assert "Laeka Brain" in result
    assert "fallback" in result.lower() or "Integrity" in result
    bust_all()


# ---------------------------------------------------------------------------
# test_fetch_brain_identity_returns_system_prompt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_brain_identity_returns_system_prompt(monkeypatch):
    """fetch_brain_identity returns the server text on 200."""
    bust_all()
    expected = "[LAEKA BRAIN CANONICAL v0.3-en — cache_control: ephemeral]\n\nIntegrity."

    class _MockClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, **kw):
            return _text_resp(expected)

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await fetch_brain_identity()
    assert result == expected
    # Second call returns cache.
    result2 = await fetch_brain_identity()
    assert result2 == expected
    bust_all()


# ---------------------------------------------------------------------------
# test_provision_mini_brain_200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provision_mini_brain_200(monkeypatch):
    payload = {
        "provisioned": True,
        "client_id": "mini-brain-test-uuid",
        "user_uuid": "test-uuid",
        "parent": "laeka-brain-core",
        "parent_version": "v0.3-en",
        "born_on": "2026-04-14T10:00:00+00:00",
    }

    class _MockClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kw):
            return _json_resp(payload, 200)

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await provision_mini_brain("test-uuid")
    assert result is not None
    assert result["provisioned"] is True


# ---------------------------------------------------------------------------
# test_provision_mini_brain_409_idempotent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provision_mini_brain_409_idempotent(monkeypatch):
    """409 is treated as success (already exists)."""
    payload = {
        "provisioned": False,
        "client_id": "mini-brain-test-uuid",
        "user_uuid": "test-uuid",
        "parent": "laeka-brain-core",
        "parent_version": "v0.3-en",
        "born_on": "2026-04-14T10:00:00+00:00",
    }

    class _MockClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kw):
            return _json_resp(payload, 409)

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await provision_mini_brain("test-uuid")
    assert result is not None
    assert result["provisioned"] is False  # 409 body


# ---------------------------------------------------------------------------
# test_get_mini_brain_identity_404_returns_none
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_mini_brain_identity_404_returns_none(monkeypatch):
    """404 → returns None without raising."""
    bust_all()

    class _MockClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, **kw):
            return _json_resp({"exists": False, "user_uuid": "ghost"}, 404)

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await get_mini_brain_identity("ghost")
    assert result is None
    bust_all()


# ---------------------------------------------------------------------------
# test_ingest_mini_brain_chunk_200
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_mini_brain_chunk_200(monkeypatch):
    """Successful ingest returns the response dict."""
    bust_all()
    payload = {
        "ingested": True,
        "doc_id": "abc123-dashed-uuid",
        "point_id": "some-uuid",
        "embedding_dim": 1024,
    }

    class _MockClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kw):
            return _json_resp(payload, 200)

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await ingest_mini_brain_chunk(
        user_uuid="test-uuid",
        text="Session summary: solved auth friction.",
    )
    assert result is not None
    assert result["ingested"] is True
    bust_all()


# ---------------------------------------------------------------------------
# test_ingest_mini_brain_chunk_404_returns_none
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ingest_mini_brain_chunk_404_returns_none(monkeypatch):
    """404 ingest → None (mini-brain not provisioned)."""
    bust_all()

    class _MockClient:
        def __init__(self, *a, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, **kw):
            return _json_resp({"exists": False}, 404)

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)
    result = await ingest_mini_brain_chunk(
        user_uuid="unknown-uuid",
        text="This should not store.",
    )
    assert result is None
    bust_all()
