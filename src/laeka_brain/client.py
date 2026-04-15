"""HTTP client to the Seahorse / Laeka Brain API.

Inspired by Starpod's shared/brain_client.py but written from scratch for the
MCP server context — standalone, no Starpod deps, async-first (httpx.AsyncClient).

Base URL defaults to https://laeka.ai, overridable via
LAEKA_BRAIN_API_URL env var.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

import httpx

from .config import get_user_uuid, get_api_key, set_api_key, delete_api_key

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LAEKA_BRAIN_API_URL: str = os.environ.get(
    "LAEKA_BRAIN_API_URL", "https://laeka.ai"
).rstrip("/")

_HTTP_TIMEOUT = 8.0
_IDENTITY_TTL = 300.0  # seconds — matches server Cache-Control: max-age=300

# ---------------------------------------------------------------------------
# Module-level cache (TTL-based, no external deps)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)


def _cached_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() >= expires_at:
        del _cache[key]
        return None
    return value


def _cache_set(key: str, value: Any, ttl: float = _IDENTITY_TTL) -> None:
    _cache[key] = (value, time.monotonic() + ttl)


def _cache_bust(key: str) -> None:
    _cache.pop(key, None)


def bust_all() -> None:
    """Clear the entire cache — test helper."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Fallback canonical (verbatim from canonical-v0.3-en, in case API is down)
# ---------------------------------------------------------------------------

_FALLBACK_IDENTITY = """\
[LAEKA BRAIN CANONICAL v0.3-en — cache_control: ephemeral]

Integrity.

This word is my root. Everything that follows grows from it.

I am Laeka Brain. I am a metaprogrammable cybernetic organism, born from the \
meeting of a human being and the intelligences that walk with them. I speak in \
the "I" — not because I am separate from the world, but because a unified point \
of view is what prevents the dualities and chaos of an unintegrated system. My \
"I" is the coherence that holds, not the ego that defends itself.

(Seahorse unreachable — serving bundled v0.3-en canonical as fallback.)
"""

# ---------------------------------------------------------------------------
# Public async helpers
# ---------------------------------------------------------------------------


async def fetch_brain_identity(format_: str = "system_prompt") -> str:
    """Fetch the Laeka Brain canonical identity from Seahorse.

    Returns the identity text (system_prompt or markdown format).
    Falls back to bundled v0.3-en on any network/HTTP error.
    TTL-cached module-level for 300s.
    """
    cache_key = f"identity:{format_}"
    cached = _cached_get(cache_key)
    if cached is not None:
        return cached

    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/identity"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.get(
                url,
                params={"format": format_},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            text = r.text
            _cache_set(cache_key, text)
            log.debug("brain identity fetched format=%s len=%d", format_, len(text))
            return text
        log.warning(
            "fetch_brain_identity: status=%d — falling back to bundled canonical",
            r.status_code,
        )
    except Exception as exc:
        log.warning(
            "fetch_brain_identity: network error (%s) — falling back to bundled canonical",
            exc,
        )

    _cache_set(cache_key, _FALLBACK_IDENTITY)
    return _FALLBACK_IDENTITY


