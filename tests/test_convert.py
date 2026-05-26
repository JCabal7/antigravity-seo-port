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


def test_serialize_frontmatter_roundtrip_simple():
    fm = {"name": "x", "description": "A skill"}
    out = convert.serialize_frontmatter(fm)
    assert out == "---\nname: x\ndescription: A skill\n---\n"


def test_serialize_frontmatter_quotes_when_needed():
    fm = {"name": "x", "description": "Contains: colon"}
    out = convert.serialize_frontmatter(fm)
    # Must round-trip through parser
    parsed, _ = convert.parse_frontmatter(out + "\nbody")
    assert parsed["description"] == "Contains: colon"


def test_serialize_frontmatter_handles_nested_metadata():
    fm = {"name": "x", "description": "d", "metadata": {"author": "A", "version": "1.0"}}
    out = convert.serialize_frontmatter(fm)
    parsed, _ = convert.parse_frontmatter(out + "\nbody")
    assert parsed["metadata"]["author"] == "A"
    assert parsed["metadata"]["version"] == "1.0"


def test_rewrite_paths_replaces_scripts_refs():
    body = "Run: `python scripts/fetch_page.py <url>` then `./scripts/score.py`."
    out = convert.rewrite_paths(body, scripts_dir="/install/scripts")
    assert "/install/scripts/fetch_page.py" in out
    assert "/install/scripts/score.py" in out
    assert "scripts/fetch_page.py" not in out


def test_rewrite_paths_replaces_schema_pdf_data():
    body = "See `schema/templates.json` and `pdf/guide.pdf` and `data/sample.csv`."
    out = convert.rewrite_paths(
        body,
        scripts_dir="/install/scripts",
        schema_dir="/install/schema",
        pdf_dir="/install/pdf",
        data_dir="/install/data",
    )
    assert "/install/schema/templates.json" in out
    assert "/install/pdf/guide.pdf" in out
    assert "/install/data/sample.csv" in out


def test_rewrite_paths_leaves_unrelated_text_alone():
    body = "Description of scripts/api with no actual file ref."
    out = convert.rewrite_paths(body, scripts_dir="/install/scripts")
    # Only the literal "scripts/<filename>.py" pattern gets touched
    assert "/install/scripts/api" not in out


def test_agent_to_skill_renames_on_collision():
    out_name = convert.agent_target_skill_name("seo-technical", existing_skills={"seo-technical"})
    assert out_name == "seo-technical-agent"


def test_agent_to_skill_keeps_name_when_no_collision():
    out_name = convert.agent_target_skill_name("seo-content", existing_skills={"seo-audit"})
    assert out_name == "seo-content"


def test_convert_agent_to_skill_normalizes_frontmatter():
    agent_md = (
        "---\nname: seo-technical\ndescription: Specialist.\n"
        "model: sonnet\nmaxTurns: 20\ntools: Read, Bash\n---\n\n"
        "You are a Technical SEO specialist.\n"
    )
    new_name = "seo-technical-agent"
    out = convert.convert_agent_to_skill(agent_md, new_name=new_name)
    fm, body = convert.parse_frontmatter(out)
    assert fm["name"] == "seo-technical-agent"
    assert fm["description"].startswith("Specialist")
    assert "maxTurns" not in fm
    assert "You are a Technical SEO specialist" in body


def test_convert_skill_normalizes_and_rewrites_paths():
    raw = (
        "---\nname: seo-audit\ndescription: Full audit.\n"
        "maxTurns: 20\nuser-invokable: true\n---\n\n"
        "Run: `python scripts/fetch_page.py <url>` then see `schema/templates.json`.\n"
    )
    out = convert.convert_skill(
        raw,
        scripts_dir="/install/scripts",
        schema_dir="/install/schema",
    )
    fm, body = convert.parse_frontmatter(out)
    assert fm == {"name": "seo-audit", "description": "Full audit."}
    assert "/install/scripts/fetch_page.py" in body
    assert "/install/schema/templates.json" in body
    assert "maxTurns" not in out


def test_convert_tree_copies_and_normalizes_skills(tmp_upstream, tmp_path):
    out_dir = tmp_path / "staging"
    convert.convert_tree(
        src=tmp_upstream,
        dst=out_dir,
        scripts_dir="/install/scripts",
        schema_dir="/install/schema",
        pdf_dir="/install/pdf",
        data_dir="/install/data",
    )
    audit = (out_dir / "skills" / "seo-audit" / "SKILL.md").read_text()
    assert "name: seo-audit" in audit
    assert "maxTurns" not in audit
    assert "/install/scripts/fetch_page.py" in audit


def test_convert_tree_maps_agents_to_skills(tmp_upstream, tmp_path):
    out_dir = tmp_path / "staging"
    convert.convert_tree(
        src=tmp_upstream,
        dst=out_dir,
        scripts_dir="/install/scripts",
    )
    # Existing skill `seo-audit` does NOT collide with `seo-technical` agent,
    # so the agent becomes a skill with the same name.
    technical = (out_dir / "skills" / "seo-technical" / "SKILL.md").read_text()
    assert "name: seo-technical" in technical
    assert "You are a Technical SEO specialist" in technical
