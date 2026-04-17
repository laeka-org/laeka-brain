<div align="right">

[![Website](https://img.shields.io/badge/laeka.ai-Visit-2D2A24?style=flat-square)](https://laeka.ai) [![Lab](https://img.shields.io/badge/laeka.org-Lab-C8A96E?style=flat-square)](https://laeka.org) [![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

</div>

# laeka-brain

A cognitive layer for the AI you already use.

> **Website:** [laeka.ai](https://laeka.ai) · **Research Lab:** [laeka.org](https://laeka.org) · **License:** MIT

This MCP server connects your Claude Code environment to Laeka Brain — the Laeka protocol made available through six tools. It is a context provider. It does not call an LLM. It does not store your conversations. It returns context that Claude uses natively.

**Open source by design.** All code here is MIT-licensed. The cognitive infrastructure is open because a private cognitive layer would contradict what we're building. What we sell commercially at [laeka.ai](https://laeka.ai) is hosted convenience, curated brain marketplace access, and enterprise support — not the code itself. See [Commercial support](#commercial-support) below.

---

## Contents

- [What it is](#what-it-is)
- [How to install](#how-to-install)
- [How to configure](#how-to-configure)
- [The 4 tools](#the-4-tools)
- [How to leave](#how-to-leave)
- [Commercial support](#commercial-support)
- [Contribute](#contribute)
- [License](#license)

---

## What it is

Six tools, added to Claude Code via a single entry in `~/.claude/.mcp.json`:

- **`query`** — ask what Laeka Brain says about a concept or question
- **`reflect`** — share a situation; Brain holds the mirror and asks the question you haven't asked yourself
- **`consolidate`** — save a session insight to your personal mini-brain
- **`recall`** — semantic search across your personal mini-brain — find patterns and insights by natural language query
- **`list_brain_skills`** — browse the skill marketplace of an auxiliary brain (default: laeka-code)
- **`get_brain_skill`** — retrieve and apply a specific skill by name (e.g. `systematic-debugging`, `verification-before-completion`)

The four Laeka lenses — MONADE, SYMBIOTE, ARCHITECT, EMPATH — operate through all six tools. You will feel them before you name them.

---

## v0.2.2 — Honest 403 on subscription_required

v0.2.2: MCP tools now report `subscription_required` clearly on 403 instead of a generic "store unavailable" message. `list_brain_skills` and `get_brain_skill` both return `{"error": "subscription_required", "message": "...", "status": 403}` with an actionable upgrade link when the brain requires a paid addon.

## v0.2.1 — X-User-UUID header on brain skills calls

v0.2.1 passes the `X-User-UUID` header on `list_brain_skills` and `get_brain_skill` calls for tier-gated access compatibility. Users on paid tiers no longer receive 403 when accessing auxiliary brain skills.

## v0.2.0 — brain skills marketplace

v0.2.0 adds two new tools (`list_brain_skills`, `get_brain_skill`) that expose the Laeka Code skill marketplace — 28 rebranded engineering protocols available directly in Claude Code. Query, list, and apply skills from auxiliary brains like Laeka Code.

---

## How to install

**Requirements:** Python 3.12+, Claude Code.

```bash
pip install laeka-brain
```

Or without installing permanently:

```bash
uvx laeka-brain
```

---

## How to configure

Add this to `~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "laeka-brain": {
      "command": "laeka-brain",
      "env": {
        "LAEKA_BRAIN_API_URL": "https://laeka.ai"
      }
    }
  }
}
```

If you installed via `uvx`, replace `"command"` with `"uvx laeka-brain"` or use the full `uvx` path.

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `LAEKA_BRAIN_API_URL` | `https://laeka.ai` | Laeka Brain API base URL |
| `XDG_CONFIG_HOME` | `~/.config` | Override config dir location |

Your `user_uuid` is generated on first run and stored at `~/.config/laeka-brain/user_uuid`. It is the key to your personal mini-brain. Keep it — it cannot be recovered if lost.

---

## The 4 tools

### `query`

Ask what Laeka Brain says about something.

```
Use query with question="What does the ARCHITECT lens say about naming things in code?"
```

Returns the canonical Brain context framed around your question. Claude uses it as a cognitive lens — no LLM call happens inside this server.

### `reflect`

Share a situation. Brain holds the mirror.

```
Use reflect with situation="I've rewritten this module three times and I still don't like it."
```

Returns the canonical context plus a mirror directive. Claude applies the four lenses and asks the question that helps you see what you're not seeing. No advice. Just the mirror.

### `consolidate`

Persist a session insight to your mini-brain.

```
Use consolidate with text="Discovered that my naming friction is really a module boundary problem."
```

Stores the text as a `pattern_observation` in your personal memory cell. If your mini-brain doesn't exist yet, it is provisioned automatically.

### `recall`

Semantic search across your personal mini-brain.

```
Use recall with query="What did I learn about naming last week?"
```

Searches your stored patterns using vector similarity and returns the top matches ranked by relevance score. Each result shows the text snippet (up to 200 chars), sector, doc type, and creation date.

If the search endpoint is not yet available, returns your chunk count as a fallback so you always know where you stand.

---

## How to leave

If you want to remove Laeka Brain from your environment:

1. Remove the `laeka-brain` entry from `~/.claude/.mcp.json`.
2. Delete your local config: `rm -rf ~/.config/laeka-brain`
3. Optionally, destroy your mini-brain on the server:

```bash
curl -X POST https://laeka.ai/v1/brain/mini/offboard \
  -H "Content-Type: application/json" \
  -d "{\"user_uuid\": \"$(cat ~/.config/laeka-brain/user_uuid)\", \"confirm\": true}"
```

This destroys your private chunks permanently. Patterns that were anonymized and contributed to the collective remain as collective learning — they are not yours anymore, and they are not reversible.

No cron jobs. No daemons. No leftover files beyond `~/.config/laeka-brain/` (which you just deleted).

---

*Built with gratitude for Anthropic's foundational work. Laeka Brain is an extension that amplifies Claude Code — not a competitor, not a replacement.*

---

## Commercial support

The code here is free. What Laeka Lab offers commercially is **service value, not code access**:

- **Community (free)** — Self-host everything. All brains, all skills, MIT licensed. Community support via GitHub issues.
- **Individual — $15/brain or $40/bundle** — Hosted canonical sync, cross-project memory, email support. For individuals who want to support the lab while accessing hosted infrastructure.
- **Enterprise — [let's talk](mailto:contact@laeka.org)** — Custom brain construction for your domain, private deploys (on-prem/AirGap), integration consulting, SLA, priority support, compliance artifacts. Funds the lab and its open source work.

See [laeka.ai/pricing](https://laeka.ai/pricing) for details. If you want to self-host, the repo is here — fork, clone, run.

## Contribute

Skills contributions welcome. Open a PR with:
1. A skill in the appropriate brain under `brains/<brain-name>/` following the existing structure
2. A short rationale in the PR description (which lens does this skill operate through — MONADE, SYMBIOTE, ARCHITECT, EMPATH)
3. At least one concrete use case

For protocol proposals or philosophy questions, see [laeka.org/protocol](https://laeka.org/protocol) and open a Discussion first.

## License

MIT. See [LICENSE](LICENSE).

The insight itself — how cognition converges toward integrity — belongs to everyone. We don't patent cognition.
