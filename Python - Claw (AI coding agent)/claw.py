#!/usr/bin/env python3
"""
Claw — a full terminal coding agent. Plug in any OpenAI-compatible API.

Zero dependencies. Python 3.10+.

Works with: Ollama (local or cloud models), Moonshot (Kimi K2),
OpenRouter, Groq, LM Studio, vLLM, OpenAI — anything that speaks
the /v1/chat/completions protocol with tool calling.

Usage:
    claw                      interactive session
    claw -c                   continue last session in this folder
    claw -p "fix the bug"     one-shot, print and exit
    claw --model qwen3:8b     override model
    claw --yolo               skip permission prompts
"""

import argparse
import datetime
import difflib
import fnmatch
import glob as globmod
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    import readline  # noqa: F401  (input() history + line editing)
except ImportError:
    pass

VERSION = "0.2.0"
CONFIG_DIR = os.path.expanduser("~/.claw")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
HISTORY_PATH = os.path.join(CONFIG_DIR, "history")
SESSIONS_DIR = os.path.join(CONFIG_DIR, "sessions")

DEFAULT_CONFIG = {
    "base_url": "http://localhost:11434/v1",
    "api_key": "ollama",
    "model": "minimax-m2.5:cloud",
    "temperature": 0.6,
    "max_tokens": 8192,
    "stream": True,
    "mode": "default",            # default | acceptEdits | plan | yolo
    "max_tool_output": 30000,
    "max_turns": 80,
    "autocompact_chars": 400000,  # ~100k tokens; auto /compact past this
    "hooks": {},                  # {"PreToolUse":[{"matcher":"bash","command":"..."}], "PostToolUse":[...]}
}

MODES = ("default", "acceptEdits", "plan", "yolo")

USAGE = {"prompt": 0, "completion": 0, "requests": 0}

# ---------------------------------------------------------------- colors

def _tty() -> bool:
    return sys.stdout.isatty()

class C:
    RESET = "\033[0m" if _tty() else ""
    BOLD = "\033[1m" if _tty() else ""
    DIM = "\033[2m" if _tty() else ""
    RED = "\033[31m" if _tty() else ""
    GREEN = "\033[32m" if _tty() else ""
    YELLOW = "\033[33m" if _tty() else ""
    BLUE = "\033[34m" if _tty() else ""
    MAGENTA = "\033[35m" if _tty() else ""
    CYAN = "\033[36m" if _tty() else ""

def info(msg: str):
    print(f"{C.DIM}{msg}{C.RESET}")

def err(msg: str):
    print(f"{C.RED}{msg}{C.RESET}", file=sys.stderr)

# ---------------------------------------------------------------- config

def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                cfg.update(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            err(f"bad config at {CONFIG_PATH}: {e} — using defaults")
    for key, env in [("base_url", "CLAW_BASE_URL"), ("api_key", "CLAW_API_KEY"),
                     ("model", "CLAW_MODEL")]:
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    return cfg

def save_config(cfg: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    persisted = {k: cfg[k] for k in DEFAULT_CONFIG if k in cfg}
    with open(CONFIG_PATH, "w") as f:
        json.dump(persisted, f, indent=2)

# ---------------------------------------------------------------- frontmatter (agents / commands)

def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse a markdown file with optional '---' yaml-ish frontmatter.
    Only flat 'key: value' lines are understood. Returns (meta, body)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, text[end + 4:].lstrip("\n")

def load_md_dir(*dirs: str) -> dict[str, dict]:
    """Load name -> {meta, body, path} from .md files. Later dirs override."""
    out: dict[str, dict] = {}
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for p in sorted(globmod.glob(os.path.join(d, "*.md"))):
            try:
                with open(p, errors="replace") as f:
                    meta, body = parse_frontmatter(f.read())
            except OSError:
                continue
            name = meta.get("name") or os.path.splitext(os.path.basename(p))[0]
            out[name] = {"meta": meta, "body": body, "path": p}
    return out

def user_and_project(kind: str, cwd: str) -> tuple[str, str]:
    return (os.path.join(CONFIG_DIR, kind),
            os.path.join(cwd, ".claw", kind))

# ---------------------------------------------------------------- API client

class APIError(Exception):
    pass

def chat_request(cfg: dict, messages: list, tools: list, stream: bool):
    """POST /chat/completions. Yields ('thinking'|'text', str) and
    ('tool_calls', list) events. Final event is ('done', finish_reason)."""
    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    body = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
        "stream": stream,
    }
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:2000]
        raise APIError(f"HTTP {e.code} from {url}\n{detail}") from None
    except urllib.error.URLError as e:
        raise APIError(f"cannot reach {url}: {e.reason}") from None

    USAGE["requests"] += 1

    def note_usage(u):
        if u:
            USAGE["prompt"] += u.get("prompt_tokens", 0)
            USAGE["completion"] += u.get("completion_tokens", 0)

    if not stream:
        data = json.loads(resp.read().decode())
        note_usage(data.get("usage"))
        choice = data["choices"][0]
        msg = choice["message"]
        if msg.get("reasoning") or msg.get("reasoning_content"):
            yield ("thinking", msg.get("reasoning") or msg.get("reasoning_content"))
        if msg.get("content"):
            yield ("text", msg["content"])
        if msg.get("tool_calls"):
            yield ("tool_calls", msg["tool_calls"])
        yield ("done", choice.get("finish_reason", "stop"))
        return

    # SSE streaming: accumulate tool-call deltas by index
    pending: dict[int, dict] = {}
    finish = "stop"
    for raw in resp:
        line = raw.decode(errors="replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            chunk = json.loads(payload)
        except json.JSONDecodeError:
            continue
        note_usage(chunk.get("usage"))
        choices = chunk.get("choices") or []
        if not choices:
            continue
        choice = choices[0]
        delta = choice.get("delta") or {}
        if delta.get("reasoning") or delta.get("reasoning_content"):
            yield ("thinking", delta.get("reasoning") or delta.get("reasoning_content"))
        if delta.get("content"):
            yield ("text", delta["content"])
        for tc in delta.get("tool_calls") or []:
            i = tc.get("index", 0)
            slot = pending.setdefault(i, {
                "id": "", "type": "function",
                "function": {"name": "", "arguments": ""},
            })
            if tc.get("id"):
                slot["id"] = tc["id"]
            fn = tc.get("function") or {}
            if fn.get("name"):
                slot["function"]["name"] += fn["name"]
            if fn.get("arguments"):
                slot["function"]["arguments"] += fn["arguments"]
        if choice.get("finish_reason"):
            finish = choice["finish_reason"]
    if pending:
        calls = [pending[i] for i in sorted(pending)]
        for n, call in enumerate(calls):
            if not call["id"]:
                call["id"] = f"call_{n}"
        yield ("tool_calls", calls)
    yield ("done", finish)

# ---------------------------------------------------------------- MCP client (stdio)

class MCPServer:
    """Minimal MCP stdio client: initialize, tools/list, tools/call."""

    def __init__(self, name: str, command: str, args: list, env: dict | None = None):
        self.name = name
        self.tools: list[dict] = []
        self._id = 0
        self.proc = subprocess.Popen(
            [command] + list(args or []),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True,
            env={**os.environ, **(env or {})},
        )

    def _send(self, msg: dict):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _rpc(self, method: str, params: dict | None = None):
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"mcp server '{self.name}' closed the pipe")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                continue
            if resp.get("id") == self._id:
                if "error" in resp:
                    raise RuntimeError(resp["error"].get("message", "mcp error"))
                return resp.get("result", {})
            # else: notification or out-of-order — skip

    def start(self):
        self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "claw", "version": VERSION},
        })
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.tools = self._rpc("tools/list").get("tools", [])

    def call(self, tool: str, args: dict) -> str:
        res = self._rpc("tools/call", {"name": tool, "arguments": args})
        parts = [c.get("text", "") for c in res.get("content", [])
                 if c.get("type") == "text"]
        out = "\n".join(p for p in parts if p)
        if res.get("isError"):
            out = "error: " + (out or "tool failed")
        return out or json.dumps(res)[:2000]

    def stop(self):
        try:
            self.proc.terminate()
        except OSError:
            pass

