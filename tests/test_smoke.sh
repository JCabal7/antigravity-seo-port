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
