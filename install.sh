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
