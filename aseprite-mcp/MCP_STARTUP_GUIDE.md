# Aseprite MCP Startup Guide

This guide is intentionally generic. It does not include any machine-specific paths.

## Start from the monorepo setup

From the repo root:

### Windows

```powershell
.\setup.ps1
```

### macOS / Linux

```bash
./setup.sh
```

That generates `mcp_config.json` with the correct local absolute paths for the current machine.

## Run `aseprite-mcp` directly

### With `uv`

```bash
cd /absolute/path/to/aseprite-mcp
export ASEPRITE_PATH=/absolute/path/to/aseprite
uv run -m aseprite_mcp
```

### With Python

```bash
cd /absolute/path/to/aseprite-mcp
export ASEPRITE_PATH=/absolute/path/to/aseprite
python -m aseprite_mcp
```

Windows PowerShell example:

```powershell
cd C:\absolute\path\to\aseprite-mcp
$env:ASEPRITE_PATH = "C:\absolute\path\to\Aseprite.exe"
uv run -m aseprite_mcp
```

## Claude Desktop example

Use your real absolute paths:

```json
{
  "mcpServers": {
    "aseprite": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/aseprite-mcp",
        "run",
        "-m",
        "aseprite_mcp"
      ],
      "cwd": "/absolute/path/to/aseprite-mcp",
      "env": {
        "ASEPRITE_PATH": "/absolute/path/to/aseprite"
      }
    }
  }
}
```

Claude Desktop config locations:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

## Quick checks

- `ASEPRITE_PATH` points to a real executable.
- `"/path/to/aseprite" --batch --version` works.
- Dependencies are installed.
- The config file uses only your current local paths.
