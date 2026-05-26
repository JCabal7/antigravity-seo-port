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

install_workflows() {
  log "generating /seo dispatcher + per-subcommand workflows ..."
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

install_mcp_extensions() {
  log "MCP-server extensions ..."

  if should_install_extension firecrawl; then
    read -rsp "  Firecrawl API key: " FIRECRAWL_API_KEY; echo
    if [ -z "${FIRECRAWL_API_KEY}" ]; then
      warn "firecrawl: empty API key — skipping"
      EXTENSION_FAILURES+=("firecrawl (empty key)")
    else
      if python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "firecrawl",
    credentials={"FIRECRAWL_API_KEY": "${FIRECRAWL_API_KEY}"})
PY
      then
        ok "firecrawl installed"
      else
        warn "firecrawl install failed — skipping"
        EXTENSION_FAILURES+=("firecrawl")
      fi
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
         "${SEO_INSTALL}/extensions/dataforseo/field-config.json" 2>/dev/null || true
      if python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "dataforseo",
    credentials={"DATAFORSEO_USERNAME": "${DATAFORSEO_USERNAME}",
                 "DATAFORSEO_PASSWORD": "${DATAFORSEO_PASSWORD}"},
    extra_env={"FIELD_CONFIG_PATH": "${SEO_INSTALL}/extensions/dataforseo/field-config.json"})
PY
      then
        ok "dataforseo installed"
      else
        warn "dataforseo install failed — skipping"
        EXTENSION_FAILURES+=("dataforseo")
      fi
    fi
  fi

  if should_install_extension banana; then
    read -rsp "  Google AI (Gemini) API key: " GOOGLE_AI_API_KEY; echo
    if [ -z "${GOOGLE_AI_API_KEY}" ]; then
      warn "banana: empty API key — skipping"
      EXTENSION_FAILURES+=("banana (empty key)")
    else
      if python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "banana",
    credentials={"GOOGLE_AI_API_KEY": "${GOOGLE_AI_API_KEY}"})
PY
      then
        ok "banana installed"
      else
        warn "banana install failed — skipping"
        EXTENSION_FAILURES+=("banana")
      fi
    fi
  fi

  if should_install_extension ahrefs; then
    read -rsp "  Ahrefs API token: " AHREFS_API_TOKEN; echo
    if [ -z "${AHREFS_API_TOKEN}" ]; then
      warn "ahrefs: empty API token — skipping"
      EXTENSION_FAILURES+=("ahrefs (empty token)")
    else
      if python3 - <<PY
import sys; sys.path.insert(0, "${PORT_ROOT}")
from pathlib import Path
from lib import mcp_install
mcp_install.install_mcp_server(
    Path("${MCP_CONFIG}"), "ahrefs",
    credentials={"AHREFS_API_TOKEN": "${AHREFS_API_TOKEN}"})
PY
      then
        ok "ahrefs installed"
      else
        warn "ahrefs install failed — skipping"
        EXTENSION_FAILURES+=("ahrefs")
      fi
    fi
  fi
}

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

install_hooks() {
  log "installing schema-validation hook ..."
  mkdir -p "${SEO_INSTALL}/hooks"
  if [ -f "${TMP_DIR}/upstream/hooks/validate-schema.py" ]; then
    cp "${TMP_DIR}/upstream/hooks/validate-schema.py" "${SEO_INSTALL}/hooks/validate-schema.py"
    chmod +x "${SEO_INSTALL}/hooks/validate-schema.py"
  fi

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

  # Smoke-test the validator script standalone (only if venv exists)
  if [ -x "${SEO_INSTALL}/.venv/bin/python" ] && [ -f "${SEO_INSTALL}/hooks/validate-schema.py" ]; then
    echo '<script type="application/ld+json">{"@context":"https://schema.org"}</script>' > /tmp/.schema-probe.html
    if "${SEO_INSTALL}/.venv/bin/python" "${SEO_INSTALL}/hooks/validate-schema.py" /tmp/.schema-probe.html >/dev/null 2>&1; then
      ok "validator script smoke-tested"
    else
      warn "validator script smoke test failed (will retry post-venv)"
    fi
    rm -f /tmp/.schema-probe.html
  fi
}

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

preflight
clone_upstream
run_conversion
rsync_install
install_workflows
install_mcp_extensions
install_script_extensions
install_hooks
install_venv
echo "(portability check follows)"