def load_mcp_servers(cwd: str) -> dict[str, MCPServer]:
    servers: dict[str, MCPServer] = {}
    spec: dict = {}
    for path in (os.path.join(CONFIG_DIR, "mcp.json"),
                 os.path.join(cwd, ".claw", "mcp.json")):
        if os.path.exists(path):
            try:
                with open(path) as f:
                    spec.update(json.load(f).get("mcpServers", {}))
            except (json.JSONDecodeError, OSError) as e:
                err(f"bad mcp config {path}: {e}")
    for name, conf in spec.items():
        try:
            srv = MCPServer(name, conf["command"], conf.get("args", []),
                            conf.get("env"))
            srv.start()
            servers[name] = srv
            info(f"mcp: {name} connected ({len(srv.tools)} tools)")
        except Exception as e:
            err(f"mcp: {name} failed: {e}")
    return servers

def mcp_tool_defs(servers: dict[str, MCPServer]) -> list[dict]:
    defs = []
    for sname, srv in servers.items():
        for t in srv.tools:
            defs.append({
                "type": "function",
                "function": {
                    "name": f"mcp__{sname}__{t['name']}",
                    "description": (t.get("description") or "")[:1000],
                    "parameters": t.get("inputSchema") or {"type": "object", "properties": {}},
                },
            })
    return defs

# ---------------------------------------------------------------- background processes

