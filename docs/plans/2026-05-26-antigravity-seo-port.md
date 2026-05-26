# antigravity-seo-port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone installer (`antigravity-seo-port/`) that takes a pinned tag of `AgriciDaniel/claude-seo` and installs all 25 skills, 18 subagents, 8 extensions, the `/seo` slash-command tree, the schema-validation hook, and all helper scripts/assets into a Google Antigravity environment with feature parity to the Claude Code version.

**Architecture:** Python conversion library (`lib/`) wrapped by a Bash installer (`install.sh`). Conversion library does mechanical transforms (frontmatter normalize, path rewrite, agent→skill, MCP/env/hook merges) and is fully unit-tested. Installer handles preflight, cloning upstream, interactive credential prompts, venv setup, and post-install verification. Uninstaller is the inverse, surgical (touches only entries this project owns).

**Tech Stack:** Python 3.10+ (stdlib only — `pathlib`, `json`, `tempfile`, `re`, `subprocess`, `argparse`), pytest for unit tests, Bash for the installer, `rsync` for atomic tree copies, `npx` for MCP server bootstrapping.

**Spec:** `docs/specs/2026-05-25-antigravity-seo-port-design.md`

---

## File Structure

```
antigravity-seo-port/
├── README.md                          # user install/uninstall instructions
├── install.sh                         # main installer (Bash)
├── uninstall.sh                       # main uninstaller (Bash)
├── pyproject.toml                     # Python package config (for tests + linting)
├── .gitignore
├── lib/
│   ├── __init__.py
│   ├── convert.py                     # skill/agent conversion: frontmatter normalize, path rewrite, agent→skill mapping
│   ├── mcp_install.py                 # idempotent ~/.gemini/config/mcp_config.json merges
│   ├── env_install.py                 # idempotent .env writes for script-only extensions
│   ├── workflow_install.py            # /seo dispatcher + per-subcommand workflow generation
│   └── portability_check.py           # frontmatter portability lint (adapted from upstream)
├── templates/
│   ├── seo-workflow.md.tmpl           # /seo dispatcher template
│   ├── seo-subcmd-workflow.md.tmpl    # per-subcommand convenience template
│   ├── hooks.json.tmpl                # Antigravity-shaped hooks.json template
│   └── dotenv_shim.py                 # 3-line dotenv-loading wrapper for script-only extensions
├── tests/
│   ├── __init__.py
│   ├── conftest.py                    # pytest fixtures (tmp upstream, tmp install root)
│   ├── test_convert.py
│   ├── test_mcp_install.py
│   ├── test_env_install.py
│   ├── test_workflow_install.py
│   ├── test_portability.py
│   ├── fixtures/                      # sample SKILL.md / agent.md / install.sh snippets
│   │   ├── sample_skill.md
│   │   ├── sample_agent.md
│   │   └── sample_mcp_config.json
│   └── test_smoke.sh                  # end-to-end install/uninstall in sandbox
└── _research/
    └── notes.md                       # field notes from probing Antigravity unknowns
```

**File responsibilities:**

- `lib/convert.py` — pure transforms on YAML/Markdown strings and file trees. No I/O outside `pathlib`. No knowledge of Antigravity install paths.
- `lib/mcp_install.py` — owns the table of 4 MCP servers and the JSON-merge logic.
- `lib/env_install.py` — owns `.env` line-oriented edits with owner-tagged comments.
- `lib/workflow_install.py` — owns workflow templates and rendering.
- `lib/portability_check.py` — adapted copy of upstream's lint, retargeted at the installed tree.
- `install.sh` — orchestrates: preflight → clone → staging → convert → rsync → workflows → MCP prompts → env prompts → hooks → venv → verify.
- `uninstall.sh` — orchestrates removal: snapshot → remove skills/workflows → un-merge MCP/env/hooks → remove venv.

---

## Conventions used throughout this plan

- `$PORT` refers to the project root (`/Users/jspringe/.claude/projects/antigravity-seo-port` for this user; can be anywhere for other engineers).
- `$UPSTREAM` refers to the cloned claude-seo source tree.
- `$INSTALL` refers to `~/.gemini/antigravity/skills/seo` (the install root for the SEO bundle).
- Every `git commit` step uses `-S` only if the engineer's git is configured to sign; otherwise plain `git commit`. Plan shows plain.
- Tests use `pytest` from the project root: `pytest tests/test_X.py::test_name -v`.

---

## Phase 0: Bootstrap

### Task 0.1: Create project skeleton

**Files:**
- Create: `$PORT/.gitignore`
- Create: `$PORT/pyproject.toml`
- Create: `$PORT/README.md` (placeholder)
- Create: `$PORT/lib/__init__.py` (empty)
- Create: `$PORT/tests/__init__.py` (empty)
- Create: `$PORT/tests/conftest.py`
- Create: `$PORT/_research/notes.md` (header only)
- Create: `$PORT/templates/.gitkeep`

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
*.egg-info/
.DS_Store
_tmp_clone/
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "antigravity-seo-port"
version = "0.1.0"
description = "Installer that ports claude-seo to Google Antigravity"
requires-python = ">=3.10"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 3: Create placeholder `README.md`**

```markdown
# antigravity-seo-port

Installer that ports [claude-seo](https://github.com/AgriciDaniel/claude-seo) v2.0.0 to Google Antigravity (CLI + desktop).

Full user docs: see end of plan execution.
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
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
```

- [ ] **Step 5: Create `_research/notes.md` header**

```markdown
# Antigravity Port Research Notes

Field notes from probing unknowns in `docs/specs/2026-05-25-antigravity-seo-port-design.md` §9.

| Unknown # | Question | Resolution | Verified by |
|---|---|---|---|
| 1 | Global workflows path | (pending Task 1.1) | |
| 2 | Hooks file path + variables | (pending Task 1.2) | |
| 3 | CLI dry-run mode | (pending Task 1.3) | |
| 4 | Workflow argument handling | (pending Task 1.4) | |
| 5 | YAML strictness | (pending Task 1.5) | |
| 6 | seranking install.sh shape | (pending Task 1.6) | |
```

- [ ] **Step 6: Create empty stubs**

```bash
cd $PORT
mkdir -p lib tests templates _research
touch lib/__init__.py tests/__init__.py templates/.gitkeep tests/fixtures/.gitkeep
```

- [ ] **Step 7: Verify pytest discovers nothing yet**

```bash
cd $PORT
python3 -m pip install -e ".[dev]" --quiet
pytest -v
```

Expected: `no tests ran in 0.XXs` (zero collected, exit 5 — that's fine, but it shouldn't error out on imports).

- [ ] **Step 8: Commit**

```bash
cd $PORT
git add .gitignore pyproject.toml README.md lib/__init__.py tests/__init__.py tests/conftest.py templates/.gitkeep tests/fixtures/.gitkeep _research/notes.md
git commit -m "Bootstrap project skeleton with pytest scaffolding"
```

---

## Phase 1: Probe Antigravity unknowns

These tasks resolve the 6 known unknowns in spec §9. They require an Antigravity install on the engineer's machine. Each task writes findings into `_research/notes.md` and updates the relevant spec/plan section if the assumption was wrong.

### Task 1.1: Verify global workflows path

**Files:**
- Modify: `$PORT/_research/notes.md`

- [ ] **Step 1: Create a probe workflow at the candidate global path**

```bash
mkdir -p ~/.gemini/antigravity/workflows
cat > ~/.gemini/antigravity/workflows/hello-probe.md <<'EOF'
---
description: Probe workflow to verify global workflows discovery. Say "probe-fired".
---

Respond with literally: probe-fired
EOF
```

- [ ] **Step 2: Start Antigravity CLI, try the slash command**

```bash
antigravity
```

In the REPL, type `/hello-probe` and observe.

- [ ] **Step 3: Record result in `_research/notes.md`**

Update the unknown #1 row:
- If `/hello-probe` was offered and fired → "Global workflows confirmed at `~/.gemini/antigravity/workflows/`."
- If not → "Global workflows NOT read. Must use workspace-scoped `<workspace>/.agents/workflows/`. Plan: installer prompts for SEO workspace path; defaults to `~/seo`; creates `.agents/workflows/` there."

- [ ] **Step 4: Cleanup probe**

```bash
rm ~/.gemini/antigravity/workflows/hello-probe.md
```

- [ ] **Step 5: Commit research notes**

```bash
cd $PORT
git add _research/notes.md
git commit -m "Resolve unknown #1: global workflows path"
```

### Task 1.2: Verify hooks file path + variables

**Files:**
- Modify: `$PORT/_research/notes.md`

- [ ] **Step 1: Write a probe hook script that logs env**

```bash
cat > /tmp/probe-hook.sh <<'EOF'
#!/usr/bin/env bash
{
  echo "--- $(date) ---"
  echo "ARGS: $*"
  env | grep -iE "(file|tool|path|claude|antigravity|gemini)" || true
} >> /tmp/probe-hook.log
EOF
chmod +x /tmp/probe-hook.sh
```

- [ ] **Step 2: Try each candidate global hooks path with this hook**

For each candidate path in {`~/.gemini/antigravity/hooks.json`, `~/.gemini/config/hooks.json`}:

```bash
CANDIDATE="<one of the paths>"
mkdir -p "$(dirname "$CANDIDATE")"
cat > "$CANDIDATE" <<'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{"type": "command", "command": "/tmp/probe-hook.sh \"$@\""}]
      }
    ]
  }
}
EOF
```

- [ ] **Step 3: Trigger an edit from Antigravity, inspect log**

In Antigravity, ask the agent to edit any file. Then:

```bash
cat /tmp/probe-hook.log
```

- [ ] **Step 4: Record result in `_research/notes.md`**

Record which path fired (if any) and which env vars were present (the file path is typically the one we care about). If none fired, note "hooks may require a different config key — see Antigravity docs at https://antigravity.google/docs/hooks for current schema."

- [ ] **Step 5: Cleanup probes**

```bash
rm /tmp/probe-hook.sh /tmp/probe-hook.log
rm -f ~/.gemini/antigravity/hooks.json ~/.gemini/config/hooks.json
```

- [ ] **Step 6: Commit research notes**

```bash
cd $PORT
git add _research/notes.md
git commit -m "Resolve unknown #2: hooks file path + variables"
```

### Task 1.3: Verify CLI dry-run mode

**Files:**
- Modify: `$PORT/_research/notes.md`

- [ ] **Step 1: Probe CLI help**

```bash
antigravity --help 2>&1 | tee /tmp/antigravity-help.txt
antigravity --version
```

Look for flags like `--dry-run`, `--non-interactive`, `--script`, `--exec`, or any way to pipe a single slash command and exit.

- [ ] **Step 2: Try the most likely candidate**

```bash
echo "/skills list" | antigravity 2>&1 | head -20
# or
antigravity exec "/skills list" 2>&1 | head -20
```

- [ ] **Step 3: Record result in `_research/notes.md`**

