"""MCP server installation for the Antigravity port.

Idempotent merges into ~/.gemini/config/mcp_config.json. Atomic writes
(temp file + rename) so a crash mid-write cannot corrupt the config.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write `data` as pretty JSON to `path` atomically (temp + rename).

    The temp file is created in the same directory so the final rename is
    atomic on the same filesystem.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
