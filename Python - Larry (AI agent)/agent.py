import ollama
from rich.console import Console
from rich.prompt import Confirm

from config import Config, MEMORY_FILE, SKILLS_DIR, OBSIDIAN_VAULT
from tools import TOOL_DEFINITIONS, DESTRUCTIVE_TOOLS, READONLY_TOOLS, execute_tool

console = Console()

SYSTEM_PROMPT_BASE = f"""\
You are Larry, a local coding assistant with full filesystem access via tools.

Tool rules:
- General knowledge questions ("explain X", "how does Y work") → answer directly, no tools needed
- User gives a file path → read_file immediately, no questions
- User asks to create/edit/run something → use write_file, edit_file, run_bash immediately
- write_file works for ALL file types: .py .cpp .c .h .js .ts .html .css .json .yaml .md .sh .rs .go .java .txt and anything else — always use it, never say you can't create a file type
- User asks about their Obsidian notes/vault → use list_directory and read_file on the vault below
- Do NOT save notes or write files unless the user explicitly asks

Obsidian vault: {OBSIDIAN_VAULT}
You have full read/write access to it via the file tools. Never say you can't access it.

After using tools, always write a reply summarizing what you found or did.\
"""


def _build_system_prompt(active_skills: list) -> str:
    parts = [SYSTEM_PROMPT_BASE]

    if MEMORY_FILE.exists():
        memory = MEMORY_FILE.read_text(encoding="utf-8").strip()
        if memory:
            parts.append(f"## Your Memory\n{memory}")

    for skill_name in active_skills:
        path = SKILLS_DIR / f"{skill_name}.md"
        if path.exists():
            parts.append(f"## Active Skill: {skill_name}\n{path.read_text(encoding='utf-8').strip()}")

    return "\n\n".join(parts)


class Agent:
    def __init__(self, config: Config):
        self.config = config
        self.messages: list = [{"role": "system", "content": _build_system_prompt(config.active_skills)}]

    def reload_system_prompt(self):
        self.messages[0] = {"role": "system", "content": _build_system_prompt(self.config.active_skills)}

    def _allowed(self, tool_name: str, args: dict) -> bool:
        mode = self.config.permission_mode

        if mode == "readonly" and tool_name in DESTRUCTIVE_TOOLS:
            console.print(f"  [red]blocked[/red] — {tool_name} not allowed in readonly mode")
            return False

        if mode == "auto" or tool_name in READONLY_TOOLS:
            return True

        # ask mode — prompt for destructive tools
        preview = "  " + "\n  ".join(
            f"[dim]{k}:[/dim] {str(v)[:120]}{'...' if len(str(v)) > 120 else ''}"
            for k, v in args.items()
        )
        console.print(f"\n[yellow]  permission needed:[/yellow] [bold]{tool_name}[/bold]")
        console.print(preview)
        return Confirm.ask("  allow?", default=True)

    def run_turn(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})

        with console.status("[cyan]thinking...[/cyan]", spinner="dots"):
            response = ollama.chat(
                model=self.config.model,
                messages=self.messages,
                tools=TOOL_DEFINITIONS,
                options={"temperature": self.config.temperature},
            )

        # agentic loop — keep calling tools until the model stops
        while response.message.tool_calls:
            self.messages.append(response.message)

            for call in response.message.tool_calls:
                name = call.function.name
                args = dict(call.function.arguments)

                arg_preview = ", ".join(
                    f"{k}={repr(str(v)[:60])}" for k, v in args.items()
                )
                console.print(f"  [dim]→ {name}({arg_preview})[/dim]")

                if self._allowed(name, args):
                    result = execute_tool(name, args)
                    console.print(f"  [dim green]✓[/dim green]")
                else:
                    result = "Permission denied."

                self.messages.append({"role": "tool", "content": result})

            with console.status("[cyan]thinking...[/cyan]", spinner="dots"):
                response = ollama.chat(
                    model=self.config.model,
                    messages=self.messages,
                    tools=TOOL_DEFINITIONS,
                )

        reply = response.message.content or ""

        # model returned empty after tool calls — nudge it to summarize
        if not reply and len(self.messages) > 2:
            self.messages.append({"role": "assistant", "content": ""})
            self.messages.append({"role": "user", "content": "Summarize what you found or did."})
            with console.status("[cyan]thinking...[/cyan]", spinner="dots"):
                followup = ollama.chat(
                    model=self.config.model,
                    messages=self.messages,
                    options={"temperature": self.config.temperature},
                )
            reply = followup.message.content or ""
            self.messages.pop()  # remove the nudge prompt from history
            self.messages.pop()

        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def clear(self):
        self.messages = [{"role": "system", "content": _build_system_prompt(self.config.active_skills)}]