Document the exact invocation that works for non-interactive single-command execution. If none works, note "smoke test will skip the model-execution step; will only verify install completeness."

- [ ] **Step 4: Commit research notes**

```bash
cd $PORT
git add _research/notes.md
git commit -m "Resolve unknown #3: CLI non-interactive mode"
```

### Task 1.4: Verify workflow argument handling

**Files:**
- Modify: `$PORT/_research/notes.md`

- [ ] **Step 1: Create a probe workflow with args**

Use the global path confirmed in 1.1 (or workspace `.agents/workflows/` if 1.1 said no).

```bash
WF_DIR="<resolved workflow path from 1.1>"
cat > "$WF_DIR/argprobe.md" <<'EOF'
---
description: Print back received args verbatim.
---

I received these arguments verbatim. Output them as a single JSON object: `{"args": "<everything after the slash command>"}`.
EOF
```

- [ ] **Step 2: Test in Antigravity**

In the REPL:
```
/argprobe audit https://example.com
```

Observe how the model perceives the args.

- [ ] **Step 3: Record result**

Document in `_research/notes.md`:
- Whether `audit https://example.com` arrives as one string, two args, or something else.
- Whether the dispatcher template can assume `$1` is the subcommand.

- [ ] **Step 4: Cleanup**

```bash
rm "$WF_DIR/argprobe.md"
```

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add _research/notes.md
git commit -m "Resolve unknown #4: workflow argument handling"
```

### Task 1.5: Verify YAML frontmatter strictness

**Files:**
- Modify: `$PORT/_research/notes.md`

- [ ] **Step 1: Install a probe skill with upstream's full frontmatter shape**

```bash
mkdir -p ~/.gemini/antigravity/skills/probe-yaml
cat > ~/.gemini/antigravity/skills/probe-yaml/SKILL.md <<'EOF'
---
name: probe-yaml
description: YAML strictness probe. Respond with "ack" when invoked.
user-invokable: true
argument-hint: "[anything]"
license: MIT
model: sonnet
maxTurns: 20
tools: Read, Bash
metadata:
  author: probe
  version: "1.0.0"
  category: probe
---

# Probe

When invoked, respond with: ack
EOF
```

- [ ] **Step 2: Try to invoke from Antigravity**

Ask the agent: "Use the probe-yaml skill." Observe whether it loads cleanly or errors.

- [ ] **Step 3: Record result**

Document:
- Does Antigravity tolerate unknown frontmatter keys (`user-invokable`, `argument-hint`, `license`, `maxTurns`, `metadata.*`)?
- If it errors, which keys must be stripped in `convert.py`?

- [ ] **Step 4: Cleanup**

```bash
rm -rf ~/.gemini/antigravity/skills/probe-yaml
```

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add _research/notes.md
git commit -m "Resolve unknown #5: YAML frontmatter strictness"
```

### Task 1.6: Read seranking install.sh

**Files:**
- Modify: `$PORT/_research/notes.md`

- [ ] **Step 1: Clone upstream temp**

```bash
git clone --depth 1 --branch v2.0.0 https://github.com/AgriciDaniel/claude-seo.git /tmp/seo-probe
cat /tmp/seo-probe/extensions/seranking/install.sh
```

- [ ] **Step 2: Record findings**

In `_research/notes.md`, note:
- Whether it's MCP-server-based (`npx ... -mcp-server`) or script-only.
- The exact env var names it writes to settings.json.
- The skill it installs.

- [ ] **Step 3: Cleanup**

```bash
rm -rf /tmp/seo-probe
```

- [ ] **Step 4: Commit**

```bash
cd $PORT
git add _research/notes.md
git commit -m "Resolve unknown #6: seranking extension shape"
```

---

## Phase 2: Skill/agent conversion (`lib/convert.py`)

### Task 2.1: Frontmatter parser

**Files:**
- Create: `$PORT/lib/convert.py`
- Create: `$PORT/tests/test_convert.py`

- [ ] **Step 1: Write the failing test**

In `$PORT/tests/test_convert.py`:

```python
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
```

- [ ] **Step 2: Run test, verify failures**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 4 errors (`ModuleNotFoundError: No module named 'lib.convert'` or `AttributeError: parse_frontmatter`).

- [ ] **Step 3: Implement `parse_frontmatter`**

In `$PORT/lib/convert.py`:

```python
"""Skill/agent conversion for the Antigravity port.

Pure transforms on strings and file paths. No knowledge of install paths.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md / agent.md into (frontmatter_dict, body_str).

    Uses a small YAML subset parser (no external deps): top-level keys,
    inline values, folded (`>`) scalars, and one level of nested mapping.
    Returns ({}, raw) if no frontmatter delimiter is present.
    """
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    yaml_blob, body = m.group(1), m.group(2)
    return _parse_yaml_subset(yaml_blob), body


def _parse_yaml_subset(blob: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    lines = blob.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line.startswith(" "):
            i += 1
            continue  # handled by parent in nested case
        key, sep, rest = line.partition(":")
        if not sep:
            i += 1
            continue
        key = key.strip()
        rest = rest.strip()
        if rest == ">" or rest == "|":
            # Folded / literal scalar — collect indented continuation
            parts: list[str] = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                if lines[i].strip():
                    parts.append(lines[i].strip())
                i += 1
            sep_char = " " if rest == ">" else "\n"
            result[key] = sep_char.join(parts)
            continue
        if rest == "":
            # Nested mapping — collect indented child lines
            nested: dict[str, Any] = {}
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                if lines[i].strip():
                    cline = lines[i].lstrip()
                    ckey, csep, cval = cline.partition(":")
                    if csep:
                        nested[ckey.strip()] = _unquote(cval.strip())
                i += 1
            result[key] = nested
            continue
        result[key] = _unquote(rest)
        i += 1
    return result


def _unquote(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'"}:
        return s[1:-1]
    return s
```

- [ ] **Step 4: Run test, verify pass**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/convert.py tests/test_convert.py
git commit -m "convert: add frontmatter parser (YAML subset, stdlib only)"
```

### Task 2.2: Frontmatter normalize (strip Claude-only keys)

**Files:**
- Modify: `$PORT/lib/convert.py`
- Modify: `$PORT/tests/test_convert.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_convert.py`:

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 3 new failures (`AttributeError: normalize_frontmatter`).

- [ ] **Step 3: Implement `normalize_frontmatter`**

Append to `$PORT/lib/convert.py`:

```python
_KEEP_KEYS = {"name", "description", "model", "tools", "metadata"}


def normalize_frontmatter(fm: dict[str, Any]) -> dict[str, Any]:
    """Strip Claude-Code-only keys; keep the portable subset Antigravity reads.

    Per spec §4.3 step 1. If Task 1.5 finds Antigravity rejects `metadata`
    as a nested block, update _KEEP_KEYS and add a flattening pass here.
    """
    return {k: v for k, v in fm.items() if k in _KEEP_KEYS}
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/convert.py tests/test_convert.py
git commit -m "convert: normalize frontmatter (strip Claude-only keys)"
```

### Task 2.3: Frontmatter serializer

**Files:**
- Modify: `$PORT/lib/convert.py`
- Modify: `$PORT/tests/test_convert.py`

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 3 new failures.

- [ ] **Step 3: Implement**

Append to `lib/convert.py`:

```python
def serialize_frontmatter(fm: dict[str, Any]) -> str:
    """Emit YAML frontmatter for a normalized dict. Returns string ending with `---\\n`."""
    lines = ["---"]
    for key, val in fm.items():
        if isinstance(val, dict):
            lines.append(f"{key}:")
            for ck, cv in val.items():
                lines.append(f"  {ck}: {_yaml_value(cv)}")
        else:
            lines.append(f"{key}: {_yaml_value(val)}")
    lines.append("---\n")
    return "\n".join(lines)


def _yaml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in (":", "#", "'", '"', "\n")):
        return '"' + s.replace('"', '\\"') + '"'
    return s
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/convert.py tests/test_convert.py
git commit -m "convert: serialize frontmatter back to YAML"
```

### Task 2.4: Body path rewriter

**Files:**
- Modify: `$PORT/lib/convert.py`
- Modify: `$PORT/tests/test_convert.py`

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 3 new failures.

- [ ] **Step 3: Implement**

Append to `lib/convert.py`:

```python
_PATH_REWRITE_PATTERNS = {
    "scripts": re.compile(r"(?<![\w/])(?:\./)?scripts/([\w.\-]+\.(?:py|sh))"),
    "schema": re.compile(r"(?<![\w/])(?:\./)?schema/([\w.\-/]+\.(?:json|md))"),
    "pdf": re.compile(r"(?<![\w/])(?:\./)?pdf/([\w.\-/]+\.(?:pdf|md))"),
    "data": re.compile(r"(?<![\w/])(?:\./)?data/([\w.\-/]+\.(?:csv|json|md|txt))"),
}


def rewrite_paths(
    body: str,
    *,
    scripts_dir: str | None = None,
    schema_dir: str | None = None,
    pdf_dir: str | None = None,
    data_dir: str | None = None,
) -> str:
    """Rewrite `scripts/<file>` etc. to absolute install-path refs.

    Only rewrites paths that look like file references (have a recognized
    file extension). Bare directory mentions in prose are left untouched.
    """
    dirs = {"scripts": scripts_dir, "schema": schema_dir, "pdf": pdf_dir, "data": data_dir}
    for key, target_dir in dirs.items():
        if target_dir is None:
            continue
        body = _PATH_REWRITE_PATTERNS[key].sub(rf"{target_dir}/\1", body)
    return body
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/convert.py tests/test_convert.py
git commit -m "convert: rewrite scripts/schema/pdf/data paths to install paths"
```

### Task 2.5: Agent-to-skill conversion with collision suffix

**Files:**
- Modify: `$PORT/lib/convert.py`
- Modify: `$PORT/tests/test_convert.py`

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 3 new failures.

- [ ] **Step 3: Implement**

Append to `lib/convert.py`:

```python
def agent_target_skill_name(agent_name: str, existing_skills: set[str]) -> str:
    """Return the target skill name; suffix `-agent` only on collision."""
    if agent_name in existing_skills:
        return f"{agent_name}-agent"
    return agent_name


