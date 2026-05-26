"""Tests for lib/portability_check.py — frontmatter portability lint."""
from __future__ import annotations

from pathlib import Path

import pytest

from lib import portability_check as pc


def test_clean_skill_has_no_errors(tmp_install_root: Path):
    skill = tmp_install_root / "skills" / "seo-x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: seo-x\ndescription: A clean skill.\n---\nbody\n"
    )
    findings = pc.check_tree(tmp_install_root / "skills")
    errors = [f for f in findings if f["severity"] == "error"]
    assert errors == []


def test_missing_description_is_error(tmp_install_root: Path):
    skill = tmp_install_root / "skills" / "seo-x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: seo-x\n---\nbody\n")
    findings = pc.check_tree(tmp_install_root / "skills")
    assert any(f["rule"] == "missing-description" for f in findings)


def test_camelcase_name_is_error(tmp_install_root: Path):
    skill = tmp_install_root / "skills" / "seoX"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: seoX\ndescription: x\n---\nbody\n")
    findings = pc.check_tree(tmp_install_root / "skills")
    assert any(f["rule"] == "name-not-kebab-case" for f in findings)


def test_no_frontmatter_is_error(tmp_install_root: Path):
    skill = tmp_install_root / "skills" / "seo-x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# Just a body\n")
    findings = pc.check_tree(tmp_install_root / "skills")
    assert any(f["rule"] == "no-frontmatter" for f in findings)
