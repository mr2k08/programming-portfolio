#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()

HELP_TEXT = """\
[bold]Slash commands[/bold]

  [cyan]/model[/cyan]  [dim]([/dim][cyan]/m[/cyan][dim])[/dim]   [dim][name]          [/dim]  show or switch model
  [cyan]/mode[/cyan]   [dim]([/dim][cyan]/mo[/cyan][dim])[/dim]  [dim]auto|ask|readonly[/dim]  permission mode
  [cyan]/effort[/cyan] [dim]([/dim][cyan]/e[/cyan][dim])[/dim]   [dim]low|medium|high|max[/dim] temperature
  [cyan]/skill[/cyan]  [dim]([/dim][cyan]/s[/cyan][dim])[/dim]   [dim]list|load|unload|show[/dim]
  [cyan]/memory[/cyan] [dim]([/dim][cyan]/mem[/cyan][dim])[/dim]                      show memory
  [cyan]/btw[/cyan]    [dim]<note>[/dim]                     save a note silently, no model reply
  [cyan]/clear[/cyan]                             clear conversation
  [cyan]/status[/cyan]                            show current config
  [cyan]/help[/cyan]                              this screen
  [cyan]/exit[/cyan]                              quit

[bold]Effort levels[/bold]
  [green]low[/green]     0.1  — precise, deterministic  [dim](best for code)[/dim]
  [yellow]medium[/yellow]  0.5  — balanced  [dim](default)[/dim]
  [yellow]high[/yellow]    0.8  — creative
  [red]max[/red]     1.0  — most random

[bold]Permission modes[/bold]
  [green]auto[/green]      no prompts
  [yellow]ask[/yellow]       prompt before writes/bash  [dim](default)[/dim]
  [red]readonly[/red]  reads only\
"""


def _effort_label(temp: float) -> str:
    from config import EFFORT_LEVELS
    for name, val in EFFORT_LEVELS.items():
        if abs(val - temp) < 0.01:
            return name
    return f"{temp:.1f}"


def _print_status(config):
    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim")
    t.add_column()
    t.add_row("model",  f"[cyan]{config.model}[/cyan]")
    t.add_row("mode",   config.permission_mode)
    t.add_row("effort", f"{_effort_label(config.temperature)}  [dim]({config.temperature})[/dim]")
    t.add_row("skills", ", ".join(config.active_skills) if config.active_skills else "[dim]none[/dim]")
    t.add_row("dir",    os.getcwd())
    console.print(Panel(t, border_style="dim"))


