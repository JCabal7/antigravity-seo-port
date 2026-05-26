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
3. Installs into `~/.gemini/antigravity-seo-port/` as a Gemini extension (auto-discovered by Antigravity CLI and IDE)
4. Creates an extension manifest (`gemini-extension.json`) + context file (`GEMINI.md`)
5. Prompts to install each of 8 optional extensions:
   - **MCP-server extensions** (added to `~/.gemini/antigravity-cli/mcp_config.json`): Firecrawl, DataForSEO, Banana (image gen), Ahrefs
   - **Script-only extensions** (credentials → `~/.gemini/antigravity-seo-port/.env`): Bing Webmaster + IndexNow, Profound, SE Ranking, Unlighthouse
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

After install, open Antigravity (CLI or IDE) — skills are auto-discovered.

In the CLI, ask the agent things like:

- "Use the seo-audit skill on https://example.com"
- "Run seo-page on https://example.com/about"
- "Use seo-schema to check https://example.com"

The full list of installed skills:

```bash
ls ~/.gemini/antigravity-seo-port/skills/
```

## What gets installed where

- Extension files: `~/.gemini/antigravity-seo-port/` (manifest, GEMINI.md, skills, hooks, scripts, venv, .env)
- MCP server entries: merged into `~/.gemini/antigravity-cli/mcp_config.json` (CLI install — does not touch IDE)

## Uninstall

```bash
bash uninstall.sh
```

Removes the entire `~/.gemini/antigravity-seo-port/` extension dir and any owned MCP server entries. A snapshot manifest is saved as a sibling of the extension dir (`~/.gemini/antigravity-seo-port.uninstall-manifest-<timestamp>.json`) for recovery.

## Behavioral differences vs. Claude Code

- **No `/seo` slash command.** Claude Code had a single `/seo <subcommand>` dispatcher. Antigravity discovers skills directly, so you invoke each skill by name (`seo-audit`, `seo-page`, etc.) via natural language to the agent or via the skill picker.
- **Subagent fan-out is sequential.** Claude Code's seo-audit dispatched up to 15 specialist subagents in parallel; on Antigravity the orchestrator loads them sequentially (Antigravity CLI's workflow model doesn't expose parallel subagent dispatch). Wall time is longer.

## Updating

```bash
cd antigravity-seo-port
git pull
bash install.sh --upstream-tag <new-tag>
```

Rsync's `--delete` ensures stale skills removed upstream are also removed locally.

## License

Installer: MIT. Upstream claude-seo: MIT (see https://github.com/AgriciDaniel/claude-seo/blob/main/LICENSE).
