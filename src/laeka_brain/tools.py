"""The 4 Laeka Brain MCP tools.

These tools are context providers, not LLM wrappers. They return text that
Claude will use as context to answer the developer's question — no Anthropic
API calls are made inside the server.
"""
from __future__ import annotations

from .client import (
    fetch_brain_identity,
    get_brain_skill,
    get_satellite_identity,
    ingest_satellite_chunk,
    list_brain_skills,
    provision_satellite,
    search_satellite,
    # Legacy aliases — kept for backward compat with MCP clients 0.2.x
    get_mini_brain_identity,
    ingest_mini_brain_chunk,
    provision_mini_brain,
    search_mini_brain,
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
    "Brain applies the four Laeka lenses and asks the question "
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
    "Persist a session insight into your satellite — your private vector memory "
    "connected to the Laeka Brain canonical. "
    "Pass a short summary of what was learned or discovered in this session. "
    "Brain stores it as a private pattern in your personal satellite."
)


async def tool_consolidate(text: str) -> str:
    """Ingest a session summary into the user's satellite.

    If the satellite is not yet provisioned (404), provisions first then ingests.
    Returns a short confirmation.
    """
    user_uuid = get_user_uuid()

    result = await ingest_satellite_chunk(
        user_uuid=user_uuid,
        text=text,
        doc_type="pattern_observation",
        circle=2,
        sector="session_consolidation",
        priority=3.0,
        core_concept="session_pattern",
        chunk_role="detail",
        source="laeka-brain",
    )

    if result is None:
        # Check if the satellite simply doesn't exist yet.
        identity = await get_satellite_identity(user_uuid)
        if identity is None:
            # Provision and retry.
            provisioned = await provision_satellite(user_uuid)
            if provisioned is None:
                return (
                    "Could not consolidate — Seahorse is unreachable. "
                    "Your session insight was not stored. Try again when the service is available."
                )
            # Retry ingest after provision.
            result = await ingest_satellite_chunk(
                user_uuid=user_uuid,
                text=text,
                doc_type="pattern_observation",
                circle=2,
                sector="session_consolidation",
                priority=3.0,
                core_concept="session_pattern",
                chunk_role="detail",
                source="laeka-brain",
            )
            if result is None:
                return (
                    "Satellite provisioned but ingest failed. "
                    "Seahorse may be temporarily unavailable. Try again in a moment."
                )
            return (
                f"Satellite initialized and session consolidated. "
                f"Your first private pattern is stored (doc_id: {result.get('doc_id', '—')})."
            )
        # Identity exists but ingest still failed — transient error.
        return (
            "Ingest failed — Seahorse returned an error. "
            "Your session insight was not stored. Try again shortly."
        )

    return (
        f"Consolidated. "
        f"Pattern stored in your satellite (doc_id: {result.get('doc_id', '—')})."
    )


# ---------------------------------------------------------------------------
# Tool: recall
# ---------------------------------------------------------------------------

RECALL_DESCRIPTION = (
    "Semantic search in your satellite — your private vector memory. "
    "Find patterns, conversations, or insights you've consolidated previously."
)

_RECALL_TEXT_MAX_CHARS = 200


# ---------------------------------------------------------------------------
# Tool: list_brain_skills
# ---------------------------------------------------------------------------

LIST_BRAIN_SKILLS_DESCRIPTION = (
    "Browse the skill marketplace of an auxiliary brain. "
    "Returns a formatted list of available skills with name, category, legacy name, "
    "and a short summary. Default brain is 'laeka-code' (the Laeka Code coder brain). "
    "Use get_brain_skill to retrieve the full content of a specific skill."
)


