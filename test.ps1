# =============================================================================
# Godot x Aseprite MCP — Test Connection Script
# =============================================================================

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Ok   { param($msg) Write-Host "[OK]   $msg" -ForegroundColor Green }
function Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Err  { param($msg) Write-Host "[ERR]  $msg" -ForegroundColor Red }
function Info { param($msg) Write-Host "`n$msg" -ForegroundColor Cyan }

Info "=== Godot x Aseprite MCP Test ==="

# =============================================================================
# Test 1: Aseprite MCP
# =============================================================================

Info "[1/4] Testing aseprite-mcp..."

Push-Location (Join-Path $RepoRoot "aseprite-mcp")

try {
    # Check venv
    if (Test-Path ".venv") {
        Ok "Python venv exists"
    } else {
        Warn "venv missing, creating..."
        uv sync
    }

    # Check imports
    $TestResult = python -c "import sys; sys.path.insert(0, '.'); from aseprite_mcp import mcp; print('OK')" 2>&1
    if ($TestResult -match "OK") {
        Ok "FastMCP server loads correctly"
    } else {
        Warn "Import test: $TestResult"
    }

    # Check ASEPRITE_PATH
    $AsepritePath = $env:ASEPRITE_PATH
    if ($AsepritePath) {
        if (Test-Path $AsepritePath) {
            Ok "ASEPRITE_PATH set: $AsepritePath"
        } else {
            Warn "ASEPRITE_PATH set but file not found: $AsepritePath"
        }
    } else {
        Warn "ASEPRITE_PATH not set (will be auto-detected or need config)"
    }

    # List available tools
    $ToolsResult = python -c "from aseprite_mcp.tools import *; import aseprite_mcp; print('Tools loaded')" 2>&1
    if ($ToolsResult -match "Tools loaded") {
        Ok "Tool modules loadable"
    } else {
        Warn "Tool modules: $ToolsResult"
    }

} catch {
    Warn "aseprite-mcp test error: $_"
}

Pop-Location

# =============================================================================
# Test 2: Godot MCP Server
# =============================================================================

Info "[2/4] Testing Godot-MCP server..."

Push-Location (Join-Path $RepoRoot "Godot-MCP\server")

try {
    # Check dist
    if (Test-Path "dist\index.js") {
        Ok "TypeScript compiled (dist/index.js exists)"
    } else {
        Warn "dist missing, building..."
        npm run build
    }

    # Check node_modules
    if (Test-Path "node_modules") {
        Ok "Node dependencies installed"
    } else {
        Warn "node_modules missing, installing..."
        npm install
    }

    # Test server start (quick check)
    $StartTest = node -e "console.log('Node.js OK')" 2>&1
    if ($StartTest -match "Node.js OK") {
        Ok "Node.js can execute"
    } else {
        Warn "Node.js test: $StartTest"
    }

    # Check port configuration
    $PortConfig = Select-String -Path "..\addons\godot_mcp\mcp_server.gd" -Pattern "var port :=" | Select-Object -First 1
    if ($PortConfig) {
        $PortLine = $PortConfig.Line
        if ($PortLine -match "9080") {
            Ok "Port configured: 9080 (correct)"
        } else {
            Warn "Port in mcp_server.gd: $PortLine (check consistency)"
        }
    }

} catch {
    Warn "Godot-MCP server test error: $_"
}

Pop-Location

# =============================================================================
# Test 3: Godot Plugin Structure
# =============================================================================

Info "[3/4] Testing Godot plugin structure..."

$PluginDir = Join-Path $RepoRoot "Godot-MCP\addons\godot_mcp"

$RequiredFiles = @(
    "plugin.cfg",
    "mcp_server.gd",
    "command_handler.gd",
    "websocket_server.gd"
)

foreach ($file in $RequiredFiles) {
    $Path = Join-Path $PluginDir $file
    if (Test-Path $Path) {
        Ok "Plugin file: $file"
    } else {
        Warn "Missing: $file"
    }
}

# Check command modules
$CommandsDir = Join-Path $PluginDir "commands"
$CommandsCount = (Get-ChildItem -Path $CommandsDir -Filter "*.gd").Count
Ok "Command modules: $CommandsCount"

if ($CommandsCount -ge 20) {
    Ok "All 20 command modules present"
} else {
    Warn "Expected 20 command modules, found $CommandsCount"
}

# =============================================================================
# Test 4: Configuration
# =============================================================================

Info "[4/4] Testing MCP configuration..."

$ConfigFile = Join-Path $RepoRoot "mcp_config.json"

if (Test-Path $ConfigFile) {
    Ok "mcp_config.json exists"
    try {
        $Config = Get-Content $ConfigFile -Raw | ConvertFrom-Json
        if ($Config.mcpServers.aseprite) {
            Ok "aseprite server configured"
            if ($Config.mcpServers.aseprite.env.ASEPRITE_PATH) {
                Ok "  ASEPRITE_PATH set in config"
            }
        }
        if ($Config.mcpServers."godot-mcp") {
            Ok "godot-mcp server configured"
        }
    } catch {
        Warn "Config parsing error: $_"
    }
} else {
    Warn "mcp_config.json not found (run setup.ps1 to generate)"
}

# =============================================================================
# Summary
# =============================================================================

Info "`n=== Test Summary ==="
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "1. For ASEPRITE_PATH issues:"
Write-Host "   - Edit mcp_config.json and update ASEPRITE_PATH"
Write-Host "   - Or set environment variable via System Properties"
Write-Host ""
Write-Host "2. For Godot connection:"
Write-Host "   - Copy addons/godot_mcp/ to your Godot project"
Write-Host "   - Open Godot editor"
Write-Host "   - Project - Settings - Plugins - Enable Godot MCP"
Write-Host "   - Check bottom panel for MCP tab showing Connected"
Write-Host ""
Write-Host "3. For Claude Desktop:"
Write-Host "   - Copy mcp_config.json to Claude config folder"
Write-Host "   - Restart Claude Desktop"
Write-Host ""