class BackgroundShell:
    _next_id = 1

    def __init__(self):
        self.jobs: dict[str, dict] = {}

    def launch(self, command: str, cwd: str) -> str:
        jid = f"bg{BackgroundShell._next_id}"
        BackgroundShell._next_id += 1
        out = tempfile.NamedTemporaryFile(prefix=f"claw_{jid}_", suffix=".log",
                                          delete=False, mode="w")
        proc = subprocess.Popen(
            command, shell=True, cwd=cwd, stdout=out, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
            executable="/bin/zsh" if os.path.exists("/bin/zsh") else None,
        )
        self.jobs[jid] = {"proc": proc, "log": out.name, "cmd": command,
                          "read_pos": 0, "started": time.time()}
        return jid

    def output(self, jid: str) -> str:
        job = self.jobs.get(jid)
        if not job:
            return f"error: no background job {jid}"
        try:
            with open(job["log"], errors="replace") as f:
                f.seek(job["read_pos"])
                new = f.read()
                job["read_pos"] = f.tell()
        except OSError as e:
            return f"error: {e}"
        rc = job["proc"].poll()
        status = "still running" if rc is None else f"exited with code {rc}"
        return (new or "(no new output)") + f"\n[{jid}: {status}]"

    def kill(self, jid: str) -> str:
        job = self.jobs.get(jid)
        if not job:
            return f"error: no background job {jid}"
        if job["proc"].poll() is None:
            try:
                os.killpg(os.getpgid(job["proc"].pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                job["proc"].terminate()
            return f"{jid} terminated"
        return f"{jid} already exited"

    def list(self) -> str:
        if not self.jobs:
            return "(no background jobs)"
        lines = []
        for jid, job in self.jobs.items():
            rc = job["proc"].poll()
            status = "running" if rc is None else f"exit {rc}"
            lines.append(f"{jid}  [{status}]  {job['cmd'][:80]}")
        return "\n".join(lines)

BG = BackgroundShell()

# ---------------------------------------------------------------- tools

BASE_TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run a shell command and return stdout+stderr. Working "
                "directory persists across calls (cd works). Set "
                "run_in_background=true for servers/long builds, then poll "
                "with bash_output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "shell command to run"},
                    "timeout": {"type": "integer", "description": "seconds, default 120, max 600"},
                    "run_in_background": {"type": "boolean", "description": "default false"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash_output",
            "description": "Get new output from a background job started by bash(run_in_background=true).",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kill_bash",
            "description": "Terminate a background job.",
            "parameters": {
                "type": "object",
                "properties": {"job_id": {"type": "string"}},
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file. Returns numbered lines. Use offset/limit for big files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "file path (absolute or relative)"},
                    "offset": {"type": "integer", "description": "1-based start line"},
                    "limit": {"type": "integer", "description": "max lines, default 2000"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in a file. old_string must match "
                "exactly (whitespace included) and be unique unless "
                "replace_all is true."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean", "description": "default false"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Find files by name pattern, e.g. '**/*.py'. Sorted by modification time, newest first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "glob pattern like 'src/**/*.cpp'"},
                    "path": {"type": "string", "description": "directory to search, default cwd"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": (
                "Search file contents with a regex. Returns matching lines "
                "as path:line:text. Skips .git, binaries, hidden dirs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "python regex"},
                    "path": {"type": "string", "description": "directory or file, default cwd"},
                    "glob": {"type": "string", "description": "filter filenames, e.g. '*.py'"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ls",
            "description": "List a directory: names, sizes, dirs marked with /.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "default cwd"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_write",
            "description": (
                "Replace the task list shown to the user. Use for multi-step "
                "work: plan steps up front, mark exactly one in_progress, "
                "mark completed immediately when done."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {"type": "string",
                                           "enum": ["pending", "in_progress", "completed"]},
                            },
                            "required": ["content", "status"],
                        },
                    },
                },
                "required": ["todos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch a URL and return its text content (HTML tags stripped).",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web (DuckDuckGo). Returns titles, urls, snippets.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]

# tools that never modify anything — auto-approved
SAFE_TOOLS = {"read_file", "glob", "grep", "ls", "web_fetch", "web_search",
              "todo_write", "bash_output", "task"}
PLAN_TOOLS = SAFE_TOOLS  # what plan mode may run

IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv",
                "dist", "build", ".cache"}

class Tools:
    def __init__(self, cfg: dict, cwd: str | None = None):
        self.cfg = cfg
        self.cwd = cwd or os.getcwd()
        self.todos: list[dict] = []

    def _resolve(self, path: str) -> str:
        return os.path.normpath(os.path.join(self.cwd, os.path.expanduser(path)))

    # -- execution --------------------------------------------------

    def bash(self, command: str, timeout: int = 120,
             run_in_background: bool = False) -> str:
        if run_in_background:
            jid = BG.launch(command, self.cwd)
            return f"started background job {jid} — poll with bash_output"
        timeout = min(max(int(timeout or 120), 1), 600)
        # marker trick keeps `cd` persistent across calls
        marker = "__CLAW_PWD__"
        wrapped = f"{command}\nprintf '\\n{marker}%s' \"$PWD\""
        try:
            proc = subprocess.run(
                wrapped, shell=True, cwd=self.cwd, timeout=timeout,
                capture_output=True, text=True, errors="replace",
                executable="/bin/zsh" if os.path.exists("/bin/zsh") else None,
            )
        except subprocess.TimeoutExpired:
            return f"(timed out after {timeout}s — use run_in_background for long jobs)"
        out = proc.stdout
        if marker in out:
            out, _, newpwd = out.rpartition("\n" + marker)
            newpwd = newpwd.strip()
            if newpwd and os.path.isdir(newpwd):
                self.cwd = newpwd
        result = out
        if proc.stderr:
            result += ("\n" if result else "") + proc.stderr
        if proc.returncode != 0:
            result += f"\n(exit code {proc.returncode})"
        return result.strip() or "(no output)"

    def bash_output(self, job_id: str) -> str:
        return BG.output(job_id)

    def kill_bash(self, job_id: str) -> str:
        return BG.kill(job_id)

    def read_file(self, path: str, offset: int = 1, limit: int = 2000) -> str:
        p = self._resolve(path)
        if not os.path.exists(p):
            return f"error: no such file: {p}"
        if os.path.isdir(p):
            return f"error: {p} is a directory, use ls"
        try:
            with open(p, errors="replace") as f:
                lines = f.readlines()
        except OSError as e:
            return f"error: {e}"
        offset = max(int(offset or 1), 1)
        limit = int(limit or 2000)
        chunk = lines[offset - 1: offset - 1 + limit]
        if not chunk:
            return f"(file has {len(lines)} lines, offset {offset} past end)"
        numbered = "".join(f"{i:6d}\t{line}" for i, line in
                           enumerate(chunk, start=offset))
        if offset - 1 + limit < len(lines):
            numbered += f"\n... ({len(lines)} lines total, showing {offset}-{offset + len(chunk) - 1})"
        return numbered

    def write_file(self, path: str, content: str) -> str:
        p = self._resolve(path)
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        existed = os.path.exists(p)
        try:
            with open(p, "w") as f:
                f.write(content)
        except OSError as e:
            return f"error: {e}"
        verb = "overwrote" if existed else "created"
        return f"{verb} {p} ({len(content.splitlines())} lines)"

    def edit_file(self, path: str, old_string: str, new_string: str,
                  replace_all: bool = False) -> str:
        p = self._resolve(path)
        if not os.path.exists(p):
            return f"error: no such file: {p}"
        try:
            with open(p, errors="replace") as f:
                text = f.read()
        except OSError as e:
            return f"error: {e}"
        count = text.count(old_string)
        if count == 0:
            return "error: old_string not found in file (must match exactly, whitespace included)"
        if count > 1 and not replace_all:
            return f"error: old_string appears {count} times — make it unique or set replace_all"
        new_text = (text.replace(old_string, new_string) if replace_all
                    else text.replace(old_string, new_string, 1))
        with open(p, "w") as f:
            f.write(new_text)
        n = count if replace_all else 1
        return f"replaced {n} occurrence(s) in {p}"

    def glob(self, pattern: str, path: str = ".") -> str:
        root = self._resolve(path or ".")
        matches = []
        recursive = "**" in pattern
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in IGNORED_DIRS and not d.startswith(".")]
            for name in filenames:
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root)
                target = rel if recursive or os.sep in pattern else name
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(target, pattern):
                    matches.append(full)
        matches.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        if not matches:
            return "(no matches)"
        return "\n".join(matches[:200]) + ("" if len(matches) <= 200 else
                                           f"\n... ({len(matches)} total)")

    def grep(self, pattern: str, path: str = ".", glob: str = "") -> str:
        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"error: bad regex: {e}"
        root = self._resolve(path or ".")
        if os.path.isfile(root):
            files = [root]
        else:
            files = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames
                               if d not in IGNORED_DIRS and not d.startswith(".")]
                for name in filenames:
                    if glob and not fnmatch.fnmatch(name, glob):
                        continue
                    files.append(os.path.join(dirpath, name))
        hits = []
        for fp in files:
            try:
                with open(fp, errors="strict") as f:
                    for n, line in enumerate(f, 1):
                        if rx.search(line):
                            hits.append(f"{fp}:{n}:{line.rstrip()[:300]}")
                            if len(hits) >= 300:
                                break
            except (OSError, UnicodeDecodeError):
                continue  # binary or unreadable
            if len(hits) >= 300:
                hits.append("... (capped at 300 matches)")
                break
        return "\n".join(hits) if hits else "(no matches)"

    def ls(self, path: str = ".") -> str:
        p = self._resolve(path or ".")
        if not os.path.isdir(p):
            return f"error: not a directory: {p}"
        entries = []
        try:
            for name in sorted(os.listdir(p)):
                full = os.path.join(p, name)
                if os.path.isdir(full):
                    entries.append(name + "/")
                else:
                    try:
                        size = os.path.getsize(full)
                    except OSError:
                        size = 0
                    entries.append(f"{name}  ({size:,} B)")
        except OSError as e:
            return f"error: {e}"
        return "\n".join(entries) or "(empty)"

    def todo_write(self, todos: list) -> str:
        self.todos = todos
        marks = {"pending": "☐", "in_progress": "▶", "completed": "✔"}
        lines = [f"  {marks.get(t.get('status'), '?')} {t.get('content', '')}"
                 for t in todos]
        print(f"{C.MAGENTA}── todos ──{C.RESET}\n" + "\n".join(lines))
        return f"todo list updated ({len(todos)} items)"

    def web_fetch(self, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            return "error: url must start with http:// or https://"
        req = urllib.request.Request(url, headers={"User-Agent": "claw/" + VERSION})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read(2_000_000).decode(errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return f"error: {e}"
        # crude html -> text
        text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()[:50000]

    def web_search(self, query: str) -> str:
        url = ("https://html.duckduckgo.com/html/?q="
               + urllib.parse.quote_plus(query))
        req = urllib.request.Request(url, headers={
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/124.0 Safari/537.36")})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read(1_000_000).decode(errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return f"error: {e}"
        def clean(s):
            return re.sub(r"<[^>]+>", "", s or "").strip()
        links = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            html, re.S)
        snippets = re.findall(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
        results = []
        for i, (href, title) in enumerate(links[:8]):
            # ddg wraps urls in a redirect
            qs = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            real = qs.get("uddg", [href])[0]
            snippet = clean(snippets[i]) if i < len(snippets) else ""
            results.append(f"{clean(title)}\n{real}\n{snippet}")
        return "\n\n".join(results) if results else "(no results)"

    def dispatch(self, name: str, args: dict) -> str:
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_") or name == "dispatch":
            return f"error: unknown tool {name}"
        try:
            return str(fn(**args))
        except TypeError as e:
            return f"error: bad arguments for {name}: {e}"
        except Exception as e:  # tool crash must not kill the session
            return f"error: {type(e).__name__}: {e}"

# ---------------------------------------------------------------- hooks

def run_hooks(cfg: dict, event: str, tool_name: str, payload: dict,
              cwd: str) -> tuple[bool, str]:
    """Run configured hooks. Returns (allowed, message). A PreToolUse hook
    exiting with code 2 blocks the tool call; its stderr explains why."""
    for hook in cfg.get("hooks", {}).get(event, []):
        matcher = hook.get("matcher", "")
        if matcher and not re.fullmatch(matcher, tool_name):
            continue
        try:
            proc = subprocess.run(
                hook["command"], shell=True, cwd=cwd, timeout=60,
                input=json.dumps({"event": event, "tool": tool_name,
                                  "args": payload}),
                capture_output=True, text=True,
            )
        except (subprocess.TimeoutExpired, KeyError, OSError) as e:
            err(f"hook error ({event}): {e}")
            continue
        if proc.stdout.strip():
            info(f"hook: {proc.stdout.strip()[:300]}")
        if event == "PreToolUse" and proc.returncode == 2:
            return False, proc.stderr.strip()[:500] or "blocked by hook"
    return True, ""

# ---------------------------------------------------------------- permissions

class Permissions:
    def __init__(self, mode: str):
        self.mode = mode if mode in MODES else "default"
        self.always: set[str] = set()

    def preview(self, name: str, args: dict) -> str:
        if name == "bash":
            return args.get("command", "")
        if name == "write_file":
            content = args.get("content", "")
            head = "\n".join(content.splitlines()[:8])
            more = "" if len(content.splitlines()) <= 8 else "\n..."
            return f"{args.get('path')}\n{C.DIM}{head}{more}{C.RESET}"
        if name == "edit_file":
            old = args.get("old_string", "")
            new = args.get("new_string", "")
            diff = "\n".join(difflib.unified_diff(
                old.splitlines(), new.splitlines(),
                lineterm="", n=1))[:1200]
            return f"{args.get('path')}\n{C.DIM}{diff}{C.RESET}"
        if name == "task":
            return f"{args.get('agent_type', 'general')}: {args.get('description', '')}"
        return json.dumps(args)[:300]

    def check(self, name: str, args: dict) -> tuple[bool, str]:
        if self.mode == "plan" and name not in PLAN_TOOLS:
            return False, ("plan mode: read-only. Present your plan; the user "
                           "approves with /mode default (or acceptEdits/yolo).")
        if self.mode == "yolo" or name in SAFE_TOOLS or name in self.always:
            return True, ""
        if self.mode == "acceptEdits" and name in ("write_file", "edit_file"):
            return True, ""
        print(f"\n{C.YELLOW}{C.BOLD}● {name}{C.RESET} wants to run:")
        print("  " + self.preview(name, args).replace("\n", "\n  "))
        while True:
            try:
                ans = input(f"{C.YELLOW}allow? [y]es / [n]o / [a]lways ({name}) {C.RESET}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return False, "user denied this tool call"
            if ans in ("y", "yes", ""):
                return True, ""
            if ans in ("n", "no"):
                return False, "user denied this tool call"
            if ans in ("a", "always"):
                self.always.add(name)
                return True, ""

# ---------------------------------------------------------------- system prompt

PROJECT_MEMORY_FILES = ("CLAW.md", "AGENTS.md", "CLAUDE.md")

def build_system_prompt(tools: Tools, cfg: dict, agent_role: str = "") -> str:
    env_lines = [
        f"cwd: {tools.cwd}",
        f"os: {platform.system()} {platform.release()} ({platform.machine()})",
        f"date: {datetime.date.today().isoformat()}",
    ]
    if shutil.which("git"):
        branch = subprocess.run(
            ["git", "-C", tools.cwd, "branch", "--show-current"],
            capture_output=True, text=True).stdout.strip()
        if branch:
            env_lines.append(f"git branch: {branch}")
    memory = ""
    user_mem = os.path.join(CONFIG_DIR, "CLAW.md")
    if os.path.exists(user_mem):
        try:
            with open(user_mem, errors="replace") as f:
                memory += "\n\n# User notes (~/.claw/CLAW.md)\n" + f.read()[:10000]
        except OSError:
            pass
    for name in PROJECT_MEMORY_FILES:
        p = os.path.join(tools.cwd, name)
        if os.path.exists(p):
            try:
                with open(p, errors="replace") as f:
                    memory += f"\n\n# Project notes ({name})\n" + f.read()[:20000]
            except OSError:
                pass
            break
    role = agent_role or (
        "You are Claw, a terminal coding agent. You help with software "
        "engineering: writing code, fixing bugs, running commands, explaining "
        "codebases.")
    return f"""{role}

Rules:
- Be concise. Short answers for short questions. No filler.
- Use tools to act; do not just describe what could be done.
- Activate tools first, execute, then talk.
- For multi-step tasks, use todo_write to plan and track steps.
- For broad searches or independent subtasks, use the task tool to spawn a subagent and keep your own context clean.
- Read files before editing them. Verify changes by running code/tests when possible.
- For edit_file, old_string must match the file exactly — copy it from read_file output (without the line-number prefix).
- Prefer edit_file for small changes, write_file only for new files or full rewrites.
- Long-running commands (servers, watch modes): bash with run_in_background=true, then bash_output.
- Never invent file contents or command output. If a tool fails, say so and adapt.
- When the task is done, summarize briefly what changed.

Environment:
{chr(10).join(env_lines)}{memory}"""

PLAN_NOTE = ("\n\n# PLAN MODE — ACTIVE\nYou are in plan mode: read-only tools "
             "only (read/glob/grep/ls/web). Explore, then present a concrete "
             "step-by-step plan and stop. Do NOT attempt writes or commands; "
             "they will be rejected. The user switches modes to approve.")

# ---------------------------------------------------------------- agent loop

class Agent:
    def __init__(self, cfg: dict, cwd: str | None = None,
                 perms: Permissions | None = None, depth: int = 0,
                 agent_role: str = "", mcp: dict | None = None,
                 subagent_defs: dict | None = None):
        self.cfg = cfg
        self.depth = depth
        self.tools = Tools(cfg, cwd)
        self.perms = perms or Permissions(cfg.get("mode", "default"))
        self.mcp = mcp or {}
        self.subagent_defs = subagent_defs or {}
        self.session_path: str | None = None
        self.messages: list[dict] = [
            {"role": "system",
             "content": build_system_prompt(self.tools, cfg, agent_role)}
        ]

    # -- tool defs (depth-aware: subagents can't spawn subagents) ----

    def tool_defs(self) -> list[dict]:
        defs = list(BASE_TOOL_DEFS) + mcp_tool_defs(self.mcp)
        if self.depth == 0:
            agents_desc = "\n".join(
                f"- {name}: {d['meta'].get('description', '(no description)')}"
                for name, d in self.subagent_defs.items()) or "(none defined)"
            defs.append({
                "type": "function",
                "function": {
                    "name": "task",
                    "description": (
                        "Spawn a subagent with a fresh context to handle a "
                        "self-contained task (broad search, research, an "
                        "independent subtask). It returns only its final "
                        "report. Custom agent_types available:\n" + agents_desc),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string", "description": "3-6 word task label"},
                            "prompt": {"type": "string", "description": "full standalone instructions — the subagent sees nothing else"},
                            "agent_type": {"type": "string", "description": "optional custom agent name, default general"},
                        },
                        "required": ["description", "prompt"],
                    },
                },
            })
        return defs

    # -- context hygiene ---------------------------------------------

    def _context_chars(self) -> int:
        return sum(len(json.dumps(m)) for m in self.messages)

    def _truncate(self, text: str) -> str:
        cap = self.cfg["max_tool_output"]
        if len(text) <= cap:
            return text
        return text[:cap] + f"\n... (truncated, {len(text)} chars total)"

    def _request_messages(self) -> list[dict]:
        msgs = [dict(m) for m in self.messages]
        if self.perms.mode == "plan":
            msgs[0]["content"] += PLAN_NOTE
        return msgs

    # -- main loop -----------------------------------------------------

    def run_turn(self, user_input: str) -> str:
        if self._context_chars() > self.cfg["autocompact_chars"]:
            info("context large — auto-compacting...")
            self.compact()
        self.messages.append({"role": "user", "content": user_input})
        quiet = self.depth > 0
        last_text = ""
        for _ in range(self.cfg["max_turns"]):
            text_parts: list[str] = []
            tool_calls: list[dict] = []
            try:
                printed_any = False
                thinking_open = False
                for kind, data in chat_request(self.cfg, self._request_messages(),
                                               self.tool_defs(), self.cfg["stream"]):
                    if kind == "thinking" and not quiet:
                        if not thinking_open:
                            print(f"{C.DIM}✱ thinking… ", end="", flush=True)
                            thinking_open = True
                        print(f"{C.DIM}{data}{C.RESET}", end="", flush=True)
                    elif kind == "text":
                        text_parts.append(data)
                        if quiet:
                            continue
                        if thinking_open:
                            print(C.RESET)
                            thinking_open = False
                        if not printed_any:
                            print(f"{C.CYAN}{C.BOLD}claw{C.RESET} ", end="")
                            printed_any = True
                        print(data, end="", flush=True)
                    elif kind == "tool_calls":
                        tool_calls = data
                if thinking_open:
                    print(C.RESET)
                if printed_any:
                    print()
            except APIError as e:
                err(f"\nAPI error: {e}")
                self.messages.pop()  # drop the user msg so retry is clean
                return ""
            except KeyboardInterrupt:
                print(f"\n{C.YELLOW}(interrupted){C.RESET}")
                self.messages.append({"role": "assistant",
                                      "content": "".join(text_parts) or "(interrupted)"})
                self.save_session()
                return ""

            last_text = "".join(text_parts) or last_text
            assistant_msg: dict = {"role": "assistant",
                                   "content": "".join(text_parts) or None}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            self.messages.append(assistant_msg)

            if not tool_calls:
                self.save_session()
                return last_text

            for call in tool_calls:
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                    if not isinstance(args, dict):
                        raise ValueError("arguments not an object")
                except (json.JSONDecodeError, ValueError) as e:
                    self._append_tool_result(call, f"error: could not parse arguments: {e}")
                    continue
                indent = "  " * self.depth
                summary = self.perms.preview(name, args).split("\n")[0][:120]
                print(f"{indent}{C.GREEN}⏺ {name}{C.RESET}{C.DIM}({summary}){C.RESET}")

                allowed, msg = run_hooks(self.cfg, "PreToolUse", name, args,
                                         self.tools.cwd)
                if allowed:
                    allowed, msg = self.perms.check(name, args)
                if not allowed:
                    self._append_tool_result(call, msg or "denied")
                    info(f"{indent}  denied")
                    continue
                try:
                    result = self.execute(name, args)
                except KeyboardInterrupt:
                    result = "(interrupted by user)"
                run_hooks(self.cfg, "PostToolUse", name,
                          {"args": args, "result": result[:2000]}, self.tools.cwd)
                self._append_tool_result(call, self._truncate(result))
                first = result.split("\n")[0][:160]
                info(f"{indent}  ⎿ {first}" + (" ..." if "\n" in result else ""))
        err("hit max_turns limit — stopping. Say 'continue' to keep going.")
        self.save_session()
        return last_text

    def execute(self, name: str, args: dict) -> str:
        if name == "task":
            return self.run_subagent(args)
        if name.startswith("mcp__"):
            _, sname, tname = name.split("__", 2)
            srv = self.mcp.get(sname)
            if not srv:
                return f"error: mcp server {sname} not connected"
            try:
                return srv.call(tname, args)
            except Exception as e:
                return f"error: mcp call failed: {e}"
        return self.tools.dispatch(name, args)

    def run_subagent(self, args: dict) -> str:
        agent_type = args.get("agent_type", "")
        role = ""
        if agent_type and agent_type in self.subagent_defs:
            role = self.subagent_defs[agent_type]["body"]
        sub = Agent(self.cfg, cwd=self.tools.cwd, perms=self.perms,
                    depth=self.depth + 1, agent_role=role, mcp=self.mcp)
        info(f"  ↳ subagent [{agent_type or 'general'}]: {args.get('description', '')}")
        result = sub.run_turn(args.get("prompt", ""))
        info(f"  ↳ subagent done ({len(sub.messages)} messages)")
        return result or "(subagent produced no final answer)"

    def _append_tool_result(self, call: dict, result: str):
        self.messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": result,
        })

    # -- compaction ----------------------------------------------------

    def compact(self):
        info("compacting conversation...")
        transcript = []
        for m in self.messages[1:]:
            role = m["role"]
            content = m.get("content") or ""
            if m.get("tool_calls"):
                content += " " + ", ".join(
                    tc["function"]["name"] for tc in m["tool_calls"])
            transcript.append(f"{role}: {content[:2000]}")
        prompt = ("Summarize this coding session so work can continue: key "
                  "facts, files touched, decisions, current state, next steps. "
                  "Be dense.\n\n" + "\n".join(transcript)[-60000:])
        try:
            parts = []
            for kind, data in chat_request(
                    self.cfg, [{"role": "user", "content": prompt}], [], False):
                if kind == "text":
                    parts.append(data)
            summary = "".join(parts)
        except APIError as e:
            err(f"compact failed: {e}")
            return
        self.messages = [
            self.messages[0],
            {"role": "user", "content": "Session summary so far:\n" + summary},
            {"role": "assistant", "content": "Understood, continuing from that state."},
        ]
        info("compacted.")

    # -- session persistence --------------------------------------------

    def save_session(self):
        if self.depth > 0:
            return
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        if not self.session_path:
            stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.session_path = os.path.join(SESSIONS_DIR, f"{stamp}.json")
        try:
            with open(self.session_path, "w") as f:
                json.dump({"cwd": self.tools.cwd,
                           "saved": time.time(),
                           "messages": self.messages}, f)
        except OSError as e:
            err(f"could not save session: {e}")

    def load_session(self, path: str) -> bool:
        try:
            with open(path) as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            err(f"could not load session: {e}")
            return False
        self.messages = data["messages"]
        self.session_path = path
        n_user = sum(1 for m in self.messages if m["role"] == "user")
        info(f"resumed session {os.path.basename(path)} ({n_user} user messages)")
        return True

def list_sessions(cwd: str) -> list[str]:
    if not os.path.isdir(SESSIONS_DIR):
        return []
    paths = sorted(globmod.glob(os.path.join(SESSIONS_DIR, "*.json")),
                   reverse=True)
    matching = []
    for p in paths:
        try:
            with open(p) as f:
                if json.load(f).get("cwd") == cwd:
                    matching.append(p)
        except (OSError, json.JSONDecodeError):
            continue
    return matching

# ---------------------------------------------------------------- REPL

HELP = f"""{C.BOLD}slash commands{C.RESET}
  /help                this help
  /clear               wipe conversation, start fresh session
  /compact             summarize history to free context
  /mode [name]         default | acceptEdits | plan | yolo  (no arg = cycle)
  /plan                shortcut for /mode plan
  /model [name]        show or switch model (saved to config)
  /config              show current config ({CONFIG_PATH})
  /cost                token usage + context size
  /resume [n]          list / load previous sessions in this folder
  /todos               show current todo list
  /bashes              list background jobs
  /agents              list custom subagents
  /commands            list custom slash commands
  /mcp                 list connected MCP servers + tools
  /init                explore this repo and write a CLAW.md
  /loop <every> <p>    repeat prompt, e.g. /loop 5m check tests   (ctrl-c stops)
  /cwd [path]          show or change agent working directory
  /exit                quit (also: ctrl-d)

{C.BOLD}input tricks{C.RESET}
  # remember this        lines starting with '# ' append to CLAW.md (memory)
  @path/to/file          attach a file's content to your message
  trailing \\             continue on next line
  ctrl-c                 cancel current response

{C.BOLD}customization{C.RESET} (user-level in ~/.claw/, project-level in .claw/)
  agents/*.md            custom subagents  (frontmatter: name, description; body = system prompt)
  commands/*.md          custom slash commands ($ARGUMENTS placeholder)
  mcp.json               MCP servers: {{"mcpServers": {{"name": {{"command": "...", "args": []}}}}}}
  CLAW.md                memory: ~/.claw/CLAW.md (global) + ./CLAW.md (project)
  config.json hooks      PreToolUse / PostToolUse shell hooks (exit 2 blocks)"""

INIT_PROMPT = """Explore this repository (ls, key files, build system, tests) \
and write a concise CLAW.md in the project root: what the project is, how to \
build/run/test it, code layout, and any conventions you can infer. Keep it \
under 60 lines."""

def parse_interval(s: str) -> int | None:
    m = re.fullmatch(r"(\d+)(s|m|h)?", s)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2) or "s"
    return n * {"s": 1, "m": 60, "h": 3600}[unit]

