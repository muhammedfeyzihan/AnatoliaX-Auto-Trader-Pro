"""
skill_loader.py — OpenClaw SKILL.md loader.

Parses OpenClaw skill definitions (SKILL.md files) and converts
them into AnatoliaX-compatible skill objects.

OpenClaw skill format (simplified):
    # Skill: <name>
    ## Setup
    <setup description>
    ## Parameters
    - param1: type = default
    ## Handler
    <python function path>

Usage:
    loader = SkillLoader()
    skill = loader.load_from_file("skills/signal_scan.md")
    skill = loader.load_from_string(markdown_text)
"""

import re
from dataclasses import dataclass
from typing import Dict, Optional
from pathlib import Path


@dataclass
class OpenClawSkill:
    name: str
    setup: str
    parameters: Dict[str, dict]
    handler: str  # Python import path, e.g., "PYTHON.paper_trading.signal_engine:SignalEngine"
    description: str = ""


class SkillLoader:
    """Parse OpenClaw SKILL.md into AnatoliaX skill objects."""

    def load_from_file(self, path: Path) -> Optional[OpenClawSkill]:
        if not path.exists():
            return None
        return self.load_from_string(path.read_text(encoding="utf-8"))

    def load_from_string(self, text: str) -> Optional[OpenClawSkill]:
        lines = text.splitlines()
        name = ""
        setup = ""
        params: Dict[str, dict] = {}
        handler = ""
        desc_lines: list[str] = []

        section = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# Skill:"):
                name = stripped.replace("# Skill:", "").strip()
                section = "header"
            elif stripped.startswith("## Setup"):
                section = "setup"
            elif stripped.startswith("## Parameters"):
                section = "parameters"
            elif stripped.startswith("## Handler"):
                section = "handler"
            elif stripped.startswith("## Description"):
                section = "description"
            elif stripped.startswith("##"):
                section = stripped.lower().replace("##", "").strip()
            elif section == "setup":
                setup += line + "\n"
            elif section == "parameters":
                # Parse "- param: type = default"
                m = re.match(r"-\s*(\w+)\s*:\s*(\w+)\s*(?:=\s*(.+))?", stripped)
                if m:
                    params[m.group(1)] = {
                        "type": m.group(2),
                        "default": m.group(3).strip() if m.group(3) else None,
                    }
            elif section == "handler":
                if stripped and not handler:
                    handler = stripped
            elif section == "description":
                desc_lines.append(line)

        if not name:
            return None

        return OpenClawSkill(
            name=name,
            setup=setup.strip(),
            parameters=params,
            handler=handler,
            description="\n".join(desc_lines).strip(),
        )

    def discover_skills(self, directory: Path) -> list[OpenClawSkill]:
        """Auto-discover all SKILL.md files in a directory."""
        skills = []
        if not directory.exists():
            return skills
        for fpath in directory.rglob("SKILL.md"):
            skill = self.load_from_file(fpath)
            if skill:
                skills.append(skill)
        return skills