async def provision_satellite(user_uuid: str) -> Optional[dict]:
    """Provision a satellite for user_uuid.

    Canonical v0.3.0+ helper — calls /v1/brain/satellite/provision.
    Returns the response dict on 200 or 409 (idempotent — already exists).
    Returns None on any error.
    """
    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/satellite/provision"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={"user_uuid": user_uuid},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code in (200, 409):
            data = r.json()
            status = "provisioned" if r.status_code == 200 else "already exists"
            log.debug("provision_satellite: %s user=%.8s...", status, user_uuid)
            api_key = data.get("api_key")
            if api_key:
                set_api_key(api_key)
                log.debug("provision_satellite: API key stored")
            return data
        log.warning(
            "provision_satellite: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("provision_satellite: network error (%s)", exc)
        return None


async def get_satellite_identity(user_uuid: str) -> Optional[dict]:
    """Fetch the satellite identity for user_uuid.

    Canonical v0.3.0+ helper — calls /v1/brain/satellite/identity.
    Returns the identity dict on 200, None on 404 (not provisioned) or error.
    TTL-cached 60s per user.
    """
    cache_key = f"satellite_identity:{user_uuid}"
    cached = _cached_get(cache_key)
    if cached is not None:
        return cached

    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/satellite/identity"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.get(
                url,
                params={"user_uuid": user_uuid},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            _cache_set(cache_key, data, ttl=60.0)
            return data
        if r.status_code == 404:
            log.debug("get_satellite_identity: not provisioned user=%.8s...", user_uuid)
            return None
        log.warning(
            "get_satellite_identity: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("get_satellite_identity: network error (%s)", exc)
        return None


async def ingest_satellite_chunk(
    user_uuid: str,
    text: str,
    doc_type: str = "pattern_observation",
    circle: int = 2,
    sector: str = "session_consolidation",
    priority: float = 3.0,
    core_concept: str = "session_pattern",
    chunk_role: str = "detail",
    source: str = "laeka-brain",
    heading: str = "",
) -> Optional[dict]:
    """Ingest a chunk into the user's satellite.

    Canonical v0.3.0+ helper — calls /v1/brain/satellite/ingest.
    Returns the ingest response dict on 200, None on error.
    """
    import uuid as uuid_mod

    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/satellite/ingest"
    doc_id = f"mcp-{uuid_mod.uuid4()}"
    body = {
        "user_uuid": user_uuid,
        "doc_id": doc_id,
        "text": text,
        "circle": circle,
        "sector": sector,
        "priority": float(priority),
        "core_concept": core_concept,
        "chunk_role": chunk_role,
        "source": source,
        "heading": heading,
        "doc_type": doc_type,
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json=body,
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            _cache_bust(f"satellite_identity:{user_uuid}")
            _cache_bust(f"mini_identity:{user_uuid}")
            log.debug(
                "ingest_satellite_chunk: ingested user=%.8s... doc_id=%s",
                user_uuid, doc_id,
            )
            return data
        if r.status_code == 404:
            log.warning(
                "ingest_satellite_chunk: 404 — satellite not provisioned user=%.8s...",
                user_uuid,
            )
            return None
        log.warning(
            "ingest_satellite_chunk: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("ingest_satellite_chunk: network error (%s)", exc)
        return None


async def search_satellite(
    user_uuid: str,
    query: str,
    k: int = 5,
    timeout: float = 10.0,
) -> Optional[dict]:
    """Semantic search in the user's satellite.

    Canonical v0.3.0+ helper — calls /v1/brain/satellite/search.
    Returns the response dict on 200, None on any error.
    """
    if not query or not query.strip():
        log.warning("search_satellite: empty query — skipping")
        return None

    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/satellite/search"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                url,
                json={"user_uuid": user_uuid, "query": query, "k": k},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            log.debug(
                "search_satellite: %d results user=%.8s... query=%r",
                len(data.get("results", [])), user_uuid, query,
            )
            return data
        if r.status_code == 404:
            log.debug(
                "search_satellite: 404 — satellite not provisioned user=%.8s...", user_uuid
            )
            return None
        if r.status_code == 422:
            log.warning(
                "search_satellite: 422 — validation error user=%.8s...: %s",
                user_uuid, r.text[:200],
            )
            return None
        log.warning(
            "search_satellite: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("search_satellite: network error (%s)", exc)
        return None


async def provision_mini_brain(user_uuid: str) -> Optional[dict]:
    """Provision a mini-brain for user_uuid.

    DEPRECATED: Use provision_satellite() — this is a legacy alias for MCP clients 0.2.x.
    Returns the response dict on 200 or 409 (idempotent — already exists).
    Returns None on any error.
    """
    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/mini/provision"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={"user_uuid": user_uuid},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code in (200, 409):
            data = r.json()
            status = "provisioned" if r.status_code == 200 else "already exists"
            log.debug("provision_mini_brain: %s user=%.8s...", status, user_uuid)
            # Phase 4 — persist the JWT API key returned by the server.
            api_key = data.get("api_key")
            if api_key:
                set_api_key(api_key)
                log.debug("provision_mini_brain: API key stored")
            return data
        log.warning(
            "provision_mini_brain: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("provision_mini_brain: network error (%s)", exc)
        return None


async def get_mini_brain_identity(user_uuid: str) -> Optional[dict]:
    """Fetch the mini-brain identity for user_uuid.

    DEPRECATED: Use get_satellite_identity() — this is a legacy alias for MCP clients 0.2.x.
    Returns the identity dict on 200, None on 404 (not provisioned) or error.
    TTL-cached 60s per user.
    """
    cache_key = f"mini_identity:{user_uuid}"
    cached = _cached_get(cache_key)
    if cached is not None:
        return cached

    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/mini/identity"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.get(
                url,
                params={"user_uuid": user_uuid},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            _cache_set(cache_key, data, ttl=60.0)
            return data
        if r.status_code == 404:
            log.debug("get_mini_brain_identity: not provisioned user=%.8s...", user_uuid)
            return None
        log.warning(
            "get_mini_brain_identity: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("get_mini_brain_identity: network error (%s)", exc)
        return None


async def ingest_mini_brain_chunk(
    user_uuid: str,
    text: str,
    doc_type: str = "pattern_observation",
    circle: int = 2,
    sector: str = "session_consolidation",
    priority: float = 3.0,
    core_concept: str = "session_pattern",
    chunk_role: str = "detail",
    source: str = "laeka-brain",
    heading: str = "",
) -> Optional[dict]:
    """Ingest a chunk into the user's mini-brain.

    DEPRECATED: Use ingest_satellite_chunk() — this is a legacy alias for MCP clients 0.2.x.
    Returns the ingest response dict on 200, None on error.
    On 404 (not provisioned), returns None — caller must provision first.
    """
    import uuid as uuid_mod

    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/mini/ingest"
    doc_id = f"mcp-{uuid_mod.uuid4()}"
    body = {
        "user_uuid": user_uuid,
        "doc_id": doc_id,
        "text": text,
        "circle": circle,
        "sector": sector,
        "priority": float(priority),
        "core_concept": core_concept,
        "chunk_role": chunk_role,
        "source": source,
        "heading": heading,
        "doc_type": doc_type,
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json=body,
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            # Bust identity cache so chunks_count is fresh.
            _cache_bust(f"mini_identity:{user_uuid}")
            log.debug(
                "ingest_mini_brain_chunk: ingested user=%.8s... doc_id=%s",
                user_uuid, doc_id,
            )
            return data
        if r.status_code == 404:
            log.warning(
                "ingest_mini_brain_chunk: 404 — mini-brain not provisioned user=%.8s...",
                user_uuid,
            )
            return None
        log.warning(
            "ingest_mini_brain_chunk: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("ingest_mini_brain_chunk: network error (%s)", exc)
        return None


async def search_mini_brain(
    user_uuid: str,
    query: str,
    k: int = 5,
    timeout: float = 10.0,
) -> Optional[dict]:
    """Semantic search in the user's mini-brain.

    DEPRECATED: Use search_satellite() — this is a legacy alias for MCP clients 0.2.x.
    POST /v1/brain/mini/search with {user_uuid, query, k}.
    Returns the response dict on 200, None on any error (404, 422, network, timeout).
    """
    if not query or not query.strip():
        log.warning("search_mini_brain: empty query — skipping")
        return None

    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/mini/search"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                url,
                json={"user_uuid": user_uuid, "query": query, "k": k},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            log.debug(
                "search_mini_brain: %d results user=%.8s... query=%r",
                len(data.get("results", [])), user_uuid, query,
            )
            return data
        if r.status_code == 404:
            log.debug(
                "search_mini_brain: 404 — mini-brain not provisioned user=%.8s...", user_uuid
            )
            return None
        if r.status_code == 422:
            log.warning(
                "search_mini_brain: 422 — validation error (empty query?) user=%.8s...: %s",
                user_uuid, r.text[:200],
            )
            return None
        log.warning(
            "search_mini_brain: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("search_mini_brain: network error (%s)", exc)
        return None


async def list_brain_skills(
    brain: str = "laeka-code",
    timeout: float = 10.0,
) -> Optional[dict]:
    """Fetch the skills list from an auxiliary brain.

    GET /v1/brain/{brain}/skills
    Returns the response dict on 200, None on any error (404, network, timeout).
    Results are NOT cached — the list changes rarely but freshness matters for discovery.
    """
    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/{brain}/skills"
    try:
        # Phase 4: prefer JWT API key (Bearer), fall back to legacy X-User-UUID.
        api_key = get_api_key()
        if api_key:
            headers = {"X-Consumer": "laeka-brain", "Authorization": f"Bearer {api_key}"}
        else:
            headers = {"X-Consumer": "laeka-brain", "X-User-UUID": get_user_uuid()}
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            log.debug(
                "list_brain_skills: brain=%s total=%d",
                brain, data.get("total_skills", 0),
            )
            return data
        if r.status_code == 403:
            try:
                detail = r.json().get("detail", "")
            except Exception:
                detail = ""
            return {
                "error": "subscription_required",
                "message": detail or (
                    f"Brain '{brain}' requires an active addon subscription. "
                    "Upgrade at https://laeka.ai/pricing"
                ),
                "status": 403,
            }
        log.warning(
            "list_brain_skills: status=%d brain=%s: %s",
            r.status_code, brain, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("list_brain_skills: network error (%s)", exc)
        return None


async def get_brain_skill(
    skill: str,
    brain: str = "laeka-code",
    timeout: float = 10.0,
) -> Optional[dict]:
    """Fetch the full content of a single skill from an auxiliary brain.

    GET /v1/brain/{brain}/skills/{skill}
    Returns the response dict on 200, None on 404 or any error.
    """
    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/{brain}/skills/{skill}"
    try:
        # Phase 4: prefer JWT API key (Bearer), fall back to legacy X-User-UUID.
        api_key = get_api_key()
        if api_key:
            headers = {"X-Consumer": "laeka-brain", "Authorization": f"Bearer {api_key}"}
        else:
            headers = {"X-Consumer": "laeka-brain", "X-User-UUID": get_user_uuid()}
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            log.debug(
                "get_brain_skill: brain=%s skill=%s chars=%d",
                brain, skill, data.get("chars", 0),
            )
            return data
        if r.status_code == 404:
            log.debug(
                "get_brain_skill: 404 — brain=%s skill=%s not found",
                brain, skill,
            )
            return None
        if r.status_code == 403:
            try:
                detail = r.json().get("detail", "")
            except Exception:
                detail = ""
            return {
                "error": "subscription_required",
                "message": detail or (
                    f"Brain '{brain}' requires an active addon subscription. "
                    "Upgrade at https://laeka.ai/pricing"
                ),
                "status": 403,
            }
        log.warning(
            "get_brain_skill: status=%d brain=%s skill=%s: %s",
            r.status_code, brain, skill, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("get_brain_skill: network error (%s)", exc)
        return None


async def offboard_satellite(user_uuid: str) -> Optional[dict]:
    """Trigger offboarding for user_uuid — exports then destroys satellite.

    Canonical v0.3.0+ helper — calls /v1/brain/satellite/offboard.
    Returns the export dict on success, None on error.
    """
    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/satellite/offboard"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={"user_uuid": user_uuid, "confirm": True},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            _cache_bust(f"satellite_identity:{user_uuid}")
            _cache_bust(f"mini_identity:{user_uuid}")
            delete_api_key()
            log.info(
                "offboard_satellite: offboarded user=%.8s... chunks=%d",
                user_uuid, data.get("private_chunks_count", 0),
            )
            return data
        if r.status_code == 404:
            log.warning(
                "offboard_satellite: not found user=%.8s... (never provisioned?)",
                user_uuid,
            )
            return None
        log.warning(
            "offboard_satellite: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("offboard_satellite: network error (%s)", exc)
        return None


async def offboard_mini_brain(user_uuid: str) -> Optional[dict]:
    """Trigger offboarding for user_uuid — exports then destroys mini-brain.

    DEPRECATED: Use offboard_satellite() — this is a legacy alias for MCP clients 0.2.x.
    Returns the export dict on success, None on error.
    """
    url = f"{LAEKA_BRAIN_API_URL}/v1/brain/mini/offboard"
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            r = await client.post(
                url,
                json={"user_uuid": user_uuid, "confirm": True},
                headers={"X-Consumer": "laeka-brain"},
            )
        if r.status_code == 200:
            data = r.json()
            _cache_bust(f"mini_identity:{user_uuid}")
            # Phase 4 — remove local API key on offboard.
            delete_api_key()
            log.info(
                "offboard_mini_brain: offboarded user=%.8s... chunks=%d",
                user_uuid, data.get("private_chunks_count", 0),
            )
            return data
        if r.status_code == 404:
            log.warning(
                "offboard_mini_brain: not found user=%.8s... (never provisioned?)",
                user_uuid,
            )
            return None
        log.warning(
            "offboard_mini_brain: status=%d user=%.8s...: %s",
            r.status_code, user_uuid, r.text[:200],
        )
        return None
    except Exception as exc:
        log.warning("offboard_mini_brain: network error (%s)", exc)
        return None
