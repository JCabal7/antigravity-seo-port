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


MCP_SERVERS: dict[str, dict[str, Any]] = {
    "firecrawl": {
        "server_name": "firecrawl-mcp",
        "command": "npx",
        "args": ["-y", "firecrawl-mcp@3.11.0"],
        "env_vars": ["FIRECRAWL_API_KEY"],
        "env_defaults": {},
    },
    "dataforseo": {
        "server_name": "dataforseo",
        "command": "npx",
        "args": ["-y", "dataforseo-mcp-server@2.8.10"],
        "env_vars": ["DATAFORSEO_USERNAME", "DATAFORSEO_PASSWORD"],
        "env_defaults": {
            "ENABLED_MODULES": (
                "SERP,KEYWORDS_DATA,ONPAGE,DATAFORSEO_LABS,BACKLINKS,"
                "DOMAIN_ANALYTICS,BUSINESS_DATA,CONTENT_ANALYSIS,AI_OPTIMIZATION"
            ),
        },
    },
    "banana": {
        "server_name": "nanobanana-mcp",
        "command": "npx",
        "args": ["-y", "@ycse/nanobanana-mcp@1.1.1"],
        "env_vars": ["GOOGLE_AI_API_KEY"],
        "env_defaults": {},
    },
    "ahrefs": {
        "server_name": "ahrefs",
        "command": "npx",
        "args": ["--yes", "--package=@ahrefs/mcp", "ahrefs-mcp"],
        "env_vars": ["AHREFS_API_TOKEN"],
        "env_defaults": {},
    },
}
