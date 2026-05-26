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
EXT_ROOT="${HOME}/.gemini/antigravity-seo-port"

[ -f "${EXT_ROOT}/gemini-extension.json" ] || { echo "FAIL: gemini-extension.json missing"; exit 1; }
echo "PASS: gemini-extension.json present"

[ -f "${EXT_ROOT}/GEMINI.md" ] || { echo "FAIL: GEMINI.md missing"; exit 1; }
echo "PASS: GEMINI.md present"

SKILL_COUNT="$(find "${EXT_ROOT}/skills" -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ')"
[ "${SKILL_COUNT}" -ge 25 ] || { echo "FAIL: expected ≥25 skills, got ${SKILL_COUNT}"; exit 1; }
echo "PASS: ${SKILL_COUNT} skills installed"

[ -L "${HOME}/.gemini/skills/seo-audit" ] || { echo "FAIL: ~/.gemini/skills/seo-audit symlink missing"; exit 1; }
echo "PASS: shared skills symlink present"

[ -f "${EXT_ROOT}/hooks/hooks.json" ] || { echo "FAIL: hooks.json missing"; exit 1; }
echo "PASS: hooks.json present"

[ -f "${EXT_ROOT}/.venv/bin/python" ] || { echo "FAIL: venv missing"; exit 1; }
echo "PASS: venv installed"

# Uninstall
bash uninstall.sh --noninteractive

[ ! -d "${EXT_ROOT}" ] || { echo "FAIL: extension dir still present after uninstall"; exit 1; }
echo "PASS: clean uninstall"

[ ! -L "${HOME}/.gemini/skills/seo-audit" ] || { echo "FAIL: shared skills symlink still present after uninstall"; exit 1; }
echo "PASS: shared skills symlinks cleaned up"

echo ""
echo "════════════════════════════════════════"
echo "║   Smoke test: ALL PASSED              ║"
echo "════════════════════════════════════════"