def convert_agent_to_skill(agent_md: str, *, new_name: str) -> str:
    """Convert an agents/seo-*.md file body into a SKILL.md body.

    Re-emit with normalized frontmatter (claude-only keys stripped) and
    the (possibly suffixed) new skill name.
    """
    fm, body = parse_frontmatter(agent_md)
    fm["name"] = new_name
    fm = normalize_frontmatter(fm)
    return serialize_frontmatter(fm) + "\n" + body.lstrip("\n")
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/convert.py tests/test_convert.py
git commit -m "convert: agent-to-skill with collision suffixing"
```

### Task 2.6: Convert a whole skill file (frontmatter + body together)

**Files:**
- Modify: `$PORT/lib/convert.py`
- Modify: `$PORT/tests/test_convert.py`

- [ ] **Step 1: Append failing test**

```python
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
```

- [ ] **Step 2: Run, verify failure**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 1 new failure.

- [ ] **Step 3: Implement**

Append to `lib/convert.py`:

```python
def convert_skill(
    raw: str,
    *,
    scripts_dir: str | None = None,
    schema_dir: str | None = None,
    pdf_dir: str | None = None,
    data_dir: str | None = None,
) -> str:
    """End-to-end conversion: normalize frontmatter, rewrite body paths, re-serialize."""
    fm, body = parse_frontmatter(raw)
    fm = normalize_frontmatter(fm)
    body = rewrite_paths(
        body,
        scripts_dir=scripts_dir,
        schema_dir=schema_dir,
        pdf_dir=pdf_dir,
        data_dir=data_dir,
    )
    return serialize_frontmatter(fm) + "\n" + body.lstrip("\n")
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/convert.py tests/test_convert.py
git commit -m "convert: end-to-end convert_skill (normalize + rewrite)"
```

### Task 2.7: Convert a whole tree

**Files:**
- Modify: `$PORT/lib/convert.py`
- Modify: `$PORT/tests/test_convert.py`

- [ ] **Step 1: Append failing test (uses the `tmp_upstream` fixture)**

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 2 new failures.

- [ ] **Step 3: Implement**

Append to `lib/convert.py`:

```python
def convert_tree(
    *,
    src: Path,
    dst: Path,
    scripts_dir: str | None = None,
    schema_dir: str | None = None,
    pdf_dir: str | None = None,
    data_dir: str | None = None,
) -> dict[str, list[str]]:
    """Walk `src` (upstream claude-seo clone) and write Antigravity-shaped tree to `dst`.

    Returns a summary dict: {"skills": [names], "agents_mapped": [names]}.
    """
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "skills").mkdir(exist_ok=True)

    skill_names: set[str] = set()
    summary: dict[str, list[str]] = {"skills": [], "agents_mapped": []}

    # 1. Convert each skill.
    src_skills = src / "skills"
    if src_skills.is_dir():
        for skill_dir in sorted(src_skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            name = skill_dir.name
            skill_names.add(name)
            out_skill_dir = dst / "skills" / name
            out_skill_dir.mkdir(parents=True, exist_ok=True)
            for entry in skill_dir.iterdir():
                if entry.name == "SKILL.md":
                    converted = convert_skill(
                        entry.read_text(),
                        scripts_dir=scripts_dir,
                        schema_dir=schema_dir,
                        pdf_dir=pdf_dir,
                        data_dir=data_dir,
                    )
                    (out_skill_dir / "SKILL.md").write_text(converted)
                elif entry.is_dir():
                    _copy_tree(entry, out_skill_dir / entry.name)
                else:
                    (out_skill_dir / entry.name).write_bytes(entry.read_bytes())
            summary["skills"].append(name)

    # 2. Convert each agent into a skill (with collision suffixing).
    src_agents = src / "agents"
    if src_agents.is_dir():
        for agent_file in sorted(src_agents.glob("*.md")):
            agent_name = agent_file.stem
            target_name = agent_target_skill_name(agent_name, skill_names)
            out_skill_dir = dst / "skills" / target_name
            out_skill_dir.mkdir(parents=True, exist_ok=True)
            converted = convert_agent_to_skill(agent_file.read_text(), new_name=target_name)
            (out_skill_dir / "SKILL.md").write_text(converted)
            summary["agents_mapped"].append(target_name)
            skill_names.add(target_name)

    return summary


def _copy_tree(src: Path, dst: Path) -> None:
    """Recursive copy that preserves file contents byte-for-byte. No symlink magic."""
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        if entry.is_dir():
            _copy_tree(entry, dst / entry.name)
        else:
            (dst / entry.name).write_bytes(entry.read_bytes())
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_convert.py -v
```

Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/convert.py tests/test_convert.py
git commit -m "convert: convert_tree walks upstream and writes Antigravity tree"
```

---

## Phase 3: MCP server install (`lib/mcp_install.py`)

### Task 3.1: Atomic JSON write helper

**Files:**
- Create: `$PORT/lib/mcp_install.py`
- Create: `$PORT/tests/test_mcp_install.py`

- [ ] **Step 1: Write failing tests**

In `$PORT/tests/test_mcp_install.py`:

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 3 failures (ModuleNotFoundError).

- [ ] **Step 3: Implement**

In `$PORT/lib/mcp_install.py`:

```python
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
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/mcp_install.py tests/test_mcp_install.py
git commit -m "mcp_install: atomic JSON write helper"
```

### Task 3.2: MCP server table

**Files:**
- Modify: `$PORT/lib/mcp_install.py`
- Modify: `$PORT/tests/test_mcp_install.py`

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 5 failures.

- [ ] **Step 3: Implement**

Append to `lib/mcp_install.py`:

```python
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
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/mcp_install.py tests/test_mcp_install.py
git commit -m "mcp_install: table of 4 MCP servers (firecrawl, dataforseo, banana, ahrefs)"
```

### Task 3.3: Idempotent merge into mcp_config.json

**Files:**
- Modify: `$PORT/lib/mcp_install.py`
- Modify: `$PORT/tests/test_mcp_install.py`

- [ ] **Step 1: Append failing tests**

```python
def test_install_mcp_server_writes_new_file(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    mcp_install.install_mcp_server(
        cfg, "firecrawl", credentials={"FIRECRAWL_API_KEY": "fc-abc"}
    )
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["firecrawl-mcp"]["command"] == "npx"
    assert data["mcpServers"]["firecrawl-mcp"]["env"]["FIRECRAWL_API_KEY"] == "fc-abc"


def test_install_mcp_server_preserves_unrelated_entries(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    cfg.write_text(json.dumps({
        "mcpServers": {"other-server": {"command": "node", "args": ["x.js"]}}
    }))
    mcp_install.install_mcp_server(
        cfg, "firecrawl", credentials={"FIRECRAWL_API_KEY": "k"}
    )
    data = json.loads(cfg.read_text())
    assert "other-server" in data["mcpServers"]
    assert "firecrawl-mcp" in data["mcpServers"]


def test_install_mcp_server_overwrites_same_name(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    mcp_install.install_mcp_server(cfg, "firecrawl", credentials={"FIRECRAWL_API_KEY": "old"})
    mcp_install.install_mcp_server(cfg, "firecrawl", credentials={"FIRECRAWL_API_KEY": "new"})
    data = json.loads(cfg.read_text())
    assert data["mcpServers"]["firecrawl-mcp"]["env"]["FIRECRAWL_API_KEY"] == "new"


def test_install_mcp_server_dataforseo_includes_env_defaults(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    mcp_install.install_mcp_server(
        cfg,
        "dataforseo",
        credentials={"DATAFORSEO_USERNAME": "u", "DATAFORSEO_PASSWORD": "p"},
        extra_env={"FIELD_CONFIG_PATH": "/install/extensions/dataforseo/field-config.json"},
    )
    env = json.loads(cfg.read_text())["mcpServers"]["dataforseo"]["env"]
    assert env["DATAFORSEO_USERNAME"] == "u"
    assert env["DATAFORSEO_PASSWORD"] == "p"
    assert env["ENABLED_MODULES"].startswith("SERP")
    assert env["FIELD_CONFIG_PATH"] == "/install/extensions/dataforseo/field-config.json"


def test_install_mcp_server_rejects_unknown_extension(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    with pytest.raises(KeyError):
        mcp_install.install_mcp_server(cfg, "bogus", credentials={})


def test_install_mcp_server_rejects_missing_required_env(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    with pytest.raises(ValueError, match="missing required env var"):
        mcp_install.install_mcp_server(cfg, "firecrawl", credentials={})
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 6 failures.

- [ ] **Step 3: Implement**

Append to `lib/mcp_install.py`:

```python
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
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/mcp_install.py tests/test_mcp_install.py
git commit -m "mcp_install: idempotent merge into mcp_config.json"
```

### Task 3.4: Removal (for uninstall)

**Files:**
- Modify: `$PORT/lib/mcp_install.py`
- Modify: `$PORT/tests/test_mcp_install.py`

- [ ] **Step 1: Append failing tests**

```python
def test_remove_mcp_server_removes_only_owned(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    cfg.write_text(json.dumps({
        "mcpServers": {
            "firecrawl-mcp": {"command": "npx"},
            "other-server": {"command": "node"},
        }
    }))
    mcp_install.remove_mcp_server(cfg, "firecrawl")
    data = json.loads(cfg.read_text())
    assert "firecrawl-mcp" not in data["mcpServers"]
    assert "other-server" in data["mcpServers"]


def test_remove_mcp_server_no_op_when_absent(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    cfg.write_text(json.dumps({"mcpServers": {"x": {}}}))
    mcp_install.remove_mcp_server(cfg, "firecrawl")  # should not raise
    data = json.loads(cfg.read_text())
    assert "x" in data["mcpServers"]


def test_remove_mcp_server_no_file_no_op(tmp_path: Path):
    cfg = tmp_path / "mcp_config.json"
    mcp_install.remove_mcp_server(cfg, "firecrawl")  # should not raise
    assert not cfg.exists()
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 3 failures.

- [ ] **Step 3: Implement**

Append to `lib/mcp_install.py`:

```python
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
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_mcp_install.py -v
```

Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/mcp_install.py tests/test_mcp_install.py
git commit -m "mcp_install: surgical removal for uninstall"
```

---

## Phase 4: .env install for script-only extensions (`lib/env_install.py`)

### Task 4.1: Owner-tagged .env merging

**Files:**
- Create: `$PORT/lib/env_install.py`
- Create: `$PORT/tests/test_env_install.py`

- [ ] **Step 1: Write failing tests**

In `$PORT/tests/test_env_install.py`:

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_env_install.py -v
```

Expected: 7 failures.

- [ ] **Step 3: Implement**

In `$PORT/lib/env_install.py`:

```python
"""Owner-tagged .env file merges for script-only extensions.

Lines we own are bracketed with sentinel comments:

    # >>> antigravity-seo
    KEY="value"
    # <<< antigravity-seo

Other lines (set by user or other tools) are preserved.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


def set_env_var(path: Path, key: str, value: str, *, owner: str) -> None:
    """Set or update KEY="value" inside the owner-tagged block. Creates file if missing.

    File is always written with mode 0o600 (user-read-write only).
    """
    begin = f"# >>> {owner}"
    end = f"# <<< {owner}"
    line = f'{key}="{_escape(value)}"'

    lines = path.read_text().splitlines() if path.exists() else []
    in_block = False
    block_lines: list[str] = []
    other_lines: list[str] = []
    saw_block = False
    found_key = False

    for ln in lines:
        if ln == begin:
            in_block = True
            saw_block = True
            continue
        if ln == end:
            in_block = False
            continue
        if in_block:
            # Replace existing key, or pass through.
            if ln.startswith(f"{key}="):
                block_lines.append(line)
                found_key = True
            else:
                block_lines.append(ln)
        else:
            other_lines.append(ln)

    if saw_block:
        if not found_key:
            block_lines.append(line)
    else:
        block_lines = [line]

    out_lines = other_lines[:]
    if other_lines and out_lines[-1] != "":
        out_lines.append("")
    out_lines.append(begin)
    out_lines.extend(block_lines)
    out_lines.append(end)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out_lines) + "\n")
    os.chmod(path, 0o600)


def remove_owner_block(path: Path, *, owner: str) -> None:
    """Strip the owner-tagged block from the file. Leaves other content intact."""
    if not path.exists():
        return
    begin = f"# >>> {owner}"
    end = f"# <<< {owner}"
    out: list[str] = []
    skipping = False
    for ln in path.read_text().splitlines():
        if ln == begin:
            skipping = True
            continue
        if ln == end:
            skipping = False
            continue
        if skipping:
            continue
        out.append(ln)
    # Trim trailing blank lines we may have introduced
    while out and out[-1] == "":
        out.pop()
    path.write_text("\n".join(out) + ("\n" if out else ""))
    os.chmod(path, 0o600)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_env_install.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/env_install.py tests/test_env_install.py
git commit -m "env_install: owner-tagged .env merging with 0600 mode"
```

### Task 4.2: Script-only extension table + install/remove wrappers

**Files:**
- Modify: `$PORT/lib/env_install.py`
- Modify: `$PORT/tests/test_env_install.py`

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_env_install.py -v
```

Expected: 8 new failures.

- [ ] **Step 3: Implement**

Append to `lib/env_install.py`:

```python
OWNER_TAG = "antigravity-seo"

SCRIPT_ONLY_EXTENSIONS: dict[str, dict[str, Any]] = {
    "bing-webmaster": {
        "skill_name": "seo-bing",
        "env_vars": ["BING_WEBMASTER_API_KEY", "INDEXNOW_KEY", "INDEXNOW_KEY_LOCATION"],
        "require_any_of": ["BING_WEBMASTER_API_KEY", "INDEXNOW_KEY"],
    },
    "profound": {
        "skill_name": "seo-profound",
        "env_vars": ["PROFOUND_API_KEY"],
        "require_any_of": ["PROFOUND_API_KEY"],
    },
    "seranking": {
        # Updated to match Task 1.6 findings if upstream uses a different key name.
        "skill_name": "seo-seranking",
        "env_vars": ["SERANKING_API_KEY"],
        "require_any_of": ["SERANKING_API_KEY"],
    },
    "unlighthouse": {
        "skill_name": "seo-unlighthouse",
        "env_vars": [],
        "require_any_of": [],
    },
}


def install_script_extension(
    env_path: Path,
    ext_name: str,
    *,
    credentials: dict[str, str],
) -> None:
    spec = SCRIPT_ONLY_EXTENSIONS[ext_name]
    if spec["require_any_of"] and not any(credentials.get(k) for k in spec["require_any_of"]):
        raise ValueError(
            f"{ext_name} requires at least one of: {', '.join(spec['require_any_of'])}"
        )
    for var in spec["env_vars"]:
        if credentials.get(var):
            set_env_var(env_path, var, credentials[var], owner=OWNER_TAG)


def uninstall_script_extension(env_path: Path) -> None:
    """Remove all owner-tagged keys from .env. (Coarse — removes everything we ever wrote.)"""
    remove_owner_block(env_path, owner=OWNER_TAG)
```

Also add `Any` to the imports at the top:

```python
from typing import Any
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_env_install.py -v
```

Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/env_install.py tests/test_env_install.py
git commit -m "env_install: script-only extension table + install/uninstall wrappers"
```

---

## Phase 5: Workflow generation (`lib/workflow_install.py` + templates)

### Task 5.1: Dispatcher workflow template

**Files:**
- Create: `$PORT/templates/seo-workflow.md.tmpl`
- Create: `$PORT/templates/seo-subcmd-workflow.md.tmpl`
- Create: `$PORT/lib/workflow_install.py`
- Create: `$PORT/tests/test_workflow_install.py`

- [ ] **Step 1: Create dispatcher template**

`$PORT/templates/seo-workflow.md.tmpl`:

```markdown
---
description: SEO toolkit. Usage `/seo <subcommand> [args]`. Subcommands: {SUBCOMMAND_LIST}.
---

# /seo dispatcher

Parse the user's arguments as `<subcommand> [args...]`.

Dispatch table (match the first token after `/seo` to the named Antigravity skill, then load that skill and follow its instructions, passing the remaining args as the skill's input):

{DISPATCH_TABLE}

If no match: list the available subcommands and an example for each.
```

- [ ] **Step 2: Create per-subcommand convenience template**

`$PORT/templates/seo-subcmd-workflow.md.tmpl`:

```markdown
---
description: {SUBCMD_DESCRIPTION}
---

# /seo-{SUBCMD}

This is a convenience shortcut equivalent to `/seo {SUBCMD} <args>`.

Load and follow the Antigravity skill `{SKILL_NAME}`, passing the user's arguments as input.
```

- [ ] **Step 3: Write failing tests**

In `$PORT/tests/test_workflow_install.py`:

```python
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
```

- [ ] **Step 4: Run, verify failures**

```bash
cd $PORT
pytest tests/test_workflow_install.py -v
```

Expected: 5 failures.

- [ ] **Step 5: Implement**

In `$PORT/lib/workflow_install.py`:

```python
"""Workflow file generation for the /seo command tree."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = REPO_ROOT / "templates"

DISPATCHER_TEMPLATE = TEMPLATES / "seo-workflow.md.tmpl"
SUBCMD_TEMPLATE = TEMPLATES / "seo-subcmd-workflow.md.tmpl"


def render_dispatcher(subcmd_to_skill: dict[str, str]) -> str:
    """Render the /seo dispatcher from `subcmd → skill name` mapping."""
    subcmd_list = ", ".join(sorted(subcmd_to_skill.keys()))
    dispatch_lines = [
        f"- `{cmd}` → load skill `{skill}`"
        for cmd, skill in sorted(subcmd_to_skill.items())
    ]
    template = DISPATCHER_TEMPLATE.read_text()
    return (
        template
        .replace("{SUBCOMMAND_LIST}", subcmd_list)
        .replace("{DISPATCH_TABLE}", "\n".join(dispatch_lines))
    )


def render_subcmd_workflow(subcmd: str, skill_name: str, description: str) -> str:
    """Render a per-subcommand convenience workflow."""
    template = SUBCMD_TEMPLATE.read_text()
    short_desc = f"Shortcut for `/seo {subcmd}`. {description}"
    return (
        template
        .replace("{SUBCMD_DESCRIPTION}", short_desc.replace('"', "'"))
        .replace("{SUBCMD}", subcmd)
        .replace("{SKILL_NAME}", skill_name)
    )


def install_workflows(
    workflows_dir: Path,
    subcmd_to_skill: dict[str, str],
    descriptions: dict[str, str],
) -> None:
    """Write seo.md + seo-<subcmd>.md files into `workflows_dir`."""
    workflows_dir.mkdir(parents=True, exist_ok=True)
    (workflows_dir / "seo.md").write_text(render_dispatcher(subcmd_to_skill))
    for subcmd, skill in subcmd_to_skill.items():
        desc = descriptions.get(subcmd, f"Invoke the {skill} skill.")
        (workflows_dir / f"seo-{subcmd}.md").write_text(
            render_subcmd_workflow(subcmd, skill, desc)
        )


def uninstall_workflows(workflows_dir: Path) -> None:
    """Remove seo.md and seo-*.md (only the files this installer owns)."""
    if not workflows_dir.exists():
        return
    for f in workflows_dir.glob("seo.md"):
        f.unlink()
    for f in workflows_dir.glob("seo-*.md"):
        f.unlink()
```

- [ ] **Step 6: Run, verify pass**

```bash
cd $PORT
pytest tests/test_workflow_install.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
cd $PORT
git add templates/seo-workflow.md.tmpl templates/seo-subcmd-workflow.md.tmpl lib/workflow_install.py tests/test_workflow_install.py
git commit -m "workflow_install: dispatcher + per-subcommand templates"
```

### Task 5.2: Subcommand-to-skill discovery from installed tree

**Files:**
- Modify: `$PORT/lib/workflow_install.py`
- Modify: `$PORT/tests/test_workflow_install.py`

- [ ] **Step 1: Append failing tests**

```python
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
```

- [ ] **Step 2: Run, verify failure**

```bash
cd $PORT
pytest tests/test_workflow_install.py -v
```

Expected: 1 new failure.

- [ ] **Step 3: Implement**

Append to `lib/workflow_install.py`:

```python
import re
from typing import Any

_SKILL_NAME_FROM_FM = re.compile(r"^name:\s*(\S+)", re.MULTILINE)
_DESC_FROM_FM = re.compile(r"^description:\s*(.+)", re.MULTILINE)


def discover_subcommands(skills_dir: Path) -> dict[str, Any]:
    """Scan installed skills/ for `seo-*` skills; return subcommand → skill map.

    Excludes the orchestrator `seo` and agent-derived skills (suffix `-agent`).
    """
    subcmds: dict[str, str] = {}
    descriptions: dict[str, str] = {}
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name
        if name == "seo":
            continue
        if name.endswith("-agent"):
            continue
        if not name.startswith("seo-"):
            continue
        subcmd = name[len("seo-"):]
        subcmds[subcmd] = name
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            text = skill_md.read_text()
            m = _DESC_FROM_FM.search(text)
            if m:
                descriptions[subcmd] = m.group(1).strip().strip('"\'')
    return {"subcmds": subcmds, "descriptions": descriptions}
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_workflow_install.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/workflow_install.py tests/test_workflow_install.py
git commit -m "workflow_install: discover subcommands from installed skills tree"
```

---

## Phase 6: Portability lint (`lib/portability_check.py`)

### Task 6.1: Vendor upstream's lint, retarget at install path

**Files:**
- Create: `$PORT/lib/portability_check.py`
- Create: `$PORT/tests/test_portability.py`

- [ ] **Step 1: Write failing tests**

In `$PORT/tests/test_portability.py`:

```python
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
```

- [ ] **Step 2: Run, verify failures**

```bash
cd $PORT
pytest tests/test_portability.py -v
```

Expected: 4 failures.

- [ ] **Step 3: Implement**

In `$PORT/lib/portability_check.py`:

```python
"""Frontmatter portability lint for installed SKILL.md files.

Adapted from upstream claude-seo's scripts/portability_check.py. Retargeted
to scan an arbitrary installed-skills directory instead of the upstream repo.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}[a-z0-9]$")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def check_tree(skills_dir: Path) -> list[dict[str, Any]]:
    """Walk every SKILL.md under `skills_dir`; return list of finding dicts.

    Finding dict: {"path": str, "severity": "error"|"warning"|"info", "rule": str, "message": str}
    """
    findings: list[dict[str, Any]] = []
    for skill_md in skills_dir.rglob("SKILL.md"):
        findings.extend(check_one(skill_md))
    return findings


def check_one(path: Path) -> list[dict[str, Any]]:
    text = path.read_text()
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return [_finding(path, "error", "no-frontmatter", "missing --- frontmatter block")]

    fm = _parse_simple(m.group(1))
    out: list[dict[str, Any]] = []
    name = fm.get("name")
    if not name:
        out.append(_finding(path, "error", "missing-name", "name: is required"))
    elif not _NAME_RE.match(name):
        out.append(_finding(path, "error", "name-not-kebab-case",
                            f"name={name!r} must be lowercase-kebab-case"))
    desc = fm.get("description")
    if not desc:
        out.append(_finding(path, "error", "missing-description", "description: is required"))
    elif len(desc) > 1024:
        out.append(_finding(path, "info", "long-description",
                            f"description is {len(desc)} chars (>1024)"))
    return out


def _parse_simple(blob: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in blob.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or line.startswith(" "):
            continue
        key, sep, val = line.partition(":")
        if sep:
            v = val.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
                v = v[1:-1]
            result[key.strip()] = v
    return result


def _finding(path: Path, severity: str, rule: str, message: str) -> dict[str, Any]:
    return {"path": str(path), "severity": severity, "rule": rule, "message": message}
```

- [ ] **Step 4: Run, verify pass**

```bash
cd $PORT
pytest tests/test_portability.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd $PORT
git add lib/portability_check.py tests/test_portability.py
git commit -m "portability_check: frontmatter lint for installed SKILL.md files"
```

---

## Phase 7: Hooks template + dotenv shim

### Task 7.1: Hooks template

**Files:**
- Create: `$PORT/templates/hooks.json.tmpl`

- [ ] **Step 1: Create template**

`$PORT/templates/hooks.json.tmpl`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "{INSTALL_PATH}/.venv/bin/python {INSTALL_PATH}/hooks/validate-schema.py \"{FILE_PATH_VAR}\""
          }
        ]
      }
    ]
  }
}
```

`{INSTALL_PATH}` is substituted at install time with the absolute path to `~/.gemini/antigravity/skills/seo`. `{FILE_PATH_VAR}` is substituted with whatever variable name Task 1.2 resolved (e.g., `$FILE_PATH`, `$1`, or Antigravity's documented equivalent).

- [ ] **Step 2: Commit**

```bash
cd $PORT
git add templates/hooks.json.tmpl
git commit -m "templates: Antigravity-shaped hooks.json template"
```

### Task 7.2: Dotenv shim

**Files:**
- Create: `$PORT/templates/dotenv_shim.py`

- [ ] **Step 1: Create shim**

`$PORT/templates/dotenv_shim.py`:

```python
"""Tiny dotenv loader that script-only extension scripts source on import.

Usage in any wrapped script:

    import dotenv_shim  # noqa: F401 — loads ~/.gemini/antigravity/skills/seo/.env into os.environ

No dependencies. Silently no-ops if the .env file doesn't exist.
"""
from __future__ import annotations

