# laeka-brain

A cognitive layer for the AI you already use.

This MCP server connects your Claude Code environment to Laeka Brain — the OmniQ protocol made available through four tools. It is a context provider. It does not call an LLM. It does not store your conversations. It returns context that Claude uses natively.

---

## What it is

Four tools, added to Claude Code via a single entry in `~/.claude/.mcp.json`:

- **`query`** — ask what Laeka Brain says about a concept or question
- **`reflect`** — share a situation; Brain holds the mirror and asks the question you haven't asked yourself
- **`consolidate`** — save a session insight to your personal mini-brain
- **`recall`** — semantic search across your personal mini-brain — find patterns and insights by natural language query

The four OmniQ lenses — MONADE, SYMBIOTE, ARCHITECT, EMPATH — operate through all four tools. You will feel them before you name them.

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
        "LAEKA_BRAIN_API_URL": "http://172.105.0.134:8822"
      }
    }
  }
}
```

If you installed via `uvx`, replace `"command"` with `"uvx laeka-brain"` or use the full `uvx` path.

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `LAEKA_BRAIN_API_URL` | `http://172.105.0.134:8822` | Seahorse API base URL |
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
curl -X POST http://172.105.0.134:8822/v1/brain/mini/offboard \
  -H "Content-Type: application/json" \
  -d "{\"user_uuid\": \"$(cat ~/.config/laeka-brain/user_uuid)\", \"confirm\": true}"
```

This destroys your private chunks permanently. Patterns that were anonymized and contributed to the collective remain as collective learning — they are not yours anymore, and they are not reversible.

No cron jobs. No daemons. No leftover files beyond `~/.config/laeka-brain/` (which you just deleted).

---

*Built with gratitude for Anthropic's foundational work. Laeka Brain is an extension that amplifies Claude Code — not a competitor, not a replacement.*
