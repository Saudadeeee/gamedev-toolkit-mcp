#!/usr/bin/env bash
# =============================================================================
# GameDev Toolkit MCP - Setup Script (Linux / macOS)
# =============================================================================
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_OUT="$REPO_ROOT/mcp_config.json"

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
info() { echo -e "${BOLD}$1${NC}"; }

info "\n=== GameDev Toolkit MCP Setup ===\n"

# ---- Check prerequisites ----------------------------------------------------

info "Checking prerequisites..."

check_cmd() {
    if command -v "$1" &>/dev/null; then
        ok "$1 found: $(command -v "$1")"
    else
        warn "$1 not found - $2"
    fi
}

check_cmd python3 "Install from https://python.org (3.12+ required)"
check_cmd uv "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
check_cmd node "Install from https://nodejs.org (18+ required)"
check_cmd npm "Comes with Node.js"

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -gt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 12 ]; }; then
    ok "Python $PY_VER"
else
    warn "Python $PY_VER found but 3.12+ is required"
fi

NODE_VER=$(node --version 2>/dev/null | sed 's/v//' || echo "0")
NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
if [ "$NODE_MAJOR" -ge 18 ]; then
    ok "Node.js v$NODE_VER"
else
    warn "Node.js v$NODE_VER found but 18+ is required"
fi

echo ""

# ---- Aseprite MCP -----------------------------------------------------------

info "Setting up the aseprite server..."

cd "$REPO_ROOT/servers/aseprite"

if command -v uv &>/dev/null; then
    uv sync && ok "aseprite server dependencies installed (uv)"
else
    warn "uv not found, falling back to pip"
    python3 -m pip install -r requirements.txt && ok "aseprite server dependencies installed (pip)"
fi

echo ""

# ---- Godot MCP server -------------------------------------------------------

info "Building the godot-mcp server..."

cd "$REPO_ROOT/servers/godot/server"
npm install && ok "npm packages installed"
npm run build && ok "TypeScript compiled"

echo ""

# ---- Detect Aseprite path ---------------------------------------------------

info "Looking for Aseprite..."

ASEPRITE_PATH=""
CANDIDATES=(
    "/Applications/Aseprite.app/Contents/MacOS/aseprite"
    "$HOME/.local/share/Steam/steamapps/common/Aseprite/aseprite"
    "/usr/bin/aseprite"
    "/usr/local/bin/aseprite"
    "/opt/aseprite/aseprite"
)

for c in "${CANDIDATES[@]}"; do
    if [ -f "$c" ]; then
        ASEPRITE_PATH="$c"
        ok "Aseprite found: $c"
        break
    fi
done

if [ -z "$ASEPRITE_PATH" ]; then
    warn "Aseprite not found automatically."
    echo "    Common locations:"
    echo "      macOS: /Applications/Aseprite.app/Contents/MacOS/aseprite"
    echo "      Linux: /usr/bin/aseprite or ~/.local/share/Steam/steamapps/common/Aseprite/aseprite"
    ASEPRITE_PATH="/path/to/aseprite"
fi

echo ""

# ---- Generate mcp_config.json -----------------------------------------------

info "Generating mcp_config.json..."

ASEPRITE_MCP_DIR="$REPO_ROOT/servers/aseprite"
GODOT_SERVER_JS="$REPO_ROOT/servers/godot/server/dist/index.js"

if command -v uv &>/dev/null; then
    ASEPRITE_CMD="uv"
    ASEPRITE_ARGS="[\"--directory\", \"$ASEPRITE_MCP_DIR\", \"run\", \"-m\", \"aseprite_mcp\"]"
else
    ASEPRITE_CMD="python3"
    ASEPRITE_ARGS="[\"-m\", \"aseprite_mcp\"]"
fi

cat > "$CONFIG_OUT" <<EOF
{
  "mcpServers": {
    "aseprite": {
      "command": "$ASEPRITE_CMD",
      "args": $ASEPRITE_ARGS,
      "cwd": "$ASEPRITE_MCP_DIR",
      "env": {
        "ASEPRITE_PATH": "$ASEPRITE_PATH"
      }
    },
    "godot-mcp": {
      "command": "node",
      "args": ["$GODOT_SERVER_JS"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
EOF

ok "Config written to: $CONFIG_OUT"

echo ""

# ---- Final instructions -----------------------------------------------------

info "=== Setup Complete ===\n"
echo "Next steps:"
echo ""
echo "  1. Copy or merge mcp_config.json into your Claude config location:"
echo "       macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "       Linux: ~/.config/Claude/claude_desktop_config.json"
echo ""
echo "  2. Open your Godot project in the Godot editor."
echo "       Copy addons/godot_mcp/ to your project and enable the plugin:"
echo "       Project -> Project Settings -> Plugins -> Godot MCP -> Enable"
echo ""
echo "  3. Restart Claude Desktop (or reload the MCP config in Claude Code)."
echo ""
if [ "$ASEPRITE_PATH" = "/path/to/aseprite" ]; then
    warn "Remember to update ASEPRITE_PATH in mcp_config.json with the real path."
fi
