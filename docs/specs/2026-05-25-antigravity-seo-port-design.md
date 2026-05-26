# antigravity-seo: Full-Parity Port of claude-seo to Google Antigravity

- **Date:** 2026-05-25
- **Author:** jspringe (with Claude)
- **Status:** Draft — awaiting user review
- **Source repo:** https://github.com/AgriciDaniel/claude-seo (pinned to v2.0.0)
- **Target:** Antigravity CLI (primary) + Antigravity desktop app (no extra work expected — same on-disk format)

---

## 1. Summary

Produce a single installation script and a small set of generated artifacts that install **every feature** of claude-seo v2.0.0 into a Google Antigravity environment, with behavioral parity for an end user. After install, the user runs `antigravity` in any directory and can invoke `/seo <subcommand> [args]` exactly as documented for the Claude Code version, with the same skills auto-triggering, the same MCP servers backing them, and the same hook-based schema validation firing on edits.

The deliverable is **not** a fork of claude-seo. It is a separate companion project (`antigravity-seo-port/`) containing a converter + installer that consumes a pinned version of upstream claude-seo and produces an Antigravity-shaped install in the user's home directory.

---

## 2. Goals

1. **Full feature parity** with claude-seo v2.0.0 on Claude Code, including:
   - All 25 skills, all 18 subagents (mapped to Antigravity's skill model)
   - All 8 extensions (Ahrefs, Banana, Bing Webmaster, DataForSEO, Firecrawl, Profound, SE Ranking, Unlighthouse)
   - The full `/seo` slash-command surface (~25 subcommands)
   - The `PostToolUse` schema validation hook
   - All Python helper scripts and reference assets
2. **CLI works first.** Verification is "open Antigravity CLI, run `/seo audit https://example.com`, get a real report." Desktop app gets free coverage from the shared on-disk format, but is not a blocker.
3. **One-command install + one-command uninstall.** No manual file editing required for the base install.
4. **Idempotent re-runs.** Re-running the installer upgrades cleanly without corrupting `mcp_config.json` or stranding orphan files.
5. **Failure-loud, not failure-silent.** If an extension can't be installed (missing API key, missing prereq), the script reports it and continues with the rest — never half-writes a config.

## 2.1 Non-goals

- **Not** maintaining a long-lived fork of claude-seo. We pin to an upstream tag and re-run the converter on upgrades.
- **Not** publishing to any plugin marketplace (Antigravity, Gemini CLI, etc.). Personal-use install.
- **Not** porting Claude Code's `marketplace.json` concept. A standalone install script is sufficient.
- **Not** translating Antigravity's multi-agent desktop orchestration into something the CLI does. We accept that subagent fan-out is sequential under Antigravity (see §10).
- **Not** building a converter for Cursor, Codex, Cline, Aider, etc. Antigravity only.

---

## 3. Background

### 3.1 What claude-seo ships

| Component | Count | Source path | Format |
|---|---|---|---|
| Skills | 25 | `skills/seo*/SKILL.md` | YAML frontmatter (`name`, `description`, optional `model`/`tools`/`metadata`) + Markdown |
| Subagents | 18 | `agents/seo-*.md` | YAML frontmatter (`name`, `description`, `model`, `maxTurns`, `tools`) + Markdown persona |
| Slash commands | ~25 | Implicit — `/seo` is rooted at `skills/seo/SKILL.md`; subcommands dispatch to other skills | None — the orchestrator skill body parses the user input |
| MCP servers | 4 of 8 extensions | `extensions/{firecrawl,dataforseo,banana,ahrefs}/install.sh` writes `~/.claude/settings.json` `mcpServers` | Claude Code `settings.json` schema |
| Script-only extensions | 4 of 8 (`bing-webmaster`, `profound`, `seranking`, `unlighthouse`) | Each `install.sh` ships a skill + (for non-Unlighthouse) writes API keys to `~/.claude/settings.json` `env` block | Settings env vars consumed by Python scripts |
| Hooks | 1 | `hooks/hooks.json` registering `PostToolUse` on `Edit\|Write` → `hooks/validate-schema.py` | Claude Code hooks JSON |
| Python scripts | ~50 | `scripts/*.py` | Plain Python, called from skills via `python scripts/<name>.py` |
| Reference assets | many | `skills/seo/references/`, `schema/`, `pdf/`, `data/` | Markdown / JSON |
| Portability infra | n/a | `AGENTS.md`, `scripts/portability_check.py`, `tests/test_portability.py` | Already cross-harness; we will reuse the lint |

### 3.2 What Antigravity provides

| Antigravity primitive | On-disk location | Format |
|---|---|---|
| Skills (global) | `~/.gemini/antigravity/skills/<name>/SKILL.md` | YAML frontmatter (`name`, `description`) + Markdown; auto-triggered on semantic match against `description` |
| Skills (workspace) | `<workspace>/.agents/skills/<name>/SKILL.md` | Same |
| Workflows (slash commands) | `<workspace>/.agents/workflows/<name>.md` → `/<name>` | YAML frontmatter (`description`) + Markdown orchestration body |
| Subagent personas (codelab pattern) | `<workspace>/.agents/agents.md` | One file, sections like `## The Product Manager (@pm)` |
| MCP servers (CLI + IDE shared) | `~/.gemini/config/mcp_config.json` (global, cross-tool) | `{"mcpServers": {...}}` with `command`/`args`/`env` for stdio, `serverUrl`/`authProviderType` for HTTP; `serverUrl` (not `url`), no top-level `timeout`, no comments |
| Hooks | Per Antigravity 2.0: same JSON shape as Claude Code (`PostToolUse`, `matcher`, `hooks[].type`/`command`), wrapped in `{"hooks": {...}}` | JSON |

### 3.3 Where they line up cleanly

- **Skill SKILL.md format.** claude-seo already authors to a portable subset (validated by `portability_check.py`). The Claude-only frontmatter fields (`maxTurns`, `user-invokable`, `argument-hint`, `metadata`) are tolerated as unknown keys by Antigravity's YAML parser.
- **Python helper scripts.** Antigravity skills call Bash the same way Claude Code does. `python scripts/fetch_page.py <url>` works in both.
- **MCP transport.** Both use stdio MCP via `npx`-bootstrapped servers. The wrapping config differs but the underlying server invocation is identical.
- **Hooks JSON.** Per available Antigravity docs, the `PostToolUse` shape with `matcher` and `hooks[].command` carries over.

### 3.4 Where they don't

- **Subagent model.** claude-seo's `agents/seo-*.md` are *delegate* personas with `model`/`maxTurns`/`tools` — Claude Code's orchestrator routes work to them and they run in isolated context. Antigravity's `.agents/agents.md` is a single-file team roster intended for a codelab-style PM/Eng/QA workflow; it does not map 1:1 to 18 individually-dispatched specialists. **Decision:** map each `agents/seo-*.md` to a top-level Antigravity *Skill* (auto-triggered by description). The orchestrator skill body invokes them in sequence rather than parallel-fanning them out. See §5.2 and §10.
- **`/seo` subcommand routing.** Claude Code's skill orchestrator parses `/seo <subcmd>` because the user types it inside a Claude Code session and the skill body does the dispatch. Antigravity's workflows give us `/<filename>` directly but no native subcommand structure. **Decision:** one `seo.md` workflow whose body is an LLM dispatcher (model parses arg 1, loads the right child skill), plus optional convenience workflows `seo-audit.md`, `seo-page.md`, etc. for direct shortcuts. See §5.3.
- **`settings.json` env block.** Claude Code injects env vars from `settings.json` `env` into tool calls. Antigravity has no documented equivalent. For the 4 script-only extensions that rely on this (`bing-webmaster`, `profound`, `seranking`), we store credentials in a project-local `~/.gemini/antigravity/skills/seo/.env` file and wrap the Python scripts with a tiny dotenv-loading shim. See §5.5.
- **Workflow discoverability.** Antigravity's documented workflow path is `<workspace>/.agents/workflows/` (workspace-scoped). A "global workflows" path is not confirmed in the docs. **Resolution:** Implementation phase 1 verifies whether `~/.gemini/antigravity/workflows/` is read; if not, the installer drops workflows into the user's chosen "SEO workspace" (defaults to `~/seo`) and the user runs `antigravity` from there. See §9 unknown #1.

---

## 4. Architecture

### 4.1 Distribution model

A standalone Git repo `antigravity-seo-port/` containing:

```
antigravity-seo-port/
├── README.md                          # user-facing install instructions
├── install.sh                         # the installer (Bash)
├── uninstall.sh                       # the uninstaller (Bash)
├── lib/
│   ├── convert.py                     # Python module: skill/agent conversion logic
│   ├── mcp_install.py                 # Python module: idempotent mcp_config.json edits
│   ├── env_install.py                 # Python module: idempotent .env edits for script-only extensions
│   └── workflow_install.py            # Python module: workflow file generation + dispatcher rendering
├── templates/
│   ├── seo-workflow.md.tmpl           # the /seo dispatcher workflow template
│   ├── seo-subcmd-workflow.md.tmpl    # per-subcommand convenience workflow template
│   ├── hooks.json.tmpl                # Antigravity-shaped hooks.json template
│   └── dotenv-shim.py                 # tiny Python wrapper to load .env before running upstream scripts
├── tests/
│   ├── test_convert.py                # unit tests for skill/agent conversion
│   ├── test_mcp_install.py            # unit tests for mcp_config.json merge logic
│   ├── test_workflow_dispatch.py      # unit tests for /seo dispatcher template rendering
│   ├── test_portability.py            # re-run upstream portability lint on the converted install
│   └── test_smoke.sh                  # end-to-end smoke: install in a sandbox, list installed skills, dry-run /seo
└── _research/
    └── notes.md                       # field notes from §9 unknowns as they're resolved
```

The installer clones a pinned tag of upstream claude-seo into a temp dir, runs the conversion in-place to a staging directory, and atomically moves the converted tree into Antigravity's paths.

### 4.2 Source-to-install path mapping

| claude-seo source | Antigravity install destination |
|---|---|
| `skills/seo/` (orchestrator) | `~/.gemini/antigravity/skills/seo/` |
| `skills/seo-*/` (24 others) | `~/.gemini/antigravity/skills/seo-*/` (1:1) |
| `agents/seo-*.md` (18 files) | `~/.gemini/antigravity/skills/seo-*/SKILL.md` — each agent becomes a new skill (suffixed `-agent` if name collides with an existing skill, e.g. `seo-technical-agent`) |
| `scripts/*.py` | `~/.gemini/antigravity/skills/seo/scripts/` (single shared scripts dir; all skills reference via absolute path baked at install time) |
| `schema/` | `~/.gemini/antigravity/skills/seo/schema/` |
| `pdf/` | `~/.gemini/antigravity/skills/seo/pdf/` |
| `data/` | `~/.gemini/antigravity/skills/seo/data/` |
| `extensions/<ext>/skills/seo-<ext>/SKILL.md` | `~/.gemini/antigravity/skills/seo-<ext>/SKILL.md` |
| `extensions/<ext>/scripts/` (if present) | `~/.gemini/antigravity/skills/seo/scripts/` (merged into shared scripts dir) |
| `extensions/<ext>/references/` (if present) | `~/.gemini/antigravity/skills/seo-<ext>/references/` |
| Each extension's MCP server config (parsed from `install.sh`) | `~/.gemini/config/mcp_config.json` `mcpServers` entry |
| Each extension's `settings.json` env vars (where applicable) | `~/.gemini/antigravity/skills/seo/.env` |
| `hooks/hooks.json` + `hooks/validate-schema.py` | `~/.gemini/antigravity/skills/seo/hooks/` + registered at Antigravity's global hooks path (see §5.6) |
| `requirements.txt` | Installed into venv at `~/.gemini/antigravity/skills/seo/.venv/` |
| `AGENTS.md` | Copied to `~/.gemini/antigravity/AGENTS.md` (session-load context) |
| `/seo` slash command | Generated `seo.md` workflow (see §5.3); plus generated convenience workflows for each subcommand |

### 4.3 The conversion pass

Performed by `lib/convert.py` between clone and copy. Operations:

1. **Frontmatter normalize.** Read each `SKILL.md`. Keep `name`, `description`, `model`, `tools`. Strip `maxTurns`, `user-invokable`, `argument-hint`. Move `metadata.*` under a flattened key so Antigravity's stricter YAML parser doesn't choke (verify in §9 unknown #5). Re-emit.
2. **Path rewrite.** Any in-body `python scripts/<x>.py` or `./scripts/<x>.py` becomes `python ${SEO_SCRIPTS}/<x>.py` where `${SEO_SCRIPTS}` resolves to `~/.gemini/antigravity/skills/seo/scripts/` (baked at install, not a runtime env var). Same for `schema/`, `pdf/`, `data/`, `references/` references.
3. **Agent → skill.** For each `agents/seo-X.md`: load frontmatter, drop `maxTurns`, write to `~/.gemini/antigravity/skills/seo-X/SKILL.md` (suffix `-agent` only on name collision with the same-named skill).
4. **Hooks.** Translate `${CLAUDE_PLUGIN_ROOT}` → absolute install path. Translate command form to Antigravity hooks JSON. Register at the global hooks path determined in §9 unknown #2 / §5.6.
5. **MCP entries.** For each extension, the converter has a hard-coded extraction (the install.sh files have only ~4 unique MCP config shapes — easier to maintain a table than parse Bash). Table is in `lib/mcp_install.py` and tested.
6. **Env-var-only extensions.** For `bing-webmaster`, `profound`, `seranking`: read the prompts the upstream installer would have asked, ask them in our installer, write to `.env`. Wrap the relevant Python scripts with `templates/dotenv-shim.py` so they load `.env` on import.

---

## 5. Component-by-component design

### 5.1 Skills

- **Source of truth:** upstream `skills/seo*/SKILL.md`, modified only by §4.3 conversion pass.
- **Install location:** `~/.gemini/antigravity/skills/seo*/`
- **Discovery:** Antigravity auto-loads any directory under `~/.gemini/antigravity/skills/` containing a `SKILL.md`. We rely on this.
- **Naming collisions with subagents:** see §5.2.

### 5.2 Subagents (mapped to skills)

- **Mapping rule:** each `agents/seo-X.md` becomes a skill at `~/.gemini/antigravity/skills/seo-X/SKILL.md`. If `seo-X` already exists as a skill (true for `seo-technical`, `seo-content`, `seo-schema`, `seo-sitemap`, `seo-geo`, `seo-local`, `seo-maps`, `seo-backlinks`, `seo-cluster`, `seo-sxo`, `seo-drift`, `seo-ecommerce`, `seo-google`, `seo-flow`, `seo-dataforseo`, `seo-image-gen`), the agent becomes `seo-X-agent` and is linked from the skill's body with "When delegated to as a specialist, use the `seo-X-agent` skill for the deep-dive."
- **Why not Antigravity's `agents.md`:** the codelab pattern is a single-file team roster (PM/Eng/QA), tuned for ~3–6 personas. 18 SEO specialists each with their own model/tool envelope doesn't fit cleanly. Skills are the better primitive — auto-triggered, isolatable scripts, and Antigravity already manages context window per loaded skill.
- **Behavioral consequence:** the orchestrator can no longer hand a URL to `seo-technical` AND `seo-content` AND `seo-schema` in parallel. They run sequentially. See §10 risk note.

### 5.3 `/seo` slash command + subcommand workflows

- **Primary file:** `~/.gemini/antigravity/workflows/seo.md` (or workspace-scoped — see §9 unknown #1).
- **Frontmatter:**
  ```yaml
  ---
  description: SEO toolkit. Usage: /seo <subcommand> [args]. Subcommands: audit, page, technical, content, schema, sitemap, images, geo, plan, cluster, sxo, drift, ecommerce, programmatic, competitor-pages, local, hreflang, google, backlinks, image-gen, firecrawl, dataforseo, ahrefs, bing, profound, seranking, unlighthouse.
  ---
  ```
- **Body:** LLM dispatcher. Parses arg 1 as subcommand, remainder as args, then **loads the matching skill** and delegates. Body is generated from `templates/seo-workflow.md.tmpl` at install time, with the subcommand table interpolated from the actual installed skills.
- **Convenience workflows:** for each subcommand, generate `seo-<subcmd>.md` so `/seo-audit https://example.com` works as a direct shortcut without going through the dispatcher. Same body template, just pre-bound to the subcommand.
- **Why both:** `/seo X` is the documented UX (parity goal). `/seo-X` is the more Antigravity-native shape (one workflow per slash command). Shipping both costs nothing and respects both worlds.

### 5.4 MCP-server extensions (4)

| Extension | Server name in mcp_config.json | Command | Args | Env required |
|---|---|---|---|---|
| firecrawl | `firecrawl-mcp` | `npx` | `-y firecrawl-mcp@3.11.0` | `FIRECRAWL_API_KEY` |
| dataforseo | `dataforseo` | `npx` | `-y dataforseo-mcp-server@2.8.10` | `DATAFORSEO_USERNAME`, `DATAFORSEO_PASSWORD`, `ENABLED_MODULES` (preset to the 9-module string from upstream), `FIELD_CONFIG_PATH` (resolved to install path) |
| banana | `nanobanana-mcp` | `npx` | `-y @ycse/nanobanana-mcp@1.1.1` | `GOOGLE_AI_API_KEY` |
| ahrefs | `ahrefs` | `npx` | `--yes --package=@ahrefs/mcp ahrefs-mcp` | `AHREFS_API_TOKEN` |

The installer prompts (interactively) for each, allowing skip. Each merge into `~/.gemini/config/mcp_config.json` is atomic (temp file + rename) and idempotent (same server name → overwrite the entry, leave others untouched). The installer enforces Antigravity's three documented constraints: `serverUrl` not `url`, no top-level `timeout`, no JSON comments.

### 5.5 Script-only extensions (4)

These ship a skill + (some) credentials, no MCP server.

| Extension | Skill installed | Credentials stored in `.env` | Notes |
|---|---|---|---|
| bing-webmaster | `seo-bing` (+ uses `scripts/bing_webmaster.py`, `scripts/indexnow_submit.py`) | `BING_WEBMASTER_API_KEY`, `INDEXNOW_KEY`, `INDEXNOW_KEY_LOCATION` | At least one of Bing key or IndexNow key required |
| profound | `seo-profound` | `PROFOUND_API_KEY` | API key required |
| seranking | `seo-seranking` | Verified in implementation against `extensions/seranking/install.sh` — expected to follow the `profound` pattern (single API key in `.env`); tracked in §9 unknown #6 | API key required |
| unlighthouse | `seo-unlighthouse` | (none) | Fully local. Just installs the skill + pre-warms `unlighthouse-cli` via `npx` |

**Credential loading.** Python scripts that previously consumed env vars set by Claude Code's `settings.json` are wrapped with a 3-line dotenv shim (`templates/dotenv-shim.py`) that loads `~/.gemini/antigravity/skills/seo/.env` if present. Wrapper is a sibling file invoked instead of the original (original is preserved unchanged for upstream-sync compatibility).

### 5.6 Hooks

- **Source:** upstream `hooks/hooks.json` registering `PostToolUse` on `Edit|Write` → `python ${CLAUDE_PLUGIN_ROOT}/hooks/validate-schema.py "$FILE_PATH"`.
- **Translation:**
  - `${CLAUDE_PLUGIN_ROOT}` → absolute install path `~/.gemini/antigravity/skills/seo` (resolved at install time)
  - `$FILE_PATH` → verify Antigravity's equivalent variable name in `_research/notes.md`; fall back to the first positional arg if Antigravity passes the file path as `$1`
- **Install location:** Antigravity global hooks file. Per available docs the format is `{"hooks": {"PostToolUse": [...]}}`; merging into an existing file uses the same idempotent strategy as MCP config (atomic temp+rename, idempotent on `matcher`+`command` tuple).
- **Validation:** the installer runs the hook script standalone after install with a fixture file to confirm Python interpreter and validator work.

### 5.7 Shared assets

- `scripts/` (merged from upstream `scripts/` plus all extension `scripts/`) — single shared dir at `~/.gemini/antigravity/skills/seo/scripts/`.
- `schema/`, `pdf/`, `data/` — copied wholesale.
- `references/` — per-skill; copied alongside each `SKILL.md`.
- `AGENTS.md` from upstream root — copied to `~/.gemini/antigravity/AGENTS.md` so Antigravity sees portable cross-harness instructions on session start.

### 5.8 Python environment

- Venv at `~/.gemini/antigravity/skills/seo/.venv/` (mirrors upstream's `~/.claude/skills/seo/.venv/`).
- Installs upstream `requirements.txt` verbatim.
- Optional: `playwright install chromium` (same fallback behavior as upstream — log a warning, don't fail).
- All `python` invocations in installed SKILL.md bodies use the venv's interpreter explicitly: `~/.gemini/antigravity/skills/seo/.venv/bin/python`. This avoids surprise from Antigravity launching skills with a different default Python.

---

## 6. Installation flow (`install.sh`)

Ordered, fail-loud, idempotent. Each step is logged with a single-line status and a clear ✓ / ✗ glyph.

1. **Preflight.** Check `python3 >=3.10`, `git`, `npx` (for MCP servers), and presence of `antigravity` CLI on PATH. Probe `~/.gemini/` to confirm Antigravity has been initialized at least once. Hard-fail with actionable messages if any are missing.
2. **Tag pin.** Read `UPSTREAM_TAG` from env (default `v2.0.0`). Clone `--depth 1 --branch ${UPSTREAM_TAG}` into a tempdir; trap clean.
3. **Staging.** Apply §4.3 conversion to a staging dir, not the temp clone (keeps upstream pristine for diffing on re-runs).
4. **Atomic install of skills + assets.** Walk staging; for each `seo-*` skill, `rsync -a --delete` to `~/.gemini/antigravity/skills/seo-*/`. The `--delete` ensures stale files from a previous install of a removed-upstream skill are cleared.
5. **Workflows.** Render `seo.md` and per-subcommand `seo-<cmd>.md` from templates. Write to `~/.gemini/antigravity/workflows/` if §9 unknown #1 detection confirms it's read; else write to user's chosen workspace `.agents/workflows/`.
6. **MCP servers.** For each of the 4 MCP extensions, prompt: `Install <ext>? [y/N]`. On y, prompt for credentials, run `lib/mcp_install.py` to merge into `~/.gemini/config/mcp_config.json`.
7. **Script-only extensions.** Same prompt loop for the other 4. On y, prompt for credentials (where applicable), write to `~/.gemini/antigravity/skills/seo/.env`. For Unlighthouse: pre-warm `unlighthouse-cli` via `npx`.
8. **Hooks.** Merge translated `hooks.json` into Antigravity's global hooks file. Smoke-test the validator script standalone.
9. **Venv + deps.** Create venv at `~/.gemini/antigravity/skills/seo/.venv/`. `pip install -r requirements.txt`. Optionally `playwright install chromium`.
10. **Verification pass.** Run `lib/portability_check.py` (copy of upstream's lint, retargeted at the install paths) — must return zero errors. Print summary: N skills installed, M workflows registered, K MCP servers configured, hook validator green.
11. **Final message.** Print exact commands to verify: `antigravity` → `/seo audit https://example.com`.

### 6.1 Idempotency invariants

- Re-running `install.sh` with the same `UPSTREAM_TAG` is a no-op for unchanged files (verified by hash compare in rsync mode).
- Re-running with a bumped tag upgrades skills/agents/scripts in place. Stale skills removed upstream are also removed locally (via `rsync --delete`).
- `mcp_config.json` merges only touch the specific server keys this installer owns. Other users' entries are preserved.
- `.env` merges are line-oriented: only keys this installer is responsible for are overwritten.

### 6.2 Failure modes the installer handles explicitly

| Failure | Behavior |
|---|---|
| Antigravity not on PATH | Hard-fail at preflight with install URL |
| Python < 3.10 | Hard-fail at preflight with upgrade hint |
| Clone fails (network) | Hard-fail; nothing partially written (we haven't touched install paths yet) |
| MCP server install: API key empty | Skip that extension, continue with the rest, surface in final summary |
| MCP server install: write fails mid-merge | Atomic temp+rename guarantees no partial write |
| Venv creation fails | Print exact `pip install --user` command; continue (skills still install, just no auto-deps) |
| Playwright browser install fails | Warn, mark `seo-visual` as degraded in summary, continue |
| Existing user-owned files in install paths | Detect via hash diff; if user-modified, copy to `.backup-<ts>` next to original before overwriting |

---

## 7. Uninstall flow (`uninstall.sh`)

1. **Snapshot** what's about to be removed; write to `~/.gemini/antigravity/.antigravity-seo-uninstall-manifest-<ts>.json` so the user can recover.
2. Remove `~/.gemini/antigravity/skills/seo*` directories.
3. Remove `~/.gemini/antigravity/workflows/seo.md` and `seo-*.md`.
4. Remove `~/.gemini/antigravity/skills/seo/.env` (with explicit confirmation since it has credentials).
5. Surgically remove the installer-owned entries from `~/.gemini/config/mcp_config.json` (server names: `firecrawl-mcp`, `dataforseo`, `nanobanana-mcp`, `ahrefs`). Leave other entries intact.
6. Surgically remove the installer-owned entries from Antigravity's global hooks file.
7. Remove the venv directory.
8. Leave the cloned upstream temp dir untouched (it was always temp).
9. Print summary with snapshot path.

---

## 8. Testing & verification

### 8.1 Unit tests (`tests/test_*.py`)

- `test_convert.py`: feed sample upstream skills/agents through `convert.py`; assert frontmatter normalization, path rewriting, name-collision suffixing.
- `test_mcp_install.py`: start from a known `mcp_config.json` (existing user entries), run each extension installer, assert: target entry present, other entries preserved, file is valid JSON, atomic temp file cleaned up.
- `test_workflow_dispatch.py`: render `seo.md` template with various installed-skill sets; assert subcommand list matches.
- `test_portability.py`: import upstream `portability_check.py` and run against the installed tree. Zero errors required.

### 8.2 Smoke test (`tests/test_smoke.sh`)

End-to-end in a hermetic sandbox (override `GEMINI_HOME=$TMP/.gemini`):

1. Run `install.sh --noninteractive --skip-extensions` (new flags for tests).
2. Assert all 25 skill dirs and 18 agent-derived skills exist.
3. Assert `seo.md` workflow renders and contains all subcommands.
4. Run `antigravity --dry-run /seo audit https://example.com` (or equivalent CLI dry-run mode; verify available in §9 unknown #3).
5. Assert exit zero.
6. Run `uninstall.sh --noninteractive`.
7. Assert no residue.

### 8.3 Manual verification checklist (user-driven)

- [ ] `antigravity` starts and lists `/seo` in the slash command menu
- [ ] `/seo audit https://en.wikipedia.org/wiki/Search_engine_optimization` produces a report file
- [ ] `/seo page <url>` returns single-page analysis
- [ ] `/seo schema <url>` detects + validates schema
- [ ] `/seo firecrawl crawl <url>` (if Firecrawl installed) returns crawl results
- [ ] `/seo dataforseo serp <kw>` (if DataForSEO installed) returns SERP data
- [ ] Editing a file with JSON-LD triggers the validate-schema hook
- [ ] Antigravity desktop app shows the same skills under its skills picker (free coverage, but verify)

---

## 9. Known unknowns (to resolve during implementation, recorded in `_research/notes.md`)

1. **Global vs workspace workflows path.** Confirmed for skills (`~/.gemini/antigravity/skills/`), not confirmed for workflows. Verification: install one dummy workflow at `~/.gemini/antigravity/workflows/hello.md`, start `antigravity`, see if `/hello` appears. If no, fall back to workspace install path. Resolution required before §6 step 5.
2. **Antigravity hooks file path + variables.** Two related unknowns answered by the same probe: (a) where Antigravity reads its global hooks JSON (candidates: `~/.gemini/antigravity/hooks.json`, `~/.gemini/config/hooks.json`); (b) what variable name Antigravity exposes for the edited file path (Claude Code's `$FILE_PATH` may not exist). Resolution: write a hook to each candidate path with a body that logs `env` to a temp file, edit any file, see which path fires and what variables are present. Update §5.6 install logic and `validate-schema.py` invocation accordingly.
3. **Antigravity CLI dry-run / non-interactive mode.** Needed for `tests/test_smoke.sh`. If unavailable, smoke test falls back to "install completes, skill files present, workflow file present" — without running the model.
4. **Workflow argument handling.** Whether `/seo audit https://example.com` correctly passes `audit https://example.com` as one positional argument to the workflow body, or splits, or is parsed as separate. Resolution: ship a stub workflow that logs `args`, observe behavior, adjust dispatcher template if needed.
5. **Antigravity YAML strictness.** Whether the upstream frontmatter keys we keep (`metadata.*`, `model`, `tools`) parse cleanly. Resolution: install one skill, attempt invocation, check error log; on failure, expand the §4.3 frontmatter normalize pass.
6. **`seranking` extension MCP shape.** Not all extension `install.sh` files cleanly expose their config; some may use `~/.claude/settings.json` `env` for scripts. Resolution: read full `extensions/seranking/install.sh` during implementation.

Each unknown has a concrete verification step. None block design approval.

---

## 10. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Antigravity changes its skill/workflow format mid-port | low (recently launched at I/O 2026) | high | Pin to Antigravity CLI version in README; preflight check warns on version drift |
| Subagent sequential execution makes `/seo audit` significantly slower than Claude Code parallel fan-out | medium | medium | Document expected runtime in README; consider future enhancement to use desktop multi-agent orchestration once a workflow-level API for it exists |
| `mcp_config.json` merge corrupts user's existing entries | low | high | Atomic temp+rename; pre-merge JSON parse validation; backup before write |
| `.env` file leaks credentials via `chmod` default | low | high | Installer enforces `chmod 600` on `.env`; never logs values |
| Upstream claude-seo introduces Claude-Code-only features (e.g. new `compatibility` frontmatter values) in a future tag | medium | low | Conversion warns on unknown keys, doesn't fail; we update conversion table on tag bump |
| User runs installer in CI / non-interactive shell and prompts hang | medium | medium | `--noninteractive` mode skips all extension prompts (base install only); `--with-extensions firecrawl,dataforseo,...` for scripted full install |

---

## 11. File manifest (what we are creating)

```
antigravity-seo-port/
├── README.md
├── install.sh
├── uninstall.sh
├── lib/
│   ├── __init__.py
│   ├── convert.py
│   ├── mcp_install.py
│   ├── env_install.py
│   ├── workflow_install.py
│   └── portability_check.py    (copy of upstream, retargeted)
├── templates/
│   ├── seo-workflow.md.tmpl
│   ├── seo-subcmd-workflow.md.tmpl
│   ├── hooks.json.tmpl
│   └── dotenv-shim.py
├── tests/
│   ├── test_convert.py
│   ├── test_mcp_install.py
│   ├── test_workflow_dispatch.py
│   ├── test_portability.py
│   └── test_smoke.sh
└── _research/
    └── notes.md                (populated during impl as §9 unknowns resolve)
```

No changes to upstream claude-seo. Nothing touched in `~/.claude/`.

---

## 12. Success criteria

The port is **done** when all of the following hold:

1. `install.sh` completes cleanly on a Mac with Antigravity CLI installed and Python 3.10+ — no manual file editing required.
2. After `antigravity` is started, `/seo` appears in the slash command menu, and `/seo audit <url>` produces a `FULL-AUDIT-REPORT.md` and an `ACTION-PLAN.md` matching the Claude Code version's shape.
3. All 25 skills are auto-discoverable (Antigravity loads them by description match).
4. All 18 subagent-derived skills are auto-discoverable.
5. All 4 MCP servers (Firecrawl, DataForSEO, Banana, Ahrefs) are configured in `mcp_config.json` and reachable from Antigravity tool calls.
6. All 4 script-only extensions work (Bing IndexNow submission succeeds; Profound API call returns; SE Ranking script runs; Unlighthouse generates a report).
7. Editing a file containing JSON-LD fires the validate-schema hook.
8. `uninstall.sh` removes everything cleanly and the snapshot manifest is recoverable.
9. `tests/test_smoke.sh` passes in CI (GitHub Actions Mac runner).
10. `portability_check.py` reports zero errors on the installed tree.

---

## 13. Out of scope (explicit)

- Plugin packaging via Antigravity's `plugin.json` manifest (deferred until the manifest schema is publicly nailed down; tracked separately).
- Antigravity marketplace submission.
- Multi-agent parallel orchestration for `/seo audit` via Antigravity desktop orchestrator.
- Windows installer (PowerShell port) — Mac/Linux only for v1.
- Auto-update mechanism — user re-runs `install.sh` with a new `UPSTREAM_TAG` manually.
- Test coverage for every individual `/seo` subcommand against live external APIs (only smoke-level coverage; full E2E would require real API keys in CI).
