#!/usr/bin/env bash
# antigravity-seo-port uninstaller.
#
# Removes everything installed by install.sh, surgically. Does NOT touch
# MCP servers or hooks installed by other projects.
set -euo pipefail

PORT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
INSTALL_ROOT="${HOME}/.gemini/antigravity-seo-port"
SEO_INSTALL="${INSTALL_ROOT}"
MCP_CONFIG="${HOME}/.gemini/antigravity-cli/mcp_config.json"
HOOKS_FILE="${INSTALL_ROOT}/hooks/hooks.json"
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
  manifest="${INSTALL_ROOT}.uninstall-manifest-${ts}.json"   # sibling of INSTALL_ROOT
  python3 - "${manifest}" "${INSTALL_ROOT}" <<'PY'
import json, sys
from pathlib import Path
manifest, install_root = sys.argv[1], Path(sys.argv[2])
data = {"skills": [], "exists": install_root.exists()}
skills = install_root / "skills"
if skills.exists():
    data["skills"] = sorted(p.name for p in skills.iterdir() if p.is_dir())
Path(manifest).parent.mkdir(parents=True, exist_ok=True)
Path(manifest).write_text(json.dumps(data, indent=2))
print(manifest)
PY
}

remove_extension() {
  if [ -d "${INSTALL_ROOT}" ]; then
    log "removing extension dir ${INSTALL_ROOT} ..."
    rm -rf "${INSTALL_ROOT}"
    ok "extension removed"
  else
    log "extension dir does not exist; nothing to remove"
  fi
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

remove_env_warning() {
  if [ -f "${ENV_FILE}" ]; then
    if ! confirm "Extension dir contains a .env with API credentials; remove?"; then
      echo "Aborted (extension not removed)."
      exit 0
    fi
  fi
}

printf "════════════════════════════════════════\n"
printf "║   antigravity-seo-port — Uninstaller  ║\n"
printf "════════════════════════════════════════\n\n"

if ! confirm "Proceed with uninstall?"; then
  echo "Aborted."
  exit 0
fi

remove_env_warning
manifest_path="$(snapshot)"
ok "snapshot saved: ${manifest_path}"

remove_extension
remove_mcp

printf "\nDone. Snapshot: %s\n" "${manifest_path}"
