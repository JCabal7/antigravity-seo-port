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
