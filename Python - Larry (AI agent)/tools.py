import subprocess
from pathlib import Path
from urllib.parse import unquote

from config import DATA_DIR, MEMORY_FILE, SKILLS_DIR


def _path(raw: str) -> Path:
    return Path(unquote(raw)).expanduser()

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save a fact or note to persistent memory — loaded automatically at the start of every future session",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The note or fact to remember"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": "Read everything currently stored in persistent memory",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_skill",
            "description": "Create a new skill — a named set of instructions that can be loaded into any session to change behavior",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Short slug name for the skill (e.g. python-expert)"},
                    "description": {"type": "string", "description": "One line describing what this skill does"},
                    "instructions": {"type": "string", "description": "The full instructions for this skill"}
                },
                "required": ["name", "description", "instructions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": "List all available skills",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and folders in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path, defaults to current directory"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files by name or grep for text inside files",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern"},
                    "search_type": {
                        "type": "string",
                        "enum": ["name", "content"],
                        "description": "Search by filename or file content"
                    },
                    "path": {"type": "string", "description": "Directory to search in, defaults to current"}
                },
                "required": ["pattern", "search_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to any file type (.py .cpp .js .ts .html .css .json .yaml .md .txt .sh .c .h .rs .go .java etc) — creates it and any missing parent directories automatically",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace an exact string in a file with new content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string", "description": "Exact text to find and replace"},
                    "new_string": {"type": "string", "description": "Text to replace it with"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Run a shell command and return stdout/stderr",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "working_dir": {"type": "string", "description": "Optional working directory for the command"}
                },
                "required": ["command"]
            }
        }
    }
]

DESTRUCTIVE_TOOLS = {"write_file", "edit_file", "run_bash", "save_memory", "create_skill"}
READONLY_TOOLS = {"read_file", "list_directory", "search_files", "read_memory", "list_skills"}


def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "save_memory":
            DATA_DIR.mkdir(exist_ok=True)
            existing = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""
            separator = "\n" if existing and not existing.endswith("\n") else ""
            MEMORY_FILE.write_text(existing + separator + args["content"].strip() + "\n", encoding="utf-8")
            return "Memory saved."

        elif name == "read_memory":
            if not MEMORY_FILE.exists():
                return "(no memory yet)"
            content = MEMORY_FILE.read_text(encoding="utf-8").strip()
            return content if content else "(memory is empty)"

        elif name == "create_skill":
            SKILLS_DIR.mkdir(parents=True, exist_ok=True)
            name_slug = args["name"].lower().replace(" ", "-")
            path = SKILLS_DIR / f"{name_slug}.md"
            path.write_text(
                f"# {name_slug}\n\n"
                f"**Description:** {args['description']}\n\n"
                f"## Instructions\n\n{args['instructions']}\n",
                encoding="utf-8"
            )
            return f"Skill '{name_slug}' created at {path}"

        elif name == "list_skills":
            if not SKILLS_DIR.exists():
                return "(no skills yet)"
            files = sorted(SKILLS_DIR.glob("*.md"))
            if not files:
                return "(no skills yet)"
            lines = []
            for f in files:
                first_line = f.read_text(encoding="utf-8").split("\n")
                desc = next((l.replace("**Description:**", "").strip() for l in first_line if "Description:" in l), "")
                lines.append(f"{f.stem}  —  {desc}" if desc else f.stem)
            return "\n".join(lines)

        elif name == "read_file":
            path = _path(args["path"])
            if not path.exists():
                return f"Error: file not found: {path}"
            return path.read_text(encoding="utf-8", errors="replace")

        elif name == "list_directory":
            path = _path(args.get("path", "."))
            if not path.exists():
                return f"Error: directory not found: {path}"
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            lines = [f"{'[dir] ' if e.is_dir() else '[file]'} {e.name}" for e in entries]
            return "\n".join(lines) if lines else "(empty directory)"

        elif name == "search_files":
            base = args.get("path", ".")
            pattern = args["pattern"]
            if args["search_type"] == "name":
                result = subprocess.run(
                    ["find", base, "-name", pattern],
                    capture_output=True, text=True, timeout=15
                )
            else:
                result = subprocess.run(
                    f'grep -r {repr(pattern)} {base} -l 2>/dev/null | head -30',
                    shell=True, capture_output=True, text=True, timeout=15
                )
            return result.stdout.strip() or "No results found"

        elif name == "write_file":
            path = _path(args["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"], encoding="utf-8")
            return f"Wrote {len(args['content'])} chars to {path}"

        elif name == "edit_file":
            path = _path(args["path"])
            if not path.exists():
                return f"Error: file not found: {path}"
            content = path.read_text(encoding="utf-8")
            if args["old_string"] not in content:
                return "Error: old_string not found in file — no changes made"
            new_content = content.replace(args["old_string"], args["new_string"], 1)
            path.write_text(new_content, encoding="utf-8")
            return f"Edit applied to {path}"

        elif name == "run_bash":
            cwd = args.get("working_dir") or None
            result = subprocess.run(
                args["command"], shell=True,
                capture_output=True, text=True, timeout=30, cwd=cwd
            )
            out = result.stdout
            if result.stderr:
                out += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                out += f"\n[exit code: {result.returncode}]"
            return out.strip() or "(no output)"

        else:
            return f"Unknown tool: {name}"

    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30s"
    except Exception as e:
        return f"Error: {e}"