async def tool_list_brain_skills(brain: str = "laeka-code") -> str:
    """List all skills available in an auxiliary brain.

    Returns a markdown-formatted catalogue sorted by category then name.
    Falls back gracefully if the brain store is unavailable.
    """
    response = await list_brain_skills(brain=brain)

    if response is None:
        return (
            f"Could not retrieve skills for brain '{brain}'. "
            "The brain store may be unavailable or the brain ID may be incorrect. "
            "Known auxiliary brains: laeka-code."
        )

    total = response.get("total_skills", 0)
    skills = response.get("skills", [])

    if not skills:
        return f"Brain '{brain}' has no skills indexed yet. Run the ingest script first."

    lines = [f"## {brain} — {total} skill{'s' if total != 1 else ''} available\n"]
    current_category = None
    for skill in skills:
        category = skill.get("category", "—")
        name = skill.get("name", "—")
        legacy = skill.get("legacy_name", "")
        summary = skill.get("summary", "")
        chars = skill.get("chars", 0)

        if category != current_category:
            lines.append(f"\n### {category}\n")
            current_category = category

        legacy_note = f" *(was: {legacy})*" if legacy else ""
        lines.append(f"- **{name}**{legacy_note} — {summary} `[{chars} chars]`")

    lines.append(
        f"\n\n*Use `get_brain_skill(brain=\"{brain}\", skill=\"<name>\")` to apply any skill.*"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_brain_skill
# ---------------------------------------------------------------------------

GET_BRAIN_SKILL_DESCRIPTION = (
    "Retrieve the full content of a specific skill from an auxiliary brain. "
    "Returns the rebranded skill markdown — ready to apply as a cognitive framework. "
    "Use list_brain_skills first to discover available skill names. "
    "Default brain is 'laeka-code'. "
    "Example: get_brain_skill(skill='systematic-debugging') retrieves the root-cause "
    "debugging protocol."
)


async def tool_get_brain_skill(skill: str, brain: str = "laeka-code") -> str:
    """Retrieve the full content of a skill from an auxiliary brain.

    Returns the rebranded skill content as markdown, prefixed with metadata.
    Falls back gracefully if the skill is not found.
    """
    response = await get_brain_skill(skill=skill, brain=brain)

    if response is None:
        return (
            f"Skill '{skill}' not found in brain '{brain}'. "
            f"Use list_brain_skills(brain=\"{brain}\") to see available skills."
        )

    name = response.get("name", skill)
    category = response.get("category", "—")
    legacy = response.get("legacy_name", "")
    content = response.get("content", "")
    chars = response.get("chars", 0)

    legacy_note = f"\n**Legacy name:** {legacy}" if legacy else ""
    header = (
        f"## Skill: {name}\n"
        f"**Brain:** {brain}  \n"
        f"**Category:** {category}{legacy_note}  \n"
        f"**Size:** {chars} chars\n\n"
        "---\n\n"
    )
    return header + content


async def tool_recall(query: str) -> str:
    """Semantic search in the user's satellite using /v1/brain/satellite/search.

    Falls back gracefully if the endpoint is not yet live or returns no results.
    """
    user_uuid = get_user_uuid()

    response = await search_satellite(user_uuid=user_uuid, query=query, k=5)

    if response is None:
        # Endpoint not live yet or satellite not provisioned — try identity for context.
        identity = await get_satellite_identity(user_uuid)
        if identity is None:
            return (
                f"Your satellite doesn't exist yet. "
                f"Run `consolidate` at the end of a session to initialize it.\n\n"
                f"*(Query: \"{query}\" — nothing stored yet.)*"
            )
        chunks = identity.get("private_chunks_count", 0)
        born_on = identity.get("born_on", "unknown")
        born_on_short = born_on[:10] if born_on != "unknown" else "unknown"
        return (
            f'No matches found in your satellite for "{query}". '
            f"(Or semantic search isn't deployed yet — try again in a few minutes.)\n\n"
            f"Your satellite has **{chunks} private chunk{'s' if chunks != 1 else ''}** "
            f"accumulated since {born_on_short}."
        )

    results = response.get("results", [])
    total = response.get("total_chunks_in_brain", 0)

    if not results:
        return (
            f'No matches found in your satellite for "{query}".\n\n'
            f"Your satellite has **{total} private chunk{'s' if total != 1 else ''}** stored. "
            "Try a different query or use `consolidate` to add more patterns."
        )

    lines = [f'Found **{len(results)} result{"s" if len(results) != 1 else ""}** in your satellite for "{query}":\n']
    for i, hit in enumerate(results, start=1):
        score = hit.get("score", 0.0)
        text = hit.get("text", "")
        if len(text) > _RECALL_TEXT_MAX_CHARS:
            text = text[:_RECALL_TEXT_MAX_CHARS].rstrip() + "…"
        sector = hit.get("sector", "—")
        doc_type = hit.get("doc_type", "—")
        created_at = (hit.get("created_at") or "—")[:10]
        lines.append(
            f"{i}. [score {score:.2f}] {text}\n"
            f"   sector: {sector}, doc_type: {doc_type}, created: {created_at}\n"
        )

    if total:
        lines.append(f"\n*{total} total chunk{'s' if total != 1 else ''} in your satellite.*")

    return "\n".join(lines)
