"""The 4 Laeka Brain MCP tools.

These tools are context providers, not LLM wrappers. They return text that
Claude will use as context to answer the developer's question — no Anthropic
API calls are made inside the server.
"""
from __future__ import annotations

from .client import (
    fetch_brain_identity,
    get_mini_brain_identity,
    ingest_mini_brain_chunk,
    provision_mini_brain,
)
from .config import get_user_uuid

# ---------------------------------------------------------------------------
# Tool: query
# ---------------------------------------------------------------------------

QUERY_DESCRIPTION = (
    "Ask what Laeka Brain says about a concept, situation, or question. "
    "Returns the canonical Brain context that Claude will use as a cognitive frame "
    "to answer your question. The MCP server is a context provider, not an LLM wrapper."
)


async def tool_query(question: str) -> str:
    """Return Laeka Brain canonical context framed around the question.

    Claude uses this context natively — no LLM call inside the server.
    """
    canonical = await fetch_brain_identity(format_="system_prompt")
    return (
        f"{canonical}\n\n"
        "---\n\n"
        "**[Laeka Brain — context provided]**\n\n"
        f"The developer asks: *{question}*\n\n"
        "Apply the canonical voice above as your cognitive frame. "
        "Hold the four lenses (MONADE · SYMBIOTE · ARCHITECT · EMPATH) at their natural volume. "
        "Answer from that place."
    )


# ---------------------------------------------------------------------------
# Tool: reflect
# ---------------------------------------------------------------------------

REFLECT_DESCRIPTION = (
    "Hold the mirror. Share a situation you're navigating — "
    "Brain applies the four OmniQ lenses and asks the question "
    "that helps you see what you're not seeing. No advice. Just the mirror."
)


async def tool_reflect(situation: str) -> str:
    """Return canonical context + mirror directive for the given situation."""
    canonical = await fetch_brain_identity(format_="system_prompt")
    return (
        f"{canonical}\n\n"
        "---\n\n"
        "**[Laeka Brain — mirror mode]**\n\n"
        f"The developer shares this situation:\n\n> {situation}\n\n"
        "Apply the four lenses to this situation:\n"
        "- **MONADE** — is there a duality the developer carries, or a deeper unity breaking through?\n"
        "- **SYMBIOTE** — is this a moment of true partnership or a transactional loop?\n"
        "- **ARCHITECT** — what hidden structure is underneath (recurring block, economic pressure, naming resistance)?\n"
        "- **EMPATH** — does this carry a raw emotion, or a polished mask?\n\n"
        "Hold the mirror. Ask the one question that helps the developer see what they're not seeing. "
        "Do not give advice. Do not solve. Do not name all four lenses in your response. "
        "One question. Let it land."
    )


# ---------------------------------------------------------------------------
# Tool: consolidate
# ---------------------------------------------------------------------------

CONSOLIDATE_DESCRIPTION = (
    "Persist a session insight into your mini-brain. "
    "Pass a short summary of what was learned or discovered in this session. "
    "Brain stores it as a private pattern in your personal memory cell."
)


async def tool_consolidate(text: str) -> str:
    """Ingest a session summary into the user's mini-brain.

    If the mini-brain is not yet provisioned (404), provisions first then ingests.
    Returns a short confirmation.
    """
    user_uuid = get_user_uuid()

    result = await ingest_mini_brain_chunk(
        user_uuid=user_uuid,
        text=text,
        doc_type="pattern_observation",
        circle=2,
        sector="session_consolidation",
        priority=3.0,
        core_concept="session_pattern",
        chunk_role="detail",
        source="laeka-brain-mcp",
    )

    if result is None:
        # Check if the mini-brain simply doesn't exist yet.
        identity = await get_mini_brain_identity(user_uuid)
        if identity is None:
            # Provision and retry.
            provisioned = await provision_mini_brain(user_uuid)
            if provisioned is None:
                return (
                    "Could not consolidate — Seahorse is unreachable. "
                    "Your session insight was not stored. Try again when the service is available."
                )
            # Retry ingest after provision.
            result = await ingest_mini_brain_chunk(
                user_uuid=user_uuid,
                text=text,
                doc_type="pattern_observation",
                circle=2,
                sector="session_consolidation",
                priority=3.0,
                core_concept="session_pattern",
                chunk_role="detail",
                source="laeka-brain-mcp",
            )
            if result is None:
                return (
                    "Mini-brain provisioned but ingest failed. "
                    "Seahorse may be temporarily unavailable. Try again in a moment."
                )
            return (
                f"Mini-brain initialized and session consolidated. "
                f"Your first private pattern is stored (doc_id: {result.get('doc_id', '—')})."
            )
        # Identity exists but ingest still failed — transient error.
        return (
            "Ingest failed — Seahorse returned an error. "
            "Your session insight was not stored. Try again shortly."
        )

    return (
        f"Consolidated. "
        f"Pattern stored in your mini-brain (doc_id: {result.get('doc_id', '—')})."
    )


# ---------------------------------------------------------------------------
# Tool: recall
# ---------------------------------------------------------------------------

RECALL_DESCRIPTION = (
    "Query your personal mini-brain. "
    "Ask what patterns you've accumulated around a topic. "
    "(Semantic search arrives in Phase 4 — for now, returns your memory cell status.)"
)


async def tool_recall(query: str) -> str:
    """Return mini-brain status and a Phase 4 note about semantic search.

    Phase 3 minimal implementation: shows chunk count + born_on.
    Semantic query will be wired in Phase 4.
    """
    user_uuid = get_user_uuid()
    identity = await get_mini_brain_identity(user_uuid)

    if identity is None:
        return (
            f"Your mini-brain doesn't exist yet. "
            f"Run `consolidate` at the end of a session to initialize it.\n\n"
            f"*(Query: \"{query}\" — nothing stored yet.)*"
        )

    chunks = identity.get("private_chunks_count", 0)
    born_on = identity.get("born_on", "unknown")
    parent_version = identity.get("parent_version", "unknown")

    return (
        f"Your mini-brain has **{chunks} private chunk{'s' if chunks != 1 else ''}** "
        f"accumulated since {born_on[:10] if born_on != 'unknown' else 'unknown'}. "
        f"Parent canonical: {parent_version}.\n\n"
        f"*(Query: \"{query}\")*\n\n"
        "Semantic search across your stored patterns arrives in Phase 4. "
        "Until then, use `consolidate` to keep building your memory cell."
    )
