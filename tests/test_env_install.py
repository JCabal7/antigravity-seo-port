"""Tests for lib/env_install.py — owner-tagged .env merging."""
from __future__ import annotations

from pathlib import Path

import pytest

from lib import env_install

OWNER = "antigravity-seo"


def test_set_env_var_creates_file(tmp_path: Path):
    env = tmp_path / ".env"
    env_install.set_env_var(env, "FOO", "bar", owner=OWNER)
    assert env.read_text().splitlines() == [
        f"# >>> {OWNER}",
        'FOO="bar"',
        f"# <<< {OWNER}",
    ]


def test_set_env_var_updates_existing_in_block(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        f"# >>> {OWNER}\n"
        'FOO="old"\n'
        f"# <<< {OWNER}\n"
    )
    env_install.set_env_var(env, "FOO", "new", owner=OWNER)
    text = env.read_text()
    assert 'FOO="new"' in text
    assert 'FOO="old"' not in text


def test_set_env_var_appends_to_existing_block(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        f"# >>> {OWNER}\n"
        'FOO="x"\n'
        f"# <<< {OWNER}\n"
    )
    env_install.set_env_var(env, "BAR", "y", owner=OWNER)
    text = env.read_text()
    assert 'FOO="x"' in text
    assert 'BAR="y"' in text


def test_set_env_var_preserves_unrelated_blocks(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        '# Some other tool\n'
        'OTHER_KEY="keep_me"\n'
        f"# >>> {OWNER}\n"
        'FOO="x"\n'
        f"# <<< {OWNER}\n"
    )
    env_install.set_env_var(env, "FOO", "new", owner=OWNER)
    text = env.read_text()
    assert 'OTHER_KEY="keep_me"' in text
    assert 'FOO="new"' in text


def test_remove_owner_block_only_removes_owned(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text(
        'OTHER_KEY="keep"\n'
        f"# >>> {OWNER}\n"
        'FOO="x"\n'
        'BAR="y"\n'
        f"# <<< {OWNER}\n"
        'TRAILING="also keep"\n'
    )
    env_install.remove_owner_block(env, owner=OWNER)
    text = env.read_text()
    assert 'OTHER_KEY="keep"' in text
    assert 'TRAILING="also keep"' in text
    assert "FOO" not in text
    assert "BAR" not in text
    assert OWNER not in text


def test_remove_owner_block_no_file_no_op(tmp_path: Path):
    env = tmp_path / ".env"
    env_install.remove_owner_block(env, owner=OWNER)  # should not raise
    assert not env.exists()


def test_file_permissions_are_user_only(tmp_path: Path):
    env = tmp_path / ".env"
    env_install.set_env_var(env, "FOO", "bar", owner=OWNER)
    mode = env.stat().st_mode & 0o777
    assert mode == 0o600