def main():
    from config import Config, MEMORY_FILE, SKILLS_DIR, EFFORT_LEVELS
    from agent import Agent

    config = Config()

    if len(sys.argv) > 1:
        target = Path(sys.argv[1]).expanduser().resolve()
        if target.is_dir():
            os.chdir(target)
            config.working_dir = str(target)

    agent = Agent(config)

    memory_status = "[green]memory[/green]" if MEMORY_FILE.exists() and MEMORY_FILE.stat().st_size > 0 else "[dim]no memory[/dim]"
    skill_count = len(list(SKILLS_DIR.glob("*.md"))) if SKILLS_DIR.exists() else 0
    skills_status = f"[dim]{skill_count} skill{'s' if skill_count != 1 else ''}[/dim]"

    console.print(Panel(
        f"[bold cyan]Larry[/bold cyan]  [dim]powered by ollama[/dim]\n"
        f"[dim]model: {config.model}  |  mode: {config.permission_mode}  |  effort: {_effort_label(config.temperature)}[/dim]\n"
        f"{memory_status}  ·  {skills_status}  ·  [dim]/help[/dim]",
        border_style="cyan"
    ))

    # map aliases → canonical command
    ALIASES = {
        "/m":   "/model",
        "/mo":  "/mode",
        "/e":   "/effort",
        "/s":   "/skill",
        "/mem": "/memory",
    }

    def handle_slash(raw: str) -> bool:
        """Process one slash command. Returns True if /exit was requested."""
        parts = raw.strip().split(maxsplit=1)
        cmd = ALIASES.get(parts[0].lower(), parts[0].lower())
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/exit":
            return True

        elif cmd == "/clear":
            agent.clear()
            console.print("[dim]conversation cleared.[/dim]")

        elif cmd == "/help":
            console.print(Panel(HELP_TEXT, title="Larry — commands", border_style="dim"))

        elif cmd == "/status":
            _print_status(config)

        elif cmd == "/model":
            if arg:
                config.model = arg
                console.print(f"[dim]model → {config.model}[/dim]")
            else:
                console.print(f"[dim]{config.model}[/dim]")

        elif cmd == "/mode":
            if arg in ("auto", "ask", "readonly"):
                config.permission_mode = arg
                console.print(f"[dim]mode → {config.permission_mode}[/dim]")
            else:
                console.print("[dim]usage: /mode auto|ask|readonly[/dim]")

        elif cmd == "/effort":
            if arg in EFFORT_LEVELS:
                config.temperature = EFFORT_LEVELS[arg]
                console.print(f"[dim]effort → {arg} ({config.temperature})[/dim]")
            elif arg:
                try:
                    config.temperature = float(arg)
                    console.print(f"[dim]temperature → {config.temperature}[/dim]")
                except ValueError:
                    console.print("[dim]usage: /effort low|medium|high|max[/dim]")
            else:
                console.print(f"[dim]effort: {_effort_label(config.temperature)} ({config.temperature})[/dim]")

        elif cmd == "/memory":
            if MEMORY_FILE.exists():
                content = MEMORY_FILE.read_text(encoding="utf-8").strip()
                console.print(Panel(content or "(empty)", title="memory", border_style="dim"))
            else:
                console.print("[dim](no memory yet)[/dim]")

        elif cmd == "/btw":
            if not arg:
                console.print("[dim]usage: /btw <note>[/dim]")
            else:
                from config import DATA_DIR
                DATA_DIR.mkdir(exist_ok=True)
                existing = MEMORY_FILE.read_text(encoding="utf-8") if MEMORY_FILE.exists() else ""
                sep = "\n" if existing and not existing.endswith("\n") else ""
                MEMORY_FILE.write_text(existing + sep + arg.strip() + "\n", encoding="utf-8")
                agent.reload_system_prompt()
                console.print(f"[dim]noted.[/dim]")

        elif cmd == "/skill":
            sub, _, rest = arg.partition(" ")
            rest = rest.strip()

            if sub in ("list", "") or not sub:
                if not SKILLS_DIR.exists() or not list(SKILLS_DIR.glob("*.md")):
                    console.print("[dim](no skills yet)[/dim]")
                else:
                    active = set(config.active_skills)
                    for f in sorted(SKILLS_DIR.glob("*.md")):
                        marker = "[green]●[/green]" if f.stem in active else "[dim]○[/dim]"
                        console.print(f"  {marker} {f.stem}")

            elif sub == "load":
                if not rest:
                    console.print("[dim]usage: /skill load <name>[/dim]")
                else:
                    path = SKILLS_DIR / f"{rest}.md"
                    if not path.exists():
                        console.print(f"[red]skill '{rest}' not found[/red]")
                    elif rest in config.active_skills:
                        console.print(f"[dim]'{rest}' already active[/dim]")
                    else:
                        config.active_skills.append(rest)
                        agent.reload_system_prompt()
                        console.print(f"[green]loaded:[/green] {rest}")

            elif sub == "unload":
                if rest in config.active_skills:
                    config.active_skills.remove(rest)
                    agent.reload_system_prompt()
                    console.print(f"[dim]unloaded: {rest}[/dim]")
                else:
                    console.print(f"[dim]'{rest}' not active[/dim]")

            elif sub == "show":
                if not rest:
                    console.print("[dim]usage: /skill show <name>[/dim]")
                else:
                    path = SKILLS_DIR / f"{rest}.md"
                    if path.exists():
                        console.print(Panel(path.read_text(encoding="utf-8"), title=rest, border_style="dim"))
                    else:
                        console.print(f"[red]skill '{rest}' not found[/red]")

            else:
                console.print("[dim]/skill  list | load <name> | unload <name> | show <name>[/dim]")

        else:
            console.print(f"[dim]unknown command '{cmd}' — /help[/dim]")

        return False

    while True:
        try:
            user_input = console.input("\n[bold green]>[/bold green] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]bye.[/dim]")
            break

        if not user_input:
            continue

        # chained slash commands: /m qwen2.5:3b; /e low; /mo auto
        if user_input.startswith("/"):
            chunks = [c.strip() for c in user_input.split(";") if c.strip()]
            should_exit = False
            for chunk in chunks:
                if handle_slash(chunk):
                    should_exit = True
                    break
            if should_exit:
                console.print("[dim]bye.[/dim]")
                break
            continue

        try:
            reply = agent.run_turn(user_input)
            if reply:
                console.print()
                console.print(Markdown(reply))
        except KeyboardInterrupt:
            console.print("\n[dim]interrupted.[/dim]")
        except Exception as e:
            console.print(f"\n[red]error:[/red] {e}")


if __name__ == "__main__":
    main()
