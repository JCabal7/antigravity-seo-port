"""Skill/agent conversion for the Antigravity port.

Pure transforms on strings and file paths. No knowledge of install paths.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md / agent.md into (frontmatter_dict, body_str).

    Uses a small YAML subset parser (no external deps): top-level keys,
    inline values, folded (`>`) scalars, and one level of nested mapping.
    Returns ({}, raw) if no frontmatter delimiter is present.
    """
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    yaml_blob, body = m.group(1), m.group(2)
    return _parse_yaml_subset(yaml_blob), body.lstrip("\n")


def _parse_yaml_subset(blob: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    lines = blob.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith(" "):
            i += 1
            continue  # handled by parent in nested case
        key, sep, rest = line.partition(":")
        if not sep:
            i += 1
            continue
        key = key.strip()
        rest = rest.strip()
        if rest == ">" or rest == "|":
            # Folded / literal scalar — collect indented continuation
            parts: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                if lines[i].strip():
                    parts.append(lines[i].strip())
                i += 1
            sep_char = " " if rest == ">" else "\n"
            result[key] = sep_char.join(parts)
            continue
        if rest == "":
            # Nested mapping — collect indented child lines
            nested: dict[str, Any] = {}
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                if lines[i].strip():
                    cline = lines[i].lstrip()
                    ckey, csep, cval = cline.partition(":")
                    if csep:
                        nested[ckey.strip()] = _unquote(cval.strip())
                i += 1
            result[key] = nested
            continue
        result[key] = _unquote(rest)
        i += 1
    return result


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'"}:
        return s[1:-1]
    return s


_KEEP_KEYS = {"name", "description", "model", "tools", "metadata"}


def normalize_frontmatter(fm: dict[str, Any]) -> dict[str, Any]:
    """Strip Claude-Code-only keys; keep the portable subset Antigravity reads.

    Per spec §4.3 step 1. If Task 1.5 finds Antigravity rejects `metadata`
    as a nested block, update _KEEP_KEYS and add a flattening pass here.
    """
    return {k: v for k, v in fm.items() if k in _KEEP_KEYS}


def serialize_frontmatter(fm: dict[str, Any]) -> str:
    """Emit YAML frontmatter for a normalized dict. Returns string ending with `---\n`."""
    lines = ["---"]
    for key, val in fm.items():
        if isinstance(val, dict):
            lines.append(f"{key}:")
            for ck, cv in val.items():
                lines.append(f"  {ck}: {_yaml_value(cv)}")
        else:
            lines.append(f"{key}: {_yaml_value(val)}")
    lines.append("---\n")
    return "\n".join(lines)


def _yaml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in (":", "#", "'", '"', "\n")):
        return '"' + s.replace('"', '\\"') + '"'
    return s


_PATH_REWRITE_PATTERNS = {
    "scripts": re.compile(r"(?<![\w/])(?:\./)?scripts/([\w.\-]+\.(?:py|sh))"),
    "schema": re.compile(r"(?<![\w/])(?:\./)?schema/([\w.\-/]+\.(?:json|md))"),
    "pdf": re.compile(r"(?<![\w/])(?:\./)?pdf/([\w.\-/]+\.(?:pdf|md))"),
    "data": re.compile(r"(?<![\w/])(?:\./)?data/([\w.\-/]+\.(?:csv|json|md|txt))"),
}


def rewrite_paths(
    body: str,
    *,
    scripts_dir: str | None = None,
    schema_dir: str | None = None,
    pdf_dir: str | None = None,
    data_dir: str | None = None,
) -> str:
    """Rewrite `scripts/<file>` etc. to absolute install-path refs.

    Only rewrites paths that look like file references (have a recognized
    file extension). Bare directory mentions in prose are left untouched.
    """
    dirs = {"scripts": scripts_dir, "schema": schema_dir, "pdf": pdf_dir, "data": data_dir}
    for key, target_dir in dirs.items():
        if target_dir is None:
            continue
        body = _PATH_REWRITE_PATTERNS[key].sub(rf"{target_dir}/\1", body)
    return body