import os
from pathlib import Path

_ENV_PATH = Path.home() / ".gemini" / "antigravity" / "skills" / "seo" / ".env"


def _load() -> None:
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        key, sep, val = s.partition("=")
        if not sep:
            continue
        v = val.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
            v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        os.environ.setdefault(key.strip(), v)


_load()
```

- [ ] **Step 2: Commit**

```bash
cd $PORT
git add templates/dotenv_shim.py
git commit -m "templates: dotenv shim for script-only extensions"
```

---

## Phase 8: Installer (`install.sh`)

The installer is a single Bash script that orchestrates the Python modules and shell prereqs.

### Task 8.1: Preflight + arg parsing skeleton

**Files:**
- Create: `$PORT/install.sh`

- [ ] **Step 1: Create skeleton**

`$PORT/install.sh`:

```bash
#!/usr/bin/env bash
# antigravity-seo-port installer.
#
# Reads a pinned tag of AgriciDaniel/claude-seo and installs it into
# the user's Google Antigravity environment (~/.gemini/antigravity/).
#
# Usage:
#   bash install.sh                          # interactive
#   bash install.sh --noninteractive         # base install only, skip extensions
#   bash install.sh --with-extensions a,b    # base + named extensions, no prompts
#   bash install.sh --upstream-tag v2.0.0    # pin a specific upstream tag
set -euo pipefail