def expand_mentions(text: str, tools: Tools) -> str:
    """Expand @path mentions into attached file content."""
    attachments = []
    for m in re.finditer(r"@([\w~/][\w./~-]*)", text):
        p = tools._resolve(m.group(1).rstrip(".,"))
        if os.path.isfile(p):
            try:
                with open(p, errors="replace") as f:
                    content = f.read()[:30000]
                attachments.append(f"\n\n[attached file {m.group(1)}]\n```\n{content}\n```")
            except OSError:
                pass
    return text + "".join(attachments)

def read_user_input(agent: Agent) -> str:
    lines = []
    mode = agent.perms.mode
    tag = "" if mode == "default" else f"{C.MAGENTA}[{mode}]{C.RESET} "
    prompt = f"{tag}{C.BLUE}{C.BOLD}> {C.RESET}"
    while True:
        line = input(prompt)
        if line.endswith("\\"):
            lines.append(line[:-1])
            prompt = f"{C.BLUE}… {C.RESET}"
            continue
        lines.append(line)
        return "\n".join(lines).strip()

def remember(text: str, cwd: str):
    path = os.path.join(cwd, "CLAW.md")
    is_new = not os.path.exists(path)
    with open(path, "a") as f:
        if is_new:
            f.write("# Project notes\n")
        f.write(f"- {text}\n")
    info(f"noted in {path}")

