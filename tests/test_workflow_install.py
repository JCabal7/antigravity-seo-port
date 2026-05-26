"""Tests for lib/workflow_install.py."""
from __future__ import annotations

from pathlib import Path

import pytest

from lib import workflow_install


SUBCMD_MAP = {
    "audit": "seo-audit",
    "page": "seo-page",
    "schema": "seo-schema",
}


def test_render_dispatcher_includes_all_subcommands():
    out = workflow_install.render_dispatcher(SUBCMD_MAP)
    assert "audit" in out
    assert "page" in out
    assert "schema" in out
    assert "seo-audit" in out


def test_render_dispatcher_has_valid_frontmatter():
    out = workflow_install.render_dispatcher(SUBCMD_MAP)
    assert out.startswith("---\n")
    assert "description:" in out.split("---", 2)[1]


def test_render_subcmd_workflow_binds_skill():
    out = workflow_install.render_subcmd_workflow("audit", "seo-audit", "Full website audit.")
    assert "seo-audit" in out
    assert "audit" in out
    assert "Full website audit." in out


def test_install_workflows_writes_all_files(tmp_install_root: Path):
    target = tmp_install_root / "workflows"
    descriptions = {"audit": "Full audit.", "page": "Single page.", "schema": "Schema."}
    workflow_install.install_workflows(target, SUBCMD_MAP, descriptions)
    assert (target / "seo.md").exists()
    assert (target / "seo-audit.md").exists()
    assert (target / "seo-page.md").exists()
    assert (target / "seo-schema.md").exists()
    dispatcher = (target / "seo.md").read_text()
    assert "audit" in dispatcher


def test_uninstall_workflows_removes_only_owned(tmp_install_root: Path):
    target = tmp_install_root / "workflows"
    target.mkdir(exist_ok=True)
    (target / "seo.md").write_text("owned")
    (target / "seo-audit.md").write_text("owned")
    (target / "user-other.md").write_text("user wrote this")
    workflow_install.uninstall_workflows(target)
    assert not (target / "seo.md").exists()
    assert not (target / "seo-audit.md").exists()
    assert (target / "user-other.md").exists()


def test_discover_subcommands_from_install_root(tmp_install_root: Path):
    skills = tmp_install_root / "skills"
    for name, desc in [
        ("seo", "orchestrator"),
        ("seo-audit", "Full website audit."),
        ("seo-page", "Single page analysis."),
        ("seo-schema", "Schema detection."),
        ("seo-technical-agent", "Specialist (agent-derived)."),
    ]:
        d = skills / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\nbody")
    result = workflow_install.discover_subcommands(skills)
    # The orchestrator `seo` is not a subcommand of itself; agent skills excluded.
    assert "audit" in result["subcmds"]
    assert result["subcmds"]["audit"] == "seo-audit"
    assert "page" in result["subcmds"]
    assert "schema" in result["subcmds"]
    assert "seo" not in result["subcmds"]
    # Agent-derived skills (suffix -agent) are excluded from the subcommand surface.
    assert "technical-agent" not in result["subcmds"]
    assert result["descriptions"]["audit"] == "Full website audit."
