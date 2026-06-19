# Claw 🦞

A **full** terminal coding agent — Claude Code remade, but **bring your own model**.
Single Python file, **zero dependencies**, works with any OpenAI-compatible API.

## Feature map (vs Claude Code)

| Claude Code | Claw |
|---|---|
| Agentic tool loop | ✅ up to 80 tool turns per request |
| Bash / Read / Write / Edit / Glob / Grep | ✅ `bash` (persistent `cd`), `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `ls` |
| Background tasks | ✅ `bash(run_in_background=true)` + `bash_output` + `kill_bash`, `/bashes` |
| Subagents (Task tool) | ✅ `task` tool — fresh-context subagent, returns only its report |
| Custom agents | ✅ `.md` files in `~/.claw/agents/` or `.claw/agents/` |
| Custom slash commands | ✅ `.md` files in `~/.claw/commands/` or `.claw/commands/` (`$ARGUMENTS`) |
| Todo list | ✅ `todo_write` tool, rendered checklist, `/todos` |
| Plan mode | ✅ `/plan` — read-only until you approve with `/mode default` |
| Permission modes | ✅ default / acceptEdits / plan / yolo (`/mode` cycles) |
| Permission prompts | ✅ y / n / always-per-tool |
| Hooks | ✅ PreToolUse (exit 2 blocks) / PostToolUse in config.json |
| MCP servers | ✅ stdio MCP client, `~/.claw/mcp.json` or `.claw/mcp.json`, `/mcp` |
| WebFetch / WebSearch | ✅ `web_fetch`, `web_search` (DuckDuckGo) |
| /compact + auto-compact | ✅ manual + automatic past ~100k tokens |
| Memory (CLAUDE.md, `#`) | ✅ `CLAW.md` global + project; lines starting `# ` append to it |
| `@file` mentions | ✅ attaches file content to your message |
| Sessions / --continue / /resume | ✅ auto-saved per folder, `claw -c`, `/resume` |
| /init | ✅ explores repo, writes CLAW.md |
| /cost | ✅ token usage + context size |
| Loops | ✅ `/loop 5m run the tests` |
| One-shot -p | ✅ `claw -p "..."` |
| Streaming + thinking display | ✅ reasoning models show dimmed thinking |

## Install

```sh
chmod +x claw.py
ln -sf "$PWD/claw.py" /opt/homebrew/bin/claw
```

Python 3.10+. Nothing to pip install. (Already installed on this machine.)

## Pick your API

Config at `~/.claw/config.json`. Env overrides: `CLAW_BASE_URL`, `CLAW_API_KEY`, `CLAW_MODEL`.

```jsonc
// Ollama (default) — minimax-m2.5:cloud works on the free tier.
// kimi-k2.5:cloud / glm-5:cloud need a paid Ollama subscription.
{ "base_url": "http://localhost:11434/v1", "api_key": "ollama", "model": "minimax-m2.5:cloud" }

// Moonshot direct (Kimi K2)
{ "base_url": "https://api.moonshot.ai/v1", "api_key": "sk-...", "model": "kimi-k2-turbo-preview" }

// OpenRouter
{ "base_url": "https://openrouter.ai/api/v1", "api_key": "sk-or-...", "model": "moonshotai/kimi-k2" }

// LM Studio
{ "base_url": "http://localhost:1234/v1", "api_key": "lm-studio", "model": "loaded-model" }
```

Model must support **tool calling**. Small local models (3–8B) work but make mistakes.

## Customization

### Custom subagent — `.claw/agents/reviewer.md`
```md
---
name: reviewer
description: reviews code for bugs
---
You are a strict code reviewer. Hunt for bugs, report file:line for each.
```
The main agent can then spawn it: `task(agent_type="reviewer", ...)`.

### Custom slash command — `.claw/commands/test.md`
```md
---
description: run the test suite and fix failures
---
Run the project's tests. If any fail, fix them. Focus: $ARGUMENTS
```
Use as `/test the parser`.

### Hooks — in `~/.claw/config.json`
```json
"hooks": {
  "PreToolUse": [
    { "matcher": "bash", "command": "python3 ~/guard.py" }
  ]
}
```
Hook gets `{"event","tool","args"}` on stdin. Exit code **2** blocks the call
(stderr becomes the reason shown to the model).

### MCP servers — `~/.claw/mcp.json`
```json
{ "mcpServers": { "fs": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"] } } }
```
Tools appear as `mcp__fs__read_file` etc. `/mcp` lists them.

## Daily driving

```sh
claw                  # interactive
claw -c               # continue where you left off in this folder
claw -p "explain @main.cpp"
claw --mode plan      # start in plan mode
```

In-session: `/help` shows everything. Highlights:
`# remember this` → appends to CLAW.md · `@file` attaches a file ·
`/plan` → explore + plan before touching anything · `/loop 10m check CI` ·
ctrl-c cancels, ctrl-d quits.
