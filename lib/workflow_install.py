"""Workflow file generation for the /seo command tree."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "templates"

DISPATCHER_TEMPLATE = TEMPLATES / "seo-workflow.md.tmpl"
SUBCMD_TEMPLATE = TEMPLATES / "seo-subcmd-workflow.md.tmpl"


def render_dispatcher(subcmd_to_skill: dict[str, str]) -> str:
    """Render the /seo dispatcher from `subcmd → skill name` mapping."""
    subcmd_list = ", ".join(sorted(subcmd_to_skill.keys()))
    dispatch_lines = [
        f"- `{cmd}` → load skill `{skill}`"
        for cmd, skill in sorted(subcmd_to_skill.items())
    ]
    template = DISPATCHER_TEMPLATE.read_text()
    return (
        template
        .replace("{SUBCOMMAND_LIST}", subcmd_list)
        .replace("{DISPATCH_TABLE}", "\n".join(dispatch_lines))
    )


def render_subcmd_workflow(subcmd: str, skill_name: str, description: str) -> str:
    """Render a per-subcommand convenience workflow."""
    template = SUBCMD_TEMPLATE.read_text()
    short_desc = f"Shortcut for `/seo {subcmd}`. {description}"
    return (
        template
        .replace("{SUBCMD_DESCRIPTION}", short_desc.replace('"', "'"))
        .replace("{SUBCMD}", subcmd)
        .replace("{SKILL_NAME}", skill_name)
    )


def install_workflows(
    workflows_dir: Path,
    subcmd_to_skill: dict[str, str],
    descriptions: dict[str, str],
) -> None:
    """Write seo.md + seo-<subcmd>.md files into `workflows_dir`."""
    workflows_dir.mkdir(parents=True, exist_ok=True)
    (workflows_dir / "seo.md").write_text(render_dispatcher(subcmd_to_skill))
    for subcmd, skill in subcmd_to_skill.items():
        desc = descriptions.get(subcmd, f"Invoke the {skill} skill.")
        (workflows_dir / f"seo-{subcmd}.md").write_text(
            render_subcmd_workflow(subcmd, skill, desc)
        )


def uninstall_workflows(workflows_dir: Path) -> None:
    """Remove seo.md and seo-*.md (only the files this installer owns)."""
    if not workflows_dir.exists():
        return
    for f in workflows_dir.glob("seo.md"):
        f.unlink()
    for f in workflows_dir.glob("seo-*.md"):
        f.unlink()


_SKILL_NAME_FROM_FM = re.compile(r"^name:\s*(\S+)", re.MULTILINE)
_DESC_FROM_FM = re.compile(r"^description:\s*(.+)", re.MULTILINE)


def discover_subcommands(skills_dir: Path) -> dict[str, Any]:
    """Scan installed skills/ for `seo-*` skills; return subcommand → skill map.

    Excludes the orchestrator `seo` and agent-derived skills (suffix `-agent`).
    """
    subcmds: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name
        if name == "seo":
            continue
        if name.endswith("-agent"):
            continue
        if not name.startswith("seo-"):
            continue
        subcmd = name[len("seo-"):]
        subcmds[subcmd] = name
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            text = skill_md.read_text()
            m = _DESC_FROM_FM.search(text)
            if m:
                descriptions[subcmd] = m.group(1).strip().strip('"\'')
    return {"subcmds": subcmds, "descriptions": descriptions}
