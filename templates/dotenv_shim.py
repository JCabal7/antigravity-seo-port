"""Tiny dotenv loader that script-only extension scripts source on import.

Usage in any wrapped script:

    import dotenv_shim  # noqa: F401 — loads ~/.gemini/antigravity/skills/seo/.env into os.environ

No dependencies. Silently no-ops if the .env file doesn't exist.
"""
from __future__ import annotations

import os
from pathlib import Path

_ENV_PATH = Path.home() / ".gemini" / "antigravity" / "skills" / "seo" / ".env"


def _load() -> None:
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key, sep, val = s.partition("=")
        if not sep:
            continue
        v = val.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
            v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        os.environ.setdefault(key.strip(), v)


_load()
