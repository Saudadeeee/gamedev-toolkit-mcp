#!/usr/bin/env bash
# =============================================================================
# GameDev Toolkit MCP - Setup (Linux / macOS)
#
# Which servers exist, how each installs, and how each is configured all come
# from toolkit.json. This script only sequences the work -- it hardcodes no
# server list, so adding one to the registry is enough.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
info() { echo -e "\n${BOLD}$1${NC}"; }

info "=== GameDev Toolkit MCP Setup ==="

# ---- Prerequisites ----------------------------------------------------------

info "Checking prerequisites..."

check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "$1 found: $(command -v "$1")"
    else
        warn "$1 not found - $2"
    fi
}

check_cmd python3 "Install from https://python.org (3.12+ required)"
check_cmd uv      "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
check_cmd node    "Install from https://nodejs.org (18+ required)"
check_cmd npm     "Comes with Node.js"
check_cmd git     "Needed to update the vendored servers"

command -v python3 &>/dev/null || fail "python3 is required to run the setup helpers."

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=${PY_VER%%.*}
PY_MINOR=${PY_VER##*.}
if [ "$PY_MAJOR" -gt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 12 ]; }; then
    ok "Python $PY_VER"
else
    warn "Python $PY_VER found but 3.12+ is required"
fi

if command -v node &>/dev/null; then
    NODE_VER=$(node --version | sed 's/v//')
    if [ "${NODE_VER%%.*}" -ge 18 ]; then
        ok "Node.js v$NODE_VER"
    else
        warn "Node.js v$NODE_VER found but 18+ is required"
    fi
fi

# ---- First-party servers ----------------------------------------------------

info "Installing the aseprite server (servers/aseprite)..."

if command -v uv &>/dev/null; then
    (cd "$REPO_ROOT/servers/aseprite" && uv sync) && ok "dependencies installed (uv)"
else
    warn "uv not found, falling back to pip"
    (cd "$REPO_ROOT/servers/aseprite" && python3 -m pip install -r requirements.txt) \
        && ok "dependencies installed (pip)"
fi

info "Building the godot-mcp server (servers/godot/server)..."

(cd "$REPO_ROOT/servers/godot/server" && npm install) && ok "npm packages installed"
(cd "$REPO_ROOT/servers/godot/server" && npm run build) && ok "TypeScript compiled"

# ---- Upstream servers -------------------------------------------------------

info "Building the vendored servers' virtualenvs..."

python3 scripts/install_vendored.py || warn "some vendored servers need attention (see above)"

# ---- MCP client config ------------------------------------------------------

info "Generating mcp_config.json..."

python3 scripts/write_mcp_config.py

# ---- Next steps -------------------------------------------------------------

info "=== Setup Complete ==="
cat <<'EOF'

Next steps:

  1. Merge mcp_config.json into your MCP client's config:
       macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
       Linux: ~/.config/Claude/claude_desktop_config.json

  2. Install the Godot plugin into your game project:
       python3 scripts/install_godot_plugin.py /path/to/your/godot/project
     Then enable it: Project > Project Settings > Plugins > Godot MCP

  3. Wire up Obsidian (needs the Local REST API community plugin):
       python3 scripts/configure_obsidian.py

  4. Restart your MCP client, then check everything at once:
       python3 scripts/verify_toolkit.py --quick

Applications that must be running for their server to answer: Godot (scene
tools only), Blockbench, Audacity, Obsidian. Aseprite does not.
EOF
