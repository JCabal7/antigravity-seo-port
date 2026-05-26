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


def install_mcp_server(
    config_path: Path,
    ext_name: str,
    *,
    credentials: dict[str, str],
    extra_env: dict[str, str] | None = None,
) -> None:
    """Merge an MCP server entry into the Antigravity mcp_config.json.

    Idempotent: same `ext_name` overwrites its own entry. Other entries
    are preserved byte-for-byte.

    Raises:
        KeyError if `ext_name` is not in MCP_SERVERS.
        ValueError if any required env var from the spec is missing.
    """
    spec = MCP_SERVERS[ext_name]  # raises KeyError on unknown

    env: dict[str, str] = {}
    env.update(spec["env_defaults"])
    for var in spec["env_vars"]:
        if var not in credentials or not credentials[var]:
            raise ValueError(f"missing required env var {var} for {ext_name}")
        env[var] = credentials[var]
    if extra_env:
        env.update(extra_env)

    cfg = _read_config(config_path)
    cfg.setdefault("mcpServers", {})
    cfg["mcpServers"][spec["server_name"]] = {
        "command": spec["command"],
        "args": list(spec["args"]),
        "env": env,
    }
    atomic_write_json(config_path, cfg)


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def remove_mcp_server(config_path: Path, ext_name: str) -> None:
    """Remove a previously-installed MCP server entry. No-op if absent."""
    if not config_path.exists():
        return
    spec = MCP_SERVERS.get(ext_name)
    if spec is None:
        return
    cfg = _read_config(config_path)
    servers = cfg.get("mcpServers", {})
    if spec["server_name"] in servers:
        del servers[spec["server_name"]]
        atomic_write_json(config_path, cfg)
