# Antigravity Port Research Notes

Field notes from probing unknowns in `docs/specs/2026-05-25-antigravity-seo-port-design.md` §9.

| Unknown # | Question | Resolution | Verified by |
|---|---|---|---|
| 1 | Global workflows path | (pending Task 1.1) | |
| 2 | Hooks file path + variables | (pending Task 1.2) | |
| 3 | CLI dry-run mode | (pending Task 1.3) | |
| 4 | Workflow argument handling | (pending Task 1.4) | |
| 5 | YAML strictness | (pending Task 1.5) | |
| 6 | seranking install.sh shape | Script-only. Prompts for `SERANKING_API_KEY` at runtime, writes it to `env.SERANKING_API_KEY` in settings.json via embedded Python script. Copies `seo-seranking/SKILL.md` to `~/.claude/skills/seo-seranking/`. No MCP server involved—purely skill-based. | Task 1.6 (read upstream install.sh) |