PORT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
UPSTREAM_REPO="https://github.com/AgriciDaniel/claude-seo"
UPSTREAM_TAG_DEFAULT="v2.0.0"
INSTALL_ROOT="${HOME}/.gemini/antigravity"
SEO_INSTALL="${INSTALL_ROOT}/skills/seo"
MCP_CONFIG="${HOME}/.gemini/config/mcp_config.json"
ENV_FILE="${SEO_INSTALL}/.env"

# Defaults — overridden by flags
NONINTERACTIVE=0
WITH_EXTENSIONS=""
UPSTREAM_TAG="${UPSTREAM_TAG_DEFAULT}"

usage() {
  cat <<EOF
Usage: bash install.sh [options]

Options:
  --noninteractive            Skip all interactive prompts (base install only)
  --with-extensions LIST      Comma-separated extensions to install
                              (firecrawl,dataforseo,banana,ahrefs,
                               bing-webmaster,profound,seranking,unlighthouse)
  --upstream-tag TAG          Upstream claude-seo tag to install (default: ${UPSTREAM_TAG_DEFAULT})
  -h, --help                  Show this help
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --noninteractive) NONINTERACTIVE=1 ;;
    --with-extensions) WITH_EXTENSIONS="$2"; shift ;;
    --upstream-tag) UPSTREAM_TAG="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
  shift
done

log() { printf "  %s\n" "$*"; }
ok()  { printf "✓ %s\n" "$*"; }
warn(){ printf "! %s\n" "$*" >&2; }
die() { printf "✗ %s\n" "$*" >&2; exit 1; }

preflight() {
  printf "════════════════════════════════════════\n"
  printf "║   antigravity-seo-port — Installer    ║\n"
  printf "════════════════════════════════════════\n\n"

  command -v python3 >/dev/null 2>&1 || die "python3 not found"
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
    || die "python 3.10+ required"
  ok "python3 $(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"

  command -v git  >/dev/null 2>&1 || die "git not found"
  command -v npx  >/dev/null 2>&1 || die "npx not found (install Node 20+)"
  command -v rsync >/dev/null 2>&1 || die "rsync not found"
  command -v antigravity >/dev/null 2>&1 \
    || die "antigravity CLI not found. Install from https://antigravity.google then re-run."
  ok "prereqs satisfied"

  [ -d "${HOME}/.gemini" ] || die "~/.gemini not initialized — run \`antigravity\` once to set it up, then re-run the installer"

  mkdir -p "${INSTALL_ROOT}/skills" "${INSTALL_ROOT}/workflows"
  ok "install root ready: ${INSTALL_ROOT}"
}

preflight
echo "(install steps follow in subsequent tasks)"
```

- [ ] **Step 2: Make executable + smoke-run preflight**

```bash
cd $PORT
chmod +x install.sh
./install.sh -h
./install.sh
```

Expected: `-h` prints usage and exits. Bare invocation prints prereq checks and reaches "install steps follow in subsequent tasks".

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: preflight + arg parsing skeleton"
```

### Task 8.2: Clone upstream + staging

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append clone + staging step**

Append in `install.sh`, replacing the placeholder line `echo "(install steps follow in subsequent tasks)"`:

```bash
clone_upstream() {
  TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/antigravity-seo-port.XXXX")"
  trap 'rm -rf "${TMP_DIR}"' EXIT
  log "cloning ${UPSTREAM_REPO} @ ${UPSTREAM_TAG} ..."
  git clone --depth 1 --branch "${UPSTREAM_TAG}" "${UPSTREAM_REPO}" "${TMP_DIR}/upstream" >/dev/null 2>&1 \
    || die "clone failed (tag ${UPSTREAM_TAG} not found?)"
  ok "upstream cloned"
}

run_conversion() {
  log "converting upstream tree to Antigravity shape ..."
  python3 - <<PY
import sys
sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import convert

summary = convert.convert_tree(
    src=Path("${TMP_DIR}/upstream"),
    dst=Path("${TMP_DIR}/staging"),
    scripts_dir="${SEO_INSTALL}/scripts",
    schema_dir="${SEO_INSTALL}/schema",
    pdf_dir="${SEO_INSTALL}/pdf",
    data_dir="${SEO_INSTALL}/data",
)
print(f"  converted: {len(summary['skills'])} skills, {len(summary['agents_mapped'])} agents→skills")
PY
  ok "conversion complete"
}

clone_upstream
run_conversion
echo "(rsync + workflows + extensions follow)"
```

- [ ] **Step 2: Smoke test**

```bash
cd $PORT
./install.sh --upstream-tag v2.0.0
```

Expected: clone succeeds, conversion runs without traceback, prints skill + agent count.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: clone upstream + run convert.convert_tree to staging"
```

### Task 8.3: Rsync staging into install paths

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append step**

Replace `echo "(rsync + workflows + extensions follow)"` with:

```bash
rsync_install() {
  log "installing skills + assets ..."
  rsync -a --delete "${TMP_DIR}/staging/skills/" "${INSTALL_ROOT}/skills/"
  ok "rsynced ${INSTALL_ROOT}/skills/"

  # Copy shared assets (scripts/schema/pdf/data) into the orchestrator skill's dir
  for sub in scripts schema pdf data; do
    if [ -d "${TMP_DIR}/upstream/${sub}" ]; then
      mkdir -p "${SEO_INSTALL}/${sub}"
      rsync -a "${TMP_DIR}/upstream/${sub}/" "${SEO_INSTALL}/${sub}/"
      ok "rsynced ${SEO_INSTALL}/${sub}/"
    fi
  done

  # Merge extension scripts into shared scripts dir
  if [ -d "${TMP_DIR}/upstream/extensions" ]; then
    for ext_dir in "${TMP_DIR}/upstream/extensions/"*/; do
      if [ -d "${ext_dir}scripts" ]; then
        rsync -a "${ext_dir}scripts/" "${SEO_INSTALL}/scripts/"
      fi
    done
    ok "merged extension scripts into ${SEO_INSTALL}/scripts/"
  fi

  # AGENTS.md context file
  if [ -f "${TMP_DIR}/upstream/AGENTS.md" ]; then
    cp "${TMP_DIR}/upstream/AGENTS.md" "${INSTALL_ROOT}/AGENTS.md"
    ok "installed AGENTS.md"
  fi
}