def handle_slash(cmd: str, agent: Agent, cfg: dict,
                 commands: dict) -> bool:
    """Returns True if handled. Raises EOFError to quit."""
    parts = cmd.split(maxsplit=1)
    name, arg = parts[0].lower(), (parts[1] if len(parts) > 1 else "")
    if name in ("/exit", "/quit", "/q"):
        raise EOFError
    if name == "/help":
        print(HELP)
    elif name == "/clear":
        agent.messages = agent.messages[:1]
        agent.session_path = None
        agent.tools.todos = []
        info("conversation cleared — new session")
    elif name == "/compact":
        agent.compact()
    elif name in ("/mode", "/plan"):
        if name == "/plan":
            arg = "plan"
        if arg:
            if arg not in MODES:
                err(f"modes: {', '.join(MODES)}")
                return True
            agent.perms.mode = arg
        else:
            i = MODES.index(agent.perms.mode)
            agent.perms.mode = MODES[(i + 1) % len(MODES)]
        cfg["mode"] = agent.perms.mode
        labels = {"default": "ask before writes/commands",
                  "acceptEdits": "file edits auto-approved",
                  "plan": "read-only, plan first",
                  "yolo": "NO permission prompts"}
        info(f"mode: {agent.perms.mode} — {labels[agent.perms.mode]}")
    elif name == "/yolo":
        agent.perms.mode = "yolo" if agent.perms.mode != "yolo" else "default"
        info(f"mode: {agent.perms.mode}")
    elif name == "/model":
        if arg:
            cfg["model"] = arg
            save_config(cfg)
            info(f"model set to {arg} (saved)")
        else:
            info(f"model: {cfg['model']}")
    elif name == "/config":
        shown = dict(cfg)
        if shown.get("api_key") and shown["api_key"] not in ("ollama", ""):
            shown["api_key"] = shown["api_key"][:6] + "..."
        print(json.dumps(shown, indent=2))
        info(f"file: {CONFIG_PATH}")
    elif name == "/cost":
        ctx = agent._context_chars()
        print(f"requests: {USAGE['requests']}   "
              f"tokens in: {USAGE['prompt']:,}   out: {USAGE['completion']:,}\n"
              f"context: ~{ctx // 4:,} tokens ({ctx:,} chars), "
              f"auto-compact at ~{cfg['autocompact_chars'] // 4:,}")
    elif name == "/resume":
        sessions = list_sessions(agent.tools.cwd)
        if not sessions:
            info("no saved sessions for this folder")
        elif arg.isdigit() and int(arg) <= len(sessions):
            agent.load_session(sessions[int(arg) - 1])
        else:
            for i, p in enumerate(sessions[:10], 1):
                print(f"  {i}. {os.path.basename(p)}")
            info("load with /resume <number>")
    elif name == "/todos":
        if agent.tools.todos:
            agent.tools.todo_write(agent.tools.todos)
        else:
            info("(no todos)")
    elif name == "/bashes":
        print(BG.list())
    elif name == "/agents":
        if agent.subagent_defs:
            for aname, d in agent.subagent_defs.items():
                print(f"  {aname} — {d['meta'].get('description', '')}  "
                      f"{C.DIM}({d['path']}){C.RESET}")
        else:
            info("no custom agents — add .md files to ~/.claw/agents/ or .claw/agents/")
    elif name == "/commands":
        if commands:
            for cname, d in commands.items():
                print(f"  /{cname} — {d['meta'].get('description', '')}  "
                      f"{C.DIM}({d['path']}){C.RESET}")
        else:
            info("no custom commands — add .md files to ~/.claw/commands/ or .claw/commands/")
    elif name == "/mcp":
        if agent.mcp:
            for sname, srv in agent.mcp.items():
                tools = ", ".join(t["name"] for t in srv.tools)[:200]
                print(f"  {sname}: {tools}")
        else:
            info("no MCP servers — configure ~/.claw/mcp.json")
    elif name == "/init":
        agent.run_turn(INIT_PROMPT)
    elif name == "/loop":
        sub = arg.split(maxsplit=1)
        secs = parse_interval(sub[0]) if sub else None
        if not secs or len(sub) < 2:
            err("usage: /loop <interval> <prompt>   e.g. /loop 5m run the tests")
            return True
        info(f"looping every {sub[0]} — ctrl-c to stop")
        try:
            n = 0
            while True:
                n += 1
                info(f"— loop iteration {n} —")
                agent.run_turn(sub[1])
                time.sleep(secs)
        except KeyboardInterrupt:
            print()
            info(f"loop stopped after {n} iteration(s)")
    elif name == "/cwd":
        if arg:
            p = os.path.expanduser(arg)
            if os.path.isdir(p):
                agent.tools.cwd = os.path.abspath(p)
                info(f"cwd: {agent.tools.cwd}")
            else:
                err(f"not a directory: {p}")
        else:
            info(f"cwd: {agent.tools.cwd}")
    else:
        # custom command from commands/*.md
        cname = name[1:]
        if cname in commands:
            body = commands[cname]["body"].replace("$ARGUMENTS", arg)
            agent.run_turn(body)
            return True
        return False
    return True

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="claw", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-p", "--print", dest="oneshot", metavar="PROMPT",
                    help="run one prompt non-interactively and exit")
    ap.add_argument("-c", "--continue", dest="cont", action="store_true",
                    help="continue the most recent session in this folder")
    ap.add_argument("--model", help="model name override")
    ap.add_argument("--base-url", help="API base url override")
    ap.add_argument("--api-key", help="API key override")
    ap.add_argument("--yolo", action="store_true", help="skip permission prompts")
    ap.add_argument("--mode", choices=MODES, help="permission mode")
    ap.add_argument("--no-stream", action="store_true", help="disable streaming")
    ap.add_argument("--no-mcp", action="store_true", help="don't start MCP servers")
    ap.add_argument("--version", action="version", version="claw " + VERSION)
    args = ap.parse_args()

    cfg = load_config()
    if not os.path.exists(CONFIG_PATH):
        save_config(cfg)  # first run: write defaults so user can edit
    if args.model:
        cfg["model"] = args.model
    if args.base_url:
        cfg["base_url"] = args.base_url
    if args.api_key:
        cfg["api_key"] = args.api_key
    if args.mode:
        cfg["mode"] = args.mode
    if args.yolo:
        cfg["mode"] = "yolo"
    if args.no_stream:
        cfg["stream"] = False

    cwd = os.getcwd()
    mcp = {} if (args.no_mcp or args.oneshot) else load_mcp_servers(cwd)
    subagents = load_md_dir(*user_and_project("agents", cwd))
    commands = load_md_dir(*user_and_project("commands", cwd))

    if "readline" in sys.modules:
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if os.path.exists(HISTORY_PATH):
                readline.read_history_file(HISTORY_PATH)
        except OSError:
            pass

    agent = Agent(cfg, cwd=cwd, mcp=mcp, subagent_defs=subagents)

    if args.cont:
        sessions = list_sessions(cwd)
        if sessions:
            agent.load_session(sessions[0])
        else:
            info("no previous session here — starting fresh")

    try:
        if args.oneshot:
            agent.run_turn(args.oneshot)
            return

        signal.signal(signal.SIGINT, signal.default_int_handler)
        n_custom = len(subagents) + len(commands) + len(mcp)
        extras = f"  +{n_custom} custom" if n_custom else ""
        print(f"{C.MAGENTA}{C.BOLD}claw{C.RESET} v{VERSION}  "
              f"{C.DIM}model={cfg['model']}  mode={cfg['mode']}{extras}{C.RESET}")
        info("/help for commands · /plan to plan first · ctrl-d to quit")
        while True:
            try:
                user_input = read_user_input(agent)
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                continue
            if not user_input:
                continue
            if user_input.startswith("# "):
                remember(user_input[2:], agent.tools.cwd)
                continue
            if user_input.startswith("/"):
                try:
                    if handle_slash(user_input, agent, cfg, commands):
                        continue
                    err(f"unknown command: {user_input.split()[0]} — try /help")
                    continue
                except EOFError:
                    break
            agent.run_turn(expand_mentions(user_input, agent.tools))
        if "readline" in sys.modules:
            try:
                readline.write_history_file(HISTORY_PATH)
            except OSError:
                pass
        info("bye")
    finally:
        for srv in mcp.values():
            srv.stop()

if __name__ == "__main__":
    main()
