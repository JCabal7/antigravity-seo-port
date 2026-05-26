"""Owner-tagged .env file merges for script-only extensions.

Lines we own are bracketed with sentinel comments:

    # >>> antigravity-seo
    KEY="value"
    # <<< antigravity-seo

Other lines (set by user or other tools) are preserved.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def set_env_var(path: Path, key: str, value: str, *, owner: str) -> None:
    """Set or update KEY="value" inside the owner-tagged block. Creates file if missing.

    File is always written with mode 0o600 (user-read-write only).
    """
    begin = f"# >>> {owner}"
    end = f"# <<< {owner}"
    line = f'{key}="{_escape(value)}"'

    lines = path.read_text().splitlines() if path.exists() else []
    in_block = False
    block_lines: list[str] = []
    other_lines: list[str] = []
    saw_block = False
    found_key = False

    for ln in lines:
        if ln == begin:
            in_block = True
            saw_block = True
            continue
        if ln == end:
            in_block = False
            continue
        if in_block:
            # Replace existing key, or pass through.
            if ln.startswith(f"{key}="):
                block_lines.append(line)
                found_key = True
            else:
                block_lines.append(ln)
        else:
            other_lines.append(ln)

    if saw_block:
        if not found_key:
            block_lines.append(line)
    else:
        block_lines = [line]

    out_lines = other_lines[:]
    if other_lines and out_lines[-1] != "":
        out_lines.append("")
    out_lines.append(begin)
    out_lines.extend(block_lines)
    out_lines.append(end)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out_lines) + "\n")
    os.chmod(path, 0o600)


def remove_owner_block(path: Path, *, owner: str) -> None:
    """Strip the owner-tagged block from the file. Leaves other content intact."""
    if not path.exists():
        return
    begin = f"# >>> {owner}"
    end = f"# <<< {owner}"
    out: list[str] = []
    skipping = False
    for ln in path.read_text().splitlines():
        if ln == begin:
            skipping = True
            continue
        if ln == end:
            skipping = False
            continue
        if skipping:
            continue
        out.append(ln)
    # Trim trailing blank lines we may have introduced
    while out and out[-1] == "":
        out.pop()
    path.write_text("\n".join(out) + ("\n" if out else ""))
    os.chmod(path, 0o600)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


OWNER_TAG = "antigravity-seo"

SCRIPT_ONLY_EXTENSIONS: dict[str, dict[str, Any]] = {
    "bing-webmaster": {
        "skill_name": "seo-bing",
        "env_vars": ["BING_WEBMASTER_API_KEY", "INDEXNOW_KEY", "INDEXNOW_KEY_LOCATION"],
        "require_any_of": ["BING_WEBMASTER_API_KEY", "INDEXNOW_KEY"],
    },
    "profound": {
        "skill_name": "seo-profound",
        "env_vars": ["PROFOUND_API_KEY"],
        "require_any_of": ["PROFOUND_API_KEY"],
    },
    "seranking": {
        "skill_name": "seo-seranking",
        "env_vars": ["SERANKING_API_KEY"],
        "require_any_of": ["SERANKING_API_KEY"],
    },
    "unlighthouse": {
        "skill_name": "seo-unlighthouse",
        "env_vars": [],
        "require_any_of": [],
    },
}


def install_script_extension(
    env_path: Path,
    ext_name: str,
    *,
    credentials: dict[str, str],
) -> None:
    spec = SCRIPT_ONLY_EXTENSIONS[ext_name]
    if spec["require_any_of"] and not any(credentials.get(k) for k in spec["require_any_of"]):
        raise ValueError(
            f"{ext_name} requires at least one of: {', '.join(spec['require_any_of'])}"
        )
    for var in spec["env_vars"]:
        if credentials.get(var):
            set_env_var(env_path, var, credentials[var], owner=OWNER_TAG)


def uninstall_script_extension(env_path: Path) -> None:
    """Remove all owner-tagged keys from .env. (Coarse — removes everything we ever wrote.)"""
    remove_owner_block(env_path, owner=OWNER_TAG)