rsync_install
echo "(workflows + extensions follow)"
```

- [ ] **Step 2: Smoke test**

```bash
cd $PORT
./install.sh
ls ~/.gemini/antigravity/skills | head -10
ls ~/.gemini/antigravity/skills/seo
```

Expected: `skills/` contains seo-* directories; `skills/seo/` contains `scripts`, `schema`, `pdf`, `data`.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: rsync skills + shared assets into Antigravity install root"
```

### Task 8.4: Generate + install workflows

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append step**

Replace `echo "(workflows + extensions follow)"` with:

```bash
install_workflows() {
  log "generating /seo dispatcher + per-subcommand workflows ..."
  # Workflow location depends on §9 unknown #1 resolution.
  # Default global; fallback to workspace if research/notes.md flagged it.
  local WF_DIR="${INSTALL_ROOT}/workflows"
  python3 - <<PY
import sys
sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import workflow_install as w

skills_dir = Path("${INSTALL_ROOT}/skills")
disc = w.discover_subcommands(skills_dir)
w.install_workflows(Path("${WF_DIR}"), disc["subcmds"], disc["descriptions"])
print(f"  installed {len(disc['subcmds'])} subcommand workflows + 1 dispatcher")
PY
  ok "workflows installed at ${WF_DIR}"
}

install_workflows
echo "(extensions + hooks + venv follow)"
```

- [ ] **Step 2: Smoke test**

```bash
cd $PORT
./install.sh
ls ~/.gemini/antigravity/workflows | head -10
cat ~/.gemini/antigravity/workflows/seo.md
```

Expected: `seo.md` + many `seo-*.md` files; dispatcher contains subcommand list.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: generate /seo dispatcher + per-subcommand workflows"
```

### Task 8.5: Prompt + install MCP-server extensions

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append step**

Replace `echo "(extensions + hooks + venv follow)"` with:

```bash
should_install_extension() {
  local ext="$1"
  if [ -n "${WITH_EXTENSIONS}" ]; then
    case ",${WITH_EXTENSIONS}," in *",${ext},"*) return 0 ;; esac
    return 1
  fi
  if [ "${NONINTERACTIVE}" -eq 1 ]; then
    return 1
  fi
  read -rp "Install ${ext}? [y/N] " ans
  [ "${ans}" = "y" ] || [ "${ans}" = "Y" ]
}

EXTENSION_FAILURES=()

try_install_extension() {
  # Run a heredoc-style python install for one extension, logging failure but not aborting.
  local name="$1"; shift
  if "$@"; then
    ok "${name} installed"
  else
    warn "${name} install failed — skipping (other extensions will continue)"
    EXTENSION_FAILURES+=("${name}")
  fi
}

install_mcp_extensions() {
  log "MCP-server extensions ..."

  if should_install_extension firecrawl; then
    read -rsp "  Firecrawl API key: " FIRECRAWL_API_KEY; echo
    if [ -z "${FIRECRAWL_API_KEY}" ]; then
      warn "firecrawl: empty API key — skipping"
      EXTENSION_FAILURES+=("firecrawl (empty key)")
    else
      try_install_extension firecrawl python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "firecrawl",
    credentials={"FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}"})
PY
    fi
  fi

  if should_install_extension dataforseo; then
    read -rp "  DataForSEO username: " DATAFORSEO_USERNAME
    read -rsp "  DataForSEO password: " DATAFORSEO_PASSWORD; echo
    if [ -z "${DATAFORSEO_USERNAME}" ] || [ -z "${DATAFORSEO_PASSWORD}" ]; then
      warn "dataforseo: empty credentials — skipping"
      EXTENSION_FAILURES+=("dataforseo (empty credentials)")
    else
      mkdir -p "${SEO_INSTALL}/extensions/dataforseo"
      cp "${TMP_DIR}/upstream/extensions/dataforseo/field-config.json" \
         "${SEO_INSTALL}/extensions/dataforseo/field-config.json"
      try_install_extension dataforseo python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "dataforseo",
    credentials={"DATAFORSEO_USERNAME": "${DATAFORSEO_USERNAME}",
                 "DATAFORSEO_PASSWORD": "${DATAFORSEO_PASSWORD}"},
    extra_env={"FIELD_CONFIG_PATH": "${SEO_INSTALL}/extensions/dataforseo/field-config.json"})
PY
    fi
  fi

  if should_install_extension banana; then
    read -rsp "  Google AI (Gemini) API key: " GOOGLE_AI_API_KEY; echo
    if [ -z "${GOOGLE_AI_API_KEY}" ]; then
      warn "banana: empty API key — skipping"
      EXTENSION_FAILURES+=("banana (empty key)")
    else
      try_install_extension banana python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "banana",
    credentials={"GOOGLE_AI_API_KEY": "${GOOGLE_AI_API_KEY}"})
PY
    fi
  fi

  if should_install_extension ahrefs; then
    read -rsp "  Ahrefs API token: " AHREFS_API_TOKEN; echo
    if [ -z "${AHREFS_API_TOKEN}" ]; then
      warn "ahrefs: empty API token — skipping"
      EXTENSION_FAILURES+=("ahrefs (empty token)")
    else
      try_install_extension ahrefs python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "ahrefs",
    credentials={"AHREFS_API_TOKEN": "${AHREFS_API_TOKEN}"})
PY
    fi
  fi
}

install_mcp_extensions
echo "(script-only extensions + hooks + venv follow)"
```

- [ ] **Step 2: Smoke test (with no extension flags — should skip all prompts in noninteractive)**

```bash
cd $PORT
./install.sh --noninteractive
cat ~/.gemini/config/mcp_config.json 2>/dev/null || echo "no MCP config (expected — none installed)"
```

Expected: no MCP config (the file may not exist if it had no entries before this run, which is fine).

- [ ] **Step 3: Smoke test with one extension via flag**

```bash
WITH=firecrawl FIRECRAWL_API_KEY=test ./install.sh --with-extensions firecrawl
# (Won't actually prompt since we don't pipe input — comment out the read in shell to test, or just test the helper directly via pytest)
```

Note: realistic test of the prompted version is in `test_smoke.sh` (Phase 10) with `expect` or piped inputs.

- [ ] **Step 4: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: interactive MCP extension prompts + installs"
```

### Task 8.6: Prompt + install script-only extensions

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append step**

Replace `echo "(script-only extensions + hooks + venv follow)"` with:

```bash
install_script_extensions() {
  log "script-only extensions ..."

  if should_install_extension bing-webmaster; then
    read -rsp "  Bing Webmaster Tools API key (empty to skip): " BING_KEY; echo
    read -rp  "  IndexNow host key (empty to skip): " INDEXNOW_KEY
    read -rp  "  IndexNow key location URL (https://example.com/<key>.txt, empty to skip): " INDEXNOW_LOC
    python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import env_install
creds = {}
if "${BING_KEY}":  creds["BING_WEBMASTER_API_KEY"]   = "${BING_KEY}"
if "${INDEXNOW_KEY}": creds["INDEXNOW_KEY"]          = "${INDEXNOW_KEY}"
if "${INDEXNOW_LOC}": creds["INDEXNOW_KEY_LOCATION"] = "${INDEXNOW_LOC}"
env_install.install_script_extension(Path("${ENV_FILE}"), "bing-webmaster", credentials=creds)
PY
    ok "bing-webmaster installed"
  fi

  if should_install_extension profound; then
    read -rsp "  Profound API key: " PROFOUND_KEY; echo
    python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import env_install
env_install.install_script_extension(
    Path("${ENV_FILE}"), "profound",
    credentials={"PROFOUND_API_KEY": "${PROFOUND_KEY}"})
PY
    ok "profound installed"
  fi

  if should_install_extension seranking; then
    read -rsp "  SE Ranking API key: " SERANKING_KEY; echo
    python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import env_install
env_install.install_script_extension(
    Path("${ENV_FILE}"), "seranking",
    credentials={"SERANKING_API_KEY": "${SERANKING_KEY}"})
PY
    ok "seranking installed"
  fi

  if should_install_extension unlighthouse; then
    log "  pre-warming unlighthouse-cli ..."
    npx --yes --package=unlighthouse-cli@^0.13 unlighthouse-ci --help >/dev/null 2>&1 || true
    ok "unlighthouse pre-warmed"
  fi

  # Install dotenv shim alongside the .env so script-only extension Python wrappers can use it
  if [ -f "${ENV_FILE}" ]; then
    cp "${PORT_ROOT}/templates/dotenv_shim.py" "${SEO_INSTALL}/scripts/dotenv_shim.py"
    ok "dotenv shim installed"
  fi
}

install_script_extensions
echo "(hooks + venv follow)"
```

- [ ] **Step 2: Smoke test**

```bash
cd $PORT
./install.sh --noninteractive
```

Expected: no script-only extensions installed (because flags didn't request any).

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: interactive script-only extension prompts + .env writes"
```

### Task 8.7: Install hooks

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append step**

Replace `echo "(hooks + venv follow)"` with:

```bash
install_hooks() {
  log "installing schema-validation hook ..."
  mkdir -p "${SEO_INSTALL}/hooks"
  cp "${TMP_DIR}/upstream/hooks/validate-schema.py" "${SEO_INSTALL}/hooks/validate-schema.py"
  chmod +x "${SEO_INSTALL}/hooks/validate-schema.py"

  # File path resolved by §9 unknown #2; default to ~/.gemini/antigravity/hooks.json.
  # Variable name for $FILE_PATH defaults to `$1` (positional) if no Antigravity-specific var.
  local HOOKS_FILE="${INSTALL_ROOT}/hooks.json"
  local FILE_PATH_VAR='$1'

  python3 - <<PY
import json, os, sys, tempfile
hooks_path = "${HOOKS_FILE}"
install_path = "${SEO_INSTALL}"
file_path_var = '${FILE_PATH_VAR}'

template = open("${PORT_ROOT}/templates/hooks.json.tmpl").read()
new_hooks = json.loads(
    template
    .replace("{INSTALL_PATH}", install_path)
    .replace("{FILE_PATH_VAR}", file_path_var)
)

existing = {}
if os.path.exists(hooks_path):
    try:
        existing = json.load(open(hooks_path))
    except json.JSONDecodeError:
        pass

merged = existing
merged.setdefault("hooks", {}).setdefault("PostToolUse", [])

# Idempotent: replace any prior entry from this installer.
owner_tag = "antigravity-seo-validate-schema"
merged["hooks"]["PostToolUse"] = [
    h for h in merged["hooks"]["PostToolUse"]
    if h.get("_owner") != owner_tag
]
new_entry = new_hooks["hooks"]["PostToolUse"][0]
new_entry["_owner"] = owner_tag
merged["hooks"]["PostToolUse"].append(new_entry)

os.makedirs(os.path.dirname(hooks_path), exist_ok=True)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(hooks_path), prefix=".hooks.", suffix=".json")
with os.fdopen(fd, "w") as fh:
    json.dump(merged, fh, indent=2)
os.replace(tmp, hooks_path)
print(f"  hooks merged into {hooks_path}")
PY
  ok "hook installed"

  # Smoke-test the validator script standalone
  echo '<script type="application/ld+json">{"@context":"https://schema.org"}</script>' > /tmp/.schema-probe.html
  if "${SEO_INSTALL}/.venv/bin/python" "${SEO_INSTALL}/hooks/validate-schema.py" /tmp/.schema-probe.html >/dev/null 2>&1; then
    ok "validator script smoke-tested"
  else
    warn "validator script smoke test failed (will retry post-venv)"
  fi
  rm -f /tmp/.schema-probe.html
}

