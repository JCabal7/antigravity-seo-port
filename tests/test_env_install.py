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


def test_script_only_extension_table_has_four():
    names = set(env_install.SCRIPT_ONLY_EXTENSIONS.keys())
    assert names == {"bing-webmaster", "profound", "seranking", "unlighthouse"}


def test_bing_extension_requires_at_least_one_credential():
    # Per upstream installer behavior: must provide Bing key OR IndexNow key
    spec = env_install.SCRIPT_ONLY_EXTENSIONS["bing-webmaster"]
    assert spec["env_vars"] == ["BING_WEBMASTER_API_KEY", "INDEXNOW_KEY", "INDEXNOW_KEY_LOCATION"]
    assert spec["require_any_of"] == ["BING_WEBMASTER_API_KEY", "INDEXNOW_KEY"]


def test_profound_extension_requires_api_key():
    spec = env_install.SCRIPT_ONLY_EXTENSIONS["profound"]
    assert spec["env_vars"] == ["PROFOUND_API_KEY"]


def test_unlighthouse_extension_has_no_env_vars():
    spec = env_install.SCRIPT_ONLY_EXTENSIONS["unlighthouse"]
    assert spec["env_vars"] == []


def test_install_script_extension_writes_env(tmp_path: Path):
    env = tmp_path / ".env"
    env_install.install_script_extension(
        env, "profound", credentials={"PROFOUND_API_KEY": "p-123"}
    )
    text = env.read_text()
    assert 'PROFOUND_API_KEY="p-123"' in text


def test_install_script_extension_skips_missing_optional(tmp_path: Path):
    env = tmp_path / ".env"
    env_install.install_script_extension(
        env, "bing-webmaster", credentials={"INDEXNOW_KEY": "k", "INDEXNOW_KEY_LOCATION": "https://x/k.txt"}
    )
    text = env.read_text()
    assert 'INDEXNOW_KEY="k"' in text
    assert 'INDEXNOW_KEY_LOCATION="https://x/k.txt"' in text
    # BING_WEBMASTER_API_KEY was not supplied — must not be written empty
    assert 'BING_WEBMASTER_API_KEY' not in text


def test_install_script_extension_rejects_missing_required(tmp_path: Path):
    env = tmp_path / ".env"
    with pytest.raises(ValueError, match="at least one of"):
        env_install.install_script_extension(env, "bing-webmaster", credentials={})


def test_uninstall_script_extension_removes_all_owned(tmp_path: Path):
    env = tmp_path / ".env"
    env_install.install_script_extension(env, "profound", credentials={"PROFOUND_API_KEY": "k"})
    env_install.install_script_extension(env, "bing-webmaster", credentials={"INDEXNOW_KEY": "i", "INDEXNOW_KEY_LOCATION": "u"})
    env_install.uninstall_script_extension(env)
    if env.exists():
        text = env.read_text()
        assert "PROFOUND_API_KEY" not in text
        assert "INDEXNOW_KEY" not in text
