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