install_hooks
echo "(venv follows)"
```

- [ ] **Step 2: Smoke test**

```bash
cd $PORT
./install.sh --noninteractive
cat ~/.gemini/antigravity/hooks.json
```

Expected: `hooks.json` exists with a `PostToolUse` entry.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: merge schema-validation hook into Antigravity hooks file"
```

### Task 8.8: Set up venv + Python dependencies

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append step**

Replace `echo "(venv follows)"` with:

```bash
install_venv() {
  log "creating venv at ${SEO_INSTALL}/.venv ..."
  if ! python3 -m venv "${SEO_INSTALL}/.venv" 2>/dev/null; then
    warn "venv creation failed; falling back to --user install"
    warn "  manual fix: pip install --user -r ${SEO_INSTALL}/requirements.txt"
    VENV_OK=0
  else
    VENV_OK=1
    ok "venv created"
  fi

  if [ -f "${TMP_DIR}/upstream/requirements.txt" ]; then
    cp "${TMP_DIR}/upstream/requirements.txt" "${SEO_INSTALL}/requirements.txt"
    log "installing Python deps ..."
    if [ "${VENV_OK}" -eq 1 ]; then
      "${SEO_INSTALL}/.venv/bin/pip" install --quiet -r "${SEO_INSTALL}/requirements.txt" \
        || warn "pip install failed; rerun: ${SEO_INSTALL}/.venv/bin/pip install -r ${SEO_INSTALL}/requirements.txt"
    else
      pip install --quiet --user -r "${SEO_INSTALL}/requirements.txt" \
        || warn "pip --user install failed; install Python deps manually"
    fi
    ok "Python deps installed"
  fi

  log "installing Playwright browsers (optional) ..."
  if [ -f "${SEO_INSTALL}/.venv/bin/playwright" ]; then
    "${SEO_INSTALL}/.venv/bin/python" -m playwright install chromium >/dev/null 2>&1 \
      && ok "Playwright Chromium installed" \
      || warn "Playwright install failed (visual analysis will fall back to WebFetch)"
  fi
}

install_venv
echo "(portability check follows)"
```

- [ ] **Step 2: Smoke test**

```bash
cd $PORT
./install.sh --noninteractive
ls ~/.gemini/antigravity/skills/seo/.venv/bin/python
```

Expected: venv python interpreter present.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: venv + pip install + optional playwright"
```

### Task 8.9: Portability check + final summary

**Files:**
- Modify: `$PORT/install.sh`

- [ ] **Step 1: Append step**

Replace `echo "(portability check follows)"` with:

```bash
verify_install() {
  log "running portability check on installed tree ..."
  python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import portability_check as pc
findings = pc.check_tree(Path("${INSTALL_ROOT}/skills"))
errors = [f for f in findings if f["severity"] == "error"]
warnings_ = [f for f in findings if f["severity"] == "warning"]
print(f"  errors: {len(errors)}, warnings: {len(warnings_)}")
for e in errors:
    print(f"  ✗ {e['path']}: {e['rule']}: {e['message']}")
sys.exit(1 if errors else 0)
PY
  ok "portability check passed"
}

print_summary() {
  local skill_count workflow_count
  skill_count="$(find "${INSTALL_ROOT}/skills" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
  workflow_count="$(find "${INSTALL_ROOT}/workflows" -maxdepth 1 -name 'seo*.md' | wc -l | tr -d ' ')"
  printf "\n════════════════════════════════════════\n"
  printf "║   Install complete                    ║\n"
  printf "════════════════════════════════════════\n\n"
  printf "Skills:    %s installed at %s/skills/\n" "${skill_count}" "${INSTALL_ROOT}"
  printf "Workflows: %s installed at %s/workflows/\n" "${workflow_count}" "${INSTALL_ROOT}"
  printf "MCP servers: see %s\n" "${MCP_CONFIG}"
  printf "Hooks: see %s/hooks.json\n" "${INSTALL_ROOT}"
  printf "Venv:  %s/.venv\n\n" "${SEO_INSTALL}"
  if [ "${#EXTENSION_FAILURES[@]:-0}" -gt 0 ]; then
    printf "Skipped extensions (rerun with --with-extensions to retry):\n"
    for ext in "${EXTENSION_FAILURES[@]}"; do
      printf "  - %s\n" "${ext}"
    done
    printf "\n"
  fi
  printf "Verify:\n"
  printf "  antigravity\n"
  printf "  /seo audit https://example.com\n\n"
  printf "Uninstall:\n"
  printf "  bash %s/uninstall.sh\n\n" "${PORT_ROOT}"
}

verify_install
print_summary
```

- [ ] **Step 2: End-to-end smoke**

```bash
cd $PORT
./install.sh --noninteractive
```

Expected: full flow succeeds; final summary prints counts; `antigravity` invocation hint printed.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add install.sh
git commit -m "install: portability verification + final summary"
```

---

## Phase 9: Uninstaller (`uninstall.sh`)

### Task 9.1: Uninstaller with snapshot

**Files:**
- Create: `$PORT/uninstall.sh`

- [ ] **Step 1: Create uninstaller**

`$PORT/uninstall.sh`:

```bash
#!/usr/bin/env bash
# antigravity-seo-port uninstaller.
#
# Removes everything installed by install.sh, surgically. Does NOT touch
# MCP servers or hooks installed by other projects.
set -euo pipefail

PORT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
INSTALL_ROOT="${HOME}/.gemini/antigravity"
SEO_INSTALL="${INSTALL_ROOT}/skills/seo"
MCP_CONFIG="${HOME}/.gemini/config/mcp_config.json"
HOOKS_FILE="${INSTALL_ROOT}/hooks.json"
ENV_FILE="${SEO_INSTALL}/.env"

NONINTERACTIVE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --noninteractive) NONINTERACTIVE=1 ;;
    -h|--help) echo "Usage: bash uninstall.sh [--noninteractive]"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

log() { printf "  %s\n" "$*"; }
ok()  { printf "✓ %s\n" "$*"; }
warn(){ printf "! %s\n" "$*" >&2; }

confirm() {
  if [ "${NONINTERACTIVE}" -eq 1 ]; then return 0; fi
  read -rp "$1 [y/N] " ans
  [ "${ans}" = "y" ] || [ "${ans}" = "Y" ]
}

snapshot() {
  local ts manifest
  ts="$(date +%Y%m%d-%H%M%S)"
  manifest="${INSTALL_ROOT}/.antigravity-seo-uninstall-manifest-${ts}.json"
  python3 - "${manifest}" <<'PY'
import json, os, sys
from pathlib import Path
manifest = sys.argv[1]
install_root = Path(os.path.expanduser("~/.gemini/antigravity"))
data = {"skills": [], "workflows": []}
skills = install_root / "skills"
if skills.exists():
    data["skills"] = sorted(p.name for p in skills.iterdir() if p.is_dir() and p.name.startswith("seo"))
wf = install_root / "workflows"
if wf.exists():
    data["workflows"] = sorted(p.name for p in wf.glob("seo*.md"))
Path(manifest).parent.mkdir(parents=True, exist_ok=True)
Path(manifest).write_text(json.dumps(data, indent=2))
print(manifest)
PY
}

remove_skills() {
  log "removing seo-* skill directories ..."
  for d in "${INSTALL_ROOT}/skills/seo"*; do
    [ -d "${d}" ] || continue
    rm -rf "${d}"
  done
  ok "skills removed"
}

remove_workflows() {
  log "removing /seo workflows ..."
  python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import workflow_install
workflow_install.uninstall_workflows(Path("${INSTALL_ROOT}/workflows"))
PY
  ok "workflows removed"
}

remove_mcp() {
  log "removing owned MCP server entries ..."
  python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
for ext in ["firecrawl", "dataforseo", "banana", "ahrefs"]:
    mcp_install.remove_mcp_server(Path("${MCP_CONFIG}"), ext)
PY
  ok "MCP entries removed"
}

remove_env() {
  if [ -f "${ENV_FILE}" ]; then
    if confirm "Remove ${ENV_FILE} (contains API credentials)?"; then
      python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import env_install
env_install.uninstall_script_extension(Path("${ENV_FILE}"))
PY
      ok ".env credentials removed"
    else
      warn ".env kept at ${ENV_FILE}"
    fi
  fi
}

remove_hooks() {
  if [ -f "${HOOKS_FILE}" ]; then
    log "removing owned hooks ..."
    python3 - <<PY
import json
from pathlib import Path
p = Path("${HOOKS_FILE}")
data = json.loads(p.read_text())
post = data.get("hooks", {}).get("PostToolUse", [])
data["hooks"]["PostToolUse"] = [h for h in post if h.get("_owner") != "antigravity-seo-validate-schema"]
p.write_text(json.dumps(data, indent=2))
PY
    ok "hooks removed"
  fi
}

remove_misc() {
  if [ -f "${INSTALL_ROOT}/AGENTS.md" ]; then
    rm "${INSTALL_ROOT}/AGENTS.md"
    ok "removed AGENTS.md"
  fi
}

printf "════════════════════════════════════════\n"
printf "║   antigravity-seo-port — Uninstaller  ║\n"
printf "════════════════════════════════════════\n\n"

if ! confirm "Proceed with uninstall?"; then
  echo "Aborted."
  exit 0
fi

manifest_path="$(snapshot)"
ok "snapshot saved: ${manifest_path}"

remove_skills
remove_workflows
remove_mcp
remove_env
remove_hooks
remove_misc

printf "\nDone. Snapshot: %s\n" "${manifest_path}"
```

- [ ] **Step 2: Make executable + smoke test**

```bash
cd $PORT
chmod +x uninstall.sh
./install.sh --noninteractive
./uninstall.sh --noninteractive
ls ~/.gemini/antigravity/skills 2>/dev/null
```

Expected: install completes; uninstall removes all seo-* dirs; no residual seo* files in `~/.gemini/antigravity/skills/`.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add uninstall.sh
git commit -m "uninstall: surgical removal with snapshot manifest"
```

---

## Phase 10: End-to-end smoke test

### Task 10.1: Sandbox smoke test

**Files:**
- Create: `$PORT/tests/test_smoke.sh`

- [ ] **Step 1: Create smoke test**

`$PORT/tests/test_smoke.sh`:

```bash
#!/usr/bin/env bash
# End-to-end smoke test: install in a sandbox, assert structure, uninstall.
#
# Runs entirely in a tmpdir-based fake $HOME. Does NOT mutate the user's
# real ~/.gemini/.
set -euo pipefail

