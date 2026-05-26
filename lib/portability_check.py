"""Frontmatter portability lint for installed SKILL.md files.

Adapted from upstream claude-seo's scripts/portability_check.py. Retargeted
to scan an arbitrary installed-skills directory instead of the upstream repo.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def check_tree(skills_dir: Path) -> list[dict[str, Any]]:
    """Walk every SKILL.md under `skills_dir`; return list of finding dicts.

    Finding dict: {"path": str, "severity": "error"|"warning"|"info", "rule": str, "message": str}
    """
    findings: list[dict[str, Any]] = []
    for skill_md in skills_dir.rglob("SKILL.md"):
        findings.extend(check_one(skill_md))
    return findings


def check_one(path: Path) -> list[dict[str, Any]]:
    text = path.read_text()
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return [_finding(path, "error", "no-frontmatter", "missing --- frontmatter block")]

    fm = _parse_simple(m.group(1))
    out: list[dict[str, Any]] = []
    name = fm.get("name")
    if not name:
        out.append(_finding(path, "error", "missing-name", "name: is required"))
    elif not _NAME_RE.match(name):
        out.append(_finding(path, "error", "name-not-kebab-case",
                            f"name={name!r} must be lowercase-kebab-case"))
    desc = fm.get("description")
    if not desc:
        out.append(_finding(path, "error", "missing-description", "description: is required"))
    elif len(desc) > 1024:
        out.append(_finding(path, "info", "long-description",
                            f"description is {len(desc)} chars (>1024)"))
    return out


def _parse_simple(blob: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in blob.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.startswith(" "):
            continue
        key, sep, val = line.partition(":")
        if sep:
            v = val.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
                v = v[1:-1]
            result[key.strip()] = v
    return result


def _finding(path: Path, severity: str, rule: str, message: str) -> dict[str, Any]:
    return {"path": str(path), "severity": severity, "rule": rule, "message": message}
