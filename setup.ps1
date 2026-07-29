# =============================================================================
# GameDev Toolkit MCP - Setup Script (Windows PowerShell)
# =============================================================================
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConfigOut = Join-Path $RepoRoot "mcp_config.json"

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Info { param($msg) Write-Host "`n$msg" -ForegroundColor Cyan }

Info "=== GameDev Toolkit MCP Setup (Windows) ==="

# ---- Check prerequisites ----------------------------------------------------

Info "Checking prerequisites..."

function Check-Command {
    param($name, $hint)
    if (Get-Command $name -ErrorAction SilentlyContinue) {
        Ok "$name found"
    } else {
        Warn "$name not found - $hint"
    }
}

Check-Command "python"  "Install from https://python.org (3.12+ required)"
Check-Command "uv"      "Install with: winget install astral-sh.uv  OR  pip install uv"
Check-Command "node"    "Install from https://nodejs.org (18+ required)"
Check-Command "npm"     "Comes with Node.js"

try {
    $PyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $Parts = $PyVer.Split(".")
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
    $NodeVer = (node --version).TrimStart("v")
    $NodeMajor = [int]($NodeVer.Split(".")[0])
    if ($NodeMajor -ge 18) {
        Ok "Node.js v$NodeVer"
    } else {
        Warn "Node.js v$NodeVer found but 18+ is required"
    }
} catch {
    Warn "Could not determine Node.js version"
}

# ---- Aseprite MCP -----------------------------------------------------------

Info "Setting up the aseprite server..."

Push-Location (Join-Path $RepoRoot "serversseprite")

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    uv sync
    Ok "aseprite server dependencies installed (uv)"
} else {
    Warn "uv not found, falling back to pip"
    python -m pip install -r requirements.txt
    Ok "aseprite server dependencies installed (pip)"
}

Pop-Location

# ---- Godot MCP server -------------------------------------------------------

Info "Building the godot-mcp server..."

Push-Location (Join-Path $RepoRoot "servers\godot\server")
npm install
Ok "npm packages installed"
npm run build
Ok "TypeScript compiled"
Pop-Location

# ---- Detect Aseprite path ---------------------------------------------------

Info "Looking for Aseprite..."

$AsepriteExe = $null
$Candidates = @(
    "C:\Program Files\Aseprite\Aseprite.exe",
    "C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe",
    "$env:LOCALAPPDATA\Programs\Aseprite\Aseprite.exe",
    "D:\Games\Steam\steamapps\common\Aseprite\Aseprite.exe",
    "D:\Program Files\Aseprite\Aseprite.exe"
)

foreach ($c in $Candidates) {
    if (Test-Path $c) {
        $AsepriteExe = $c
        Ok "Aseprite found: $c"
        break
    }
}

if (-not $AsepriteExe) {
    try {
        $reg = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*" |
               Where-Object { $_.DisplayName -like "*Aseprite*" } |
               Select-Object -First 1
        if ($reg -and $reg.InstallLocation) {
            $candidate = Join-Path $reg.InstallLocation "Aseprite.exe"
            if (Test-Path $candidate) {
                $AsepriteExe = $candidate
                Ok "Aseprite found via registry: $candidate"
            }
        }
    } catch {}
}

if (-not $AsepriteExe) {
    Warn "Aseprite not found automatically. Common locations:"
    Write-Host "    Steam:   C:\Program Files (x86)\Steam\steamapps\common\Aseprite\Aseprite.exe"
    Write-Host "    Direct:  C:\Program Files\Aseprite\Aseprite.exe"
    $AsepriteExe = "C:\\path\\to\\Aseprite.exe"
}

# ---- Generate mcp_config.json -----------------------------------------------

Info "Generating mcp_config.json..."

$AsepriteMcpDir  = (Join-Path $RepoRoot "serversseprite") -replace '\\', '/'
$GodotServerJs   = (Join-Path $RepoRoot "servers\godot\server\dist\index.js") -replace '\\', '/'
$AsepriteExeJson = $AsepriteExe -replace '\\', '/'

if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    $AsepCmd  = "uv"
    $AsepArgs = "[`"--directory`", `"$AsepriteMcpDir`", `"run`", `"-m`", `"aseprite_mcp`"]"
} else {
    $AsepCmd  = "python"
    $AsepArgs = "[`"-m`", `"aseprite_mcp`"]"
}

$Config = @"
{
  "mcpServers": {
    "aseprite": {
      "command": "$AsepCmd",
      "args": $AsepArgs,
      "cwd": "$AsepriteMcpDir",
      "env": {
        "ASEPRITE_PATH": "$AsepriteExeJson"
      }
    },
    "godot-mcp": {
      "command": "node",
      "args": ["$GodotServerJs"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
"@

$Config | Out-File -FilePath $ConfigOut -Encoding UTF8
Ok "Config written to: $ConfigOut"

# ---- Final instructions -----------------------------------------------------

Info "=== Setup Complete ===`n"
Write-Host "Next steps:"
Write-Host ""
Write-Host "  1. Copy or merge mcp_config.json into your Claude config location:"
Write-Host "       $env:APPDATA\Claude\claude_desktop_config.json"
Write-Host ""
Write-Host "  2. Open your Godot project in the Godot editor."
Write-Host "       Copy addons\godot_mcp\ to your project and enable the plugin:"
Write-Host "       Project -> Project Settings -> Plugins -> Godot MCP -> Enable"
Write-Host ""
Write-Host "  3. Restart Claude Desktop (or reload MCP config in Claude Code)."
Write-Host ""

if ($AsepriteExe -eq "C:\\path\\to\\Aseprite.exe") {
    Warn "Remember to update ASEPRITE_PATH in mcp_config.json with the real Aseprite path."
}