PORT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
SANDBOX="$(mktemp -d "${TMPDIR:-/tmp}/antigravity-seo-smoke.XXXX")"
trap 'rm -rf "${SANDBOX}"' EXIT

export HOME="${SANDBOX}"
mkdir -p "${HOME}/.gemini"  # mimic an initialized Antigravity install

cd "${PORT_ROOT}"
bash install.sh --noninteractive

# Assertions
SKILL_COUNT="$(find "${HOME}/.gemini/antigravity/skills" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
[ "${SKILL_COUNT}" -ge 25 ] || { echo "FAIL: expected ≥25 skills, got ${SKILL_COUNT}"; exit 1; }
echo "PASS: ${SKILL_COUNT} skills installed"

[ -f "${HOME}/.gemini/antigravity/workflows/seo.md" ] || { echo "FAIL: seo.md missing"; exit 1; }
echo "PASS: dispatcher present"

grep -q "audit" "${HOME}/.gemini/antigravity/workflows/seo.md" || { echo "FAIL: dispatcher missing 'audit'"; exit 1; }
echo "PASS: dispatcher contains audit subcommand"

[ -f "${HOME}/.gemini/antigravity/skills/seo/.venv/bin/python" ] || { echo "FAIL: venv missing"; exit 1; }
echo "PASS: venv installed"

[ -f "${HOME}/.gemini/antigravity/hooks.json" ] || { echo "FAIL: hooks.json missing"; exit 1; }
echo "PASS: hooks.json present"

# Uninstall
bash uninstall.sh --noninteractive

REMAINING="$(find "${HOME}/.gemini/antigravity/skills" -maxdepth 1 -name 'seo*' 2>/dev/null | wc -l | tr -d ' ')"
[ "${REMAINING}" -eq 0 ] || { echo "FAIL: ${REMAINING} seo* dirs remain after uninstall"; exit 1; }
echo "PASS: clean uninstall"

echo ""
echo "════════════════════════════════════════"
echo "║   Smoke test: ALL PASSED              ║"
echo "════════════════════════════════════════"
```

- [ ] **Step 2: Make executable + run**

```bash
cd $PORT
chmod +x tests/test_smoke.sh
bash tests/test_smoke.sh
```

Expected: "ALL PASSED" message at the end.

- [ ] **Step 3: Commit**

```bash
cd $PORT
git add tests/test_smoke.sh
git commit -m "smoke: end-to-end install + uninstall in hermetic sandbox"
```

---

## Phase 11: User-facing README

### Task 11.1: Write the README

**Files:**
- Modify: `$PORT/README.md`

- [ ] **Step 1: Replace placeholder**

`$PORT/README.md`:

```markdown
# antigravity-seo-port

One-command installer that brings [claude-seo](https://github.com/AgriciDaniel/claude-seo) — Tier-4 SEO analysis with 25 skills, 18 specialist agents, and 8 extensions — to Google Antigravity (CLI + desktop).

## Prerequisites

- macOS or Linux (Windows: PowerShell port not yet available)
- [Google Antigravity](https://antigravity.google) installed and signed in
- Python 3.10 or newer
- Node.js 20+ (for `npx`-bootstrapped MCP servers)
- `git`, `rsync`

## Install

```bash
git clone <this repo URL> antigravity-seo-port
cd antigravity-seo-port
bash install.sh
```

The installer:

1. Clones a pinned tag of upstream claude-seo
2. Converts skills + agents to Antigravity's `SKILL.md` shape
3. Installs into `~/.gemini/antigravity/skills/seo-*` (25 skills + 18 agent-derived skills)
4. Generates `/seo` slash command + convenience workflows (`/seo-audit`, `/seo-page`, …) at `~/.gemini/antigravity/workflows/`
5. Prompts to install each of 8 optional extensions:
   - **MCP-server extensions** (added to `~/.gemini/config/mcp_config.json`): Firecrawl, DataForSEO, Banana (image gen), Ahrefs
   - **Script-only extensions** (credentials → `~/.gemini/antigravity/skills/seo/.env`): Bing Webmaster + IndexNow, Profound, SE Ranking, Unlighthouse
6. Sets up a Python venv with all dependencies
7. Installs a `PostToolUse` schema-validation hook
8. Runs a portability check

Non-interactive base install (no extensions):

```bash
bash install.sh --noninteractive
```

With specific extensions:

```bash
bash install.sh --with-extensions firecrawl,dataforseo
```

## Usage

After install:

```bash
antigravity
```

Then in the prompt:

```
/seo audit https://example.com
/seo page https://example.com/about
/seo schema https://example.com
/seo geo https://example.com
/seo firecrawl crawl https://example.com    # if Firecrawl extension installed
```

Full command list lives in the installed skill at `~/.gemini/antigravity/skills/seo/SKILL.md` and in upstream's `docs/COMMANDS.md`.

## Uninstall

```bash
bash uninstall.sh
```

Surgical: only entries this installer wrote are removed. Other MCP servers, hooks, and skills are left untouched. A snapshot manifest is saved to `~/.gemini/antigravity/.antigravity-seo-uninstall-manifest-<timestamp>.json` for recovery.

## Behavioral differences vs. Claude Code

- **Subagent fan-out is sequential.** Claude Code's `/seo audit` dispatches up to 15 specialist subagents in parallel; on Antigravity the orchestrator loads them sequentially (Antigravity's CLI workflow model doesn't expose parallel subagent dispatch). Wall time is longer. The desktop app's multi-agent orchestrator may enable parallelism in a future revision of this port.

## Updating

```bash
cd antigravity-seo-port
git pull
bash install.sh --upstream-tag <new-tag>
```

Rsync's `--delete` ensures stale skills removed upstream are also removed locally.

## License

Installer: MIT. Upstream claude-seo: MIT (see https://github.com/AgriciDaniel/claude-seo/blob/main/LICENSE).
```

- [ ] **Step 2: Commit**

```bash
cd $PORT
git add README.md
git commit -m "README: user-facing install/usage/uninstall docs"
```

---

## Phase 12: Final verification

### Task 12.1: Full test pass + final smoke

**Files:**
- (none — verification only)

- [ ] **Step 1: Run full pytest suite**

```bash
cd $PORT
pytest -v
```

Expected: all unit tests pass.

- [ ] **Step 2: Run smoke test**

```bash
cd $PORT
bash tests/test_smoke.sh
```

Expected: "ALL PASSED".

- [ ] **Step 3: Run real install on the engineer's actual machine**

```bash
cd $PORT
bash install.sh
```

Step through extension prompts. Choose at least 1 MCP extension and 1 script-only extension to exercise both code paths.

- [ ] **Step 4: Manual verification checklist**

Open Antigravity:

- [ ] `antigravity` starts cleanly
- [ ] `/seo` appears in the slash command menu
- [ ] `/seo audit https://en.wikipedia.org/wiki/Search_engine_optimization` runs without YAML/parse errors and produces output
- [ ] `/seo page <url>` returns a single-page report
- [ ] `/seo schema <url>` detects + validates JSON-LD
- [ ] If Firecrawl installed: `/seo firecrawl crawl <url>` returns crawl results
- [ ] If DataForSEO installed: `/seo dataforseo serp <kw>` returns SERP rows
- [ ] Editing a file containing `<script type="application/ld+json">{...}</script>` fires the validate-schema hook (visible in Antigravity's hook log if available, or by running the hook script standalone)

- [ ] **Step 5: If any manual check fails**

- File a follow-up in `_research/notes.md` describing the failure
- For frontmatter parse errors: revisit Task 2.2 (normalize_frontmatter) and add the rejecting key to `_KEEP_KEYS` removal list
- For workflow not appearing: revisit Task 1.1 — workflows global path may need to be workspace-scoped; update Task 8.4 to write to `<workspace>/.agents/workflows/` instead
- For MCP server not callable: check `~/.gemini/config/mcp_config.json` shape matches what Antigravity expects (`serverUrl` not `url`, etc.)

- [ ] **Step 6: Commit any followup notes**

```bash
cd $PORT
git add _research/notes.md
git commit -m "verification: record any post-install findings"
```

---

## Spec coverage check

| Spec section | Covered by |
|---|---|
| §1 Summary | Goal at top of plan |
| §2 Goal 1 (full feature parity) | Phases 2–9 |
| §2 Goal 2 (CLI works first) | Phase 10 smoke + Phase 12 manual checks |
| §2 Goal 3 (one-command install/uninstall) | Phase 8 + Phase 9 |
| §2 Goal 4 (idempotent re-runs) | Task 3.3, 4.1, 8.x rsync with --delete |
| §2 Goal 5 (failure-loud) | install.sh `die`/`warn`; Task 3.3 raises on missing required env |
| §3 Background | Read at design time; no plan task |
| §4.1 Distribution model | File Structure section + Phase 0 |
| §4.2 Source-to-install mapping | Task 2.7 (convert_tree) + Tasks 8.3/8.4 (rsync + workflows) |
| §4.3 Conversion pass | Tasks 2.1–2.7 |
| §5.1 Skills | Task 2.7 (convert_tree skills branch) + Task 8.3 (rsync) |
| §5.2 Subagents → skills | Tasks 2.5, 2.7 |
| §5.3 `/seo` dispatcher + per-subcmd workflows | Tasks 5.1, 5.2, 8.4 |
| §5.4 MCP-server extensions (4) | Tasks 3.1–3.4, 8.5 |
| §5.5 Script-only extensions (4) | Tasks 4.1, 4.2, 8.6, 7.2 (dotenv shim) |
| §5.6 Hooks | Tasks 7.1, 8.7 |
| §5.7 Shared assets | Task 8.3 (rsync of scripts/schema/pdf/data) |
| §5.8 Python venv | Task 8.8 |
| §6 Installation flow | Phase 8 (Tasks 8.1–8.9) |
| §6.1 Idempotency invariants | Task 3.3 (overwrite), Task 4.1 (block merge), Task 8.3 (rsync --delete) |
| §6.2 Failure modes | install.sh die/warn pattern across Tasks 8.1–8.9 |
| §7 Uninstall flow | Task 9.1 |
| §8.1 Unit tests | Tasks 2.x, 3.x, 4.x, 5.x, 6.1 (each phase ends with tests) |
| §8.2 Smoke test | Task 10.1 |
| §8.3 Manual checklist | Task 12.1 step 4 |
| §9 Known unknowns | Phase 1 (Tasks 1.1–1.6) |
| §10 Risks | Handled by file mode 0o600 (Task 4.1), atomic writes (Task 3.1), --noninteractive flag (Task 8.1) |
| §11 File manifest | Matches File Structure section at top of plan |
| §12 Success criteria | Phase 12 step 4 manual checklist enumerates each criterion |

No spec sections without coverage.
