"""Tests for lib/convert.py — skill/agent conversion logic."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from lib import convert


def test_parse_frontmatter_extracts_yaml_and_body():
    raw = textwrap.dedent("""\
        ---
        name: seo-audit
        description: Full audit.
        ---

        # Body

        Run: python scripts/x.py
        """)
    fm, body = convert.parse_frontmatter(raw)
    assert fm == {"name": "seo-audit", "description": "Full audit."}
    assert body.startswith("# Body")


def test_parse_frontmatter_handles_multiline_description():
    raw = textwrap.dedent("""\
        ---
        name: x
        description: >
          line one
          line two
        ---
        body
        """)
    fm, _ = convert.parse_frontmatter(raw)
    assert fm["description"].strip() == "line one line two"


def test_parse_frontmatter_handles_nested_metadata():
    raw = textwrap.dedent("""\
        ---
        name: x
        description: x
        metadata:
          author: AgriciDaniel
          version: "2.0.0"
        ---
        body
        """)
    fm, _ = convert.parse_frontmatter(raw)
    assert fm["metadata"]["author"] == "AgriciDaniel"
    assert fm["metadata"]["version"] == "2.0.0"


def test_parse_frontmatter_no_frontmatter_returns_empty_dict():
    raw = "# Just a body, no frontmatter\n"
    fm, body = convert.parse_frontmatter(raw)
    assert fm == {}
    assert body == raw


def test_normalize_frontmatter_keeps_required_keys():
    fm = {"name": "x", "description": "d", "model": "sonnet", "tools": "Read, Bash"}
    out = convert.normalize_frontmatter(fm)
    assert out == fm


def test_normalize_frontmatter_strips_claude_only_keys():
    fm = {
        "name": "x",
        "description": "d",
        "maxTurns": 20,
        "user-invokable": True,
        "argument-hint": "[url]",
        "license": "MIT",
    }
    out = convert.normalize_frontmatter(fm)
    assert "maxTurns" not in out
    assert "user-invokable" not in out
    assert "argument-hint" not in out
    assert "license" not in out
    assert out["name"] == "x"
    assert out["description"] == "d"


def test_normalize_frontmatter_preserves_metadata_block():
    # If §9 unknown #5 proves Antigravity tolerates nested metadata, keep it.
    # Otherwise: this test must be updated to assert flattening.
    fm = {"name": "x", "description": "d", "metadata": {"author": "A", "version": "1.0"}}
    out = convert.normalize_frontmatter(fm)
    assert out["metadata"] == {"author": "A", "version": "1.0"}
