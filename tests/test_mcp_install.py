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
