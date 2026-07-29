# =============================================================================
# GameDev Toolkit MCP - Setup (Windows PowerShell)
#
# Which servers exist, how each installs, and how each is configured all come
# from toolkit.json. This script only sequences the work -- it hardcodes no
# server list, so adding one to the registry is enough.
# =============================================================================
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Info { param($msg) Write-Host "`n$msg" -ForegroundColor Cyan }
function Fail { param($msg) Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }

# Join-Path rather than string literals: a literal "servers\aseprite" is one
# stray escape-interpreting layer away from becoming "servers<BEL>seprite",
# which is exactly how this script broke before.
$AsepriteDir = Join-Path (Join-Path $RepoRoot "servers") "aseprite"
$GodotServer = Join-Path (Join-Path (Join-Path $RepoRoot "servers") "godot") "server"

Info "=== GameDev Toolkit MCP Setup (Windows) ==="

# ---- Prerequisites ----------------------------------------------------------

Info "Checking prerequisites..."

function Check-Command {
    param($name, $hint)
    if (Get-Command $name -ErrorAction SilentlyContinue) {
        Ok "$name found"
        return $true
    }
    Warn "$name not found - $hint"
    return $false
}

$HasPython = Check-Command "python" "Install from https://python.org (3.12+ required)"
$HasUv     = Check-Command "uv"     "Install with: winget install astral-sh.uv  OR  pip install uv"
Check-Command "node" "Install from https://nodejs.org (18+ required)" | Out-Null
Check-Command "npm"  "Comes with Node.js"                             | Out-Null
Check-Command "git"  "Needed to update the vendored servers"               | Out-Null

if (-not $HasPython) { Fail "python is required to run the setup helpers." }

try {
    $PyVer   = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $Parts   = $PyVer.Split(".")
    $PyMajor = [int]$Parts[0]
    $PyMinor = [int]$Parts[1]
    if (($PyMajor -gt 3) -or (($PyMajor -eq 3) -and ($PyMinor -ge 12))) {
        Ok "Python $PyVer"
    } else {
        Warn "Python $PyVer found but 3.12+ is required"
    }
} catch {
    Warn "Could not determine Python version"
}

try {
    $NodeVer   = (node --version).TrimStart("v")
    $NodeMajor = [int]($NodeVer.Split(".")[0])
    if ($NodeMajor -ge 18) {
        Ok "Node.js v$NodeVer"
    } else {
        Warn "Node.js v$NodeVer found but 18+ is required"
    }
} catch {
    Warn "Could not determine Node.js version"
}

# ---- First-party servers ----------------------------------------------------

Info "Installing the aseprite server (servers\aseprite)..."

Push-Location $AsepriteDir
try {
    if ($HasUv) {
        uv sync
        Ok "dependencies installed (uv)"
    } else {
        Warn "uv not found, falling back to pip"
        python -m pip install -r requirements.txt
        Ok "dependencies installed (pip)"
    }
} finally {
    Pop-Location
}

Info "Building the godot-mcp server (servers\godot\server)..."

Push-Location $GodotServer
try {
    npm install
    Ok "npm packages installed"
    npm run build
    Ok "TypeScript compiled"
} finally {
    Pop-Location
}

# ---- Upstream servers -------------------------------------------------------

Info "Building the vendored servers' virtualenvs..."

# These exit non-zero when a server needs attention, which is a warning here,
# not a reason to abandon the rest of setup.
$ErrorActionPreference = "Continue"
python scripts\install_vendored.py
if ($LASTEXITCODE -ne 0) { Warn "some vendored servers need attention (see above)" }

# ---- MCP client config ------------------------------------------------------

Info "Generating mcp_config.json..."

python scripts\write_mcp_config.py
if ($LASTEXITCODE -ne 0) { Fail "could not generate mcp_config.json" }

# ---- Next steps -------------------------------------------------------------

Info "=== Setup Complete ==="

Write-Host @"

Next steps:

  1. Merge mcp_config.json into your MCP client's config:
       $env:APPDATA\Claude\claude_desktop_config.json

  2. Install the Godot plugin into your game project:
       python scripts\install_godot_plugin.py C:\path\to\your\godot\project
     Then enable it: Project > Project Settings > Plugins > Godot MCP

  3. Wire up Obsidian (needs the Local REST API community plugin):
       python scripts\configure_obsidian.py

  4. Restart your MCP client, then check everything at once:
       python scripts\verify_toolkit.py --quick

Applications that must be running for their server to answer: Godot (scene
tools only), Blockbench, Audacity, Obsidian. Aseprite does not.
"@
