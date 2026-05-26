"""Shared pytest fixtures for antigravity-seo-port tests."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def tmp_install_root(tmp_path: Path) -> Path:
    """A throwaway install root that mimics ~/.gemini/antigravity/."""
    root = tmp_path / "antigravity"
    root.mkdir()
    (root / "skills").mkdir()
    (root / "workflows").mkdir()
    return root


@pytest.fixture
def tmp_gemini_config(tmp_path: Path) -> Path:
    """A throwaway global config root that mimics ~/.gemini/config/."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    return cfg


@pytest.fixture
def tmp_upstream(tmp_path: Path) -> Path:
    """Minimal upstream tree with one skill, one agent, one extension."""
    up = tmp_path / "upstream"
    (up / "skills" / "seo-audit").mkdir(parents=True)
    (up / "skills" / "seo-audit" / "SKILL.md").write_text(
        "---\nname: seo-audit\ndescription: Full site audit.\n"
        "model: sonnet\nmaxTurns: 20\ntools: Read, Bash\n---\n\n"
        "# Audit\n\nRun: python scripts/fetch_page.py <url>\n"
    )
    (up / "agents").mkdir()
    (up / "agents" / "seo-technical.md").write_text(
        "---\nname: seo-technical\ndescription: Technical SEO specialist.\n"
        "model: sonnet\nmaxTurns: 20\ntools: Read, Bash\n---\n\nYou are a Technical SEO specialist.\n"
    )
    (up / "scripts").mkdir()
    (up / "scripts" / "fetch_page.py").write_text("# stub\n")
    return up
