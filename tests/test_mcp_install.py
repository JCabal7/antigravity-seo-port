"""Tests for lib/mcp_install.py — MCP config merging."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib import mcp_install


def test_atomic_write_creates_file(tmp_path: Path):
    target = tmp_path / "out.json"
    mcp_install.atomic_write_json(target, {"key": "value"})
    assert json.loads(target.read_text()) == {"key": "value"}


def test_atomic_write_replaces_existing(tmp_path: Path):
    target = tmp_path / "out.json"
    target.write_text('{"old": true}')
    mcp_install.atomic_write_json(target, {"new": True})
    assert json.loads(target.read_text()) == {"new": True}


def test_atomic_write_leaves_no_temp_files(tmp_path: Path):
    target = tmp_path / "out.json"
    mcp_install.atomic_write_json(target, {"k": "v"})
    leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".out.json")]
    assert leftovers == []


def test_mcp_server_specs_includes_all_four():
    names = set(mcp_install.MCP_SERVERS.keys())
    assert names == {"firecrawl", "dataforseo", "banana", "ahrefs"}


def test_firecrawl_spec_shape():
    spec = mcp_install.MCP_SERVERS["firecrawl"]
    assert spec["server_name"] == "firecrawl-mcp"
    assert spec["command"] == "npx"
    assert "firecrawl-mcp@3.11.0" in spec["args"]
    assert spec["env_vars"] == ["FIRECRAWL_API_KEY"]


def test_dataforseo_spec_shape():
    spec = mcp_install.MCP_SERVERS["dataforseo"]
    assert spec["server_name"] == "dataforseo"
    assert "dataforseo-mcp-server@2.8.10" in spec["args"]
    assert "DATAFORSEO_USERNAME" in spec["env_vars"]
    assert "DATAFORSEO_PASSWORD" in spec["env_vars"]
    assert "ENABLED_MODULES" in spec["env_defaults"]
    assert "SERP" in spec["env_defaults"]["ENABLED_MODULES"]


def test_banana_spec_shape():
    spec = mcp_install.MCP_SERVERS["banana"]
    assert spec["server_name"] == "nanobanana-mcp"
    assert spec["env_vars"] == ["GOOGLE_AI_API_KEY"]


def test_ahrefs_spec_shape():
    spec = mcp_install.MCP_SERVERS["ahrefs"]
    assert spec["server_name"] == "ahrefs"
    assert spec["env_vars"] == ["AHREFS_API_TOKEN"]
