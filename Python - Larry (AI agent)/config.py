from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PermissionMode = Literal["auto", "ask", "readonly"]

DATA_DIR = Path.home() / ".larry"
MEMORY_FILE = DATA_DIR / "memory.md"
SKILLS_DIR = DATA_DIR / "skills"

OBSIDIAN_VAULT = Path("/Users/marcrubeiz/Library/Mobile Documents/com~apple~CloudDocs/Work/.claude/Obsidian Vault")


EFFORT_LEVELS = {
    "low":    0.1,
    "medium": 0.5,
    "high":   0.8,
    "max":    1.0,
}

@dataclass
class Config:
    model: str = "qwen2.5:3b"
    permission_mode: PermissionMode = "ask"
    working_dir: str = "."
    active_skills: list = field(default_factory=list)
    temperature: float = 0.5
