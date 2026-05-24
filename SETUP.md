# Setup Guide

Complete installation guide for `Godot x Aseprite MCP` on Windows, macOS, and Linux.

## Requirements

| Tool | Version | Purpose |
|---|---|---|
| [Python](https://python.org) | 3.12+ | Runs `aseprite-mcp` |
| [uv](https://github.com/astral-sh/uv) | latest | Recommended Python package manager |
| [Node.js](https://nodejs.org) | 18+ | Runs `Godot-MCP/server` |
| [Godot Engine](https://godotengine.org) | 4.x | Godot editor and plugin host |
| [Aseprite](https://aseprite.org) | 1.3+ | Pixel art tool with `--batch` support |

`Aseprite` can be the paid build or a source build, as long as CLI batch mode works.

## Quick Setup

### Windows

```powershell
git clone https://github.com/Saudadeeee/Godot-x-Aseprite-MCP-all.git
cd "Godot-x-Aseprite-MCP-all"
.\setup.ps1
```

### macOS / Linux

```bash
git clone https://github.com/Saudadeeee/Godot-x-Aseprite-MCP-all.git
cd "Godot-x-Aseprite-MCP-all"
chmod +x setup.sh
./setup.sh
```

The setup script does five things:

1. Checks required tools.
2. Installs `aseprite-mcp` dependencies.
3. Builds `Godot-MCP/server/dist/index.js`.
4. Tries to detect the local Aseprite executable.
5. Writes `mcp_config.json` in the repo root.

`mcp_config.json` contains absolute local paths and is already ignored by Git.

## Manual Setup

### 1. Clone the repository

```bash
git clone https://github.com/Saudadeeee/Godot-x-Aseprite-MCP-all.git
cd "Godot-x-Aseprite-MCP-all"
```

### 2. Install `aseprite-mcp`

Recommended:

```bash
cd aseprite-mcp
uv sync
```

Fallback if `uv` is unavailable:

```bash
cd aseprite-mcp
python -m pip install -r requirements.txt
```

### 3. Build `Godot-MCP`

```bash
cd ../Godot-MCP/server
npm install
npm run build
```

This generates `Godot-MCP/server/dist/index.js`.

### 4. Enable the Godot plugin

1. Open your Godot 4 project in the editor.
2. Copy `Godot-MCP/addons/godot_mcp/` into the project's `addons/` folder.
3. Open `Project -> Project Settings -> Plugins`.
4. Enable `Godot MCP`.
5. Confirm the plugin starts its WebSocket server on port `9080`.

To use multiple Godot projects, copy the same `addons/godot_mcp/` folder into each one.

### 5. Configure your MCP client

You can either:

1. Run a setup script and copy the generated `mcp_config.json`.
2. Start from the repo template `claude_desktop_config.json`.
3. Write the config manually.

#### Claude Desktop config locations

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

#### Example config

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
    },
    "godot-mcp": {
      "command": "node",
      "args": [
        "/absolute/path/to/Godot-MCP/server/dist/index.js"
      ],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

`cwd` on the `aseprite` entry keeps the fallback `python -m aseprite_mcp` flow valid if you do not use `uv`.

#### Claude Code

```bash
claude mcp add aseprite uv -- --directory /absolute/path/to/aseprite-mcp run -m aseprite_mcp
claude mcp add godot-mcp node -- /absolute/path/to/Godot-MCP/server/dist/index.js
```

## Platform Notes

### Windows

- Use forward slashes or escaped backslashes in JSON.
- Typical Aseprite paths:
  - `C:/Program Files/Aseprite/Aseprite.exe`
  - `C:/Program Files (x86)/Steam/steamapps/common/Aseprite/Aseprite.exe`
- If `uv` is missing after install, restart the terminal or add `%LOCALAPPDATA%\Programs\uv\bin` to `PATH`.

### macOS

- Common Aseprite path:
  - `/Applications/Aseprite.app/Contents/MacOS/aseprite`
- If `setup.sh` is not executable:
  - `chmod +x setup.sh`

### Linux

- Common Aseprite paths:
  - `~/.local/share/Steam/steamapps/common/Aseprite/aseprite`
  - `/usr/local/bin/aseprite`
- Ensure the binary is executable:
  - `chmod +x /path/to/aseprite`

## Verify the Setup

### Test `aseprite-mcp`

With `uv`:

```bash
cd aseprite-mcp
uv run python -c "import aseprite_mcp; print('aseprite_mcp OK')"
```

Without `uv`:

```bash
cd aseprite-mcp
python -c "import aseprite_mcp; print('aseprite_mcp OK')"
```

### Test `Godot-MCP/server`

```bash
node Godot-MCP/server/dist/index.js
```

The process should start without a module error. Stop it with `Ctrl+C`.

### Test the Godot plugin connection

1. Open a Godot project with the plugin enabled.
2. Check the bottom `MCP` panel.
3. Or check the Godot output for a message that the WebSocket server started on port `9080`.

## Troubleshooting

### `aseprite-mcp`: Aseprite not found

- Verify `ASEPRITE_PATH` points to the executable.
- Test it directly:
  - `"/path/to/aseprite" --batch --version`
- On macOS or Linux, verify execute permission.

### `godot-mcp`: WebSocket connection refused

- The Godot editor must be open with the plugin enabled.
- The project must have `addons/godot_mcp/` installed.
- Check whether port `9080` is already in use.

Windows:

```powershell
netstat -ano | findstr 9080
```

macOS / Linux:

```bash
netstat -an | grep 9080
```

### `godot-mcp`: Cannot find `dist/index.js`

- Run `npm run build` inside `Godot-MCP/server`.
- `dist/` is generated and is not committed to the repo.

### `uv` not found

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows:

```powershell
winget install astral-sh.uv
```

Fallback:

```bash
python -m pip install uv
```

### Node.js is too old

Linux / macOS:

```bash
nvm install 20
nvm use 20
```

Windows:

- Install a current Node.js release from `https://nodejs.org`.
- Or use `nvm-windows`.

## Updating

```bash
git pull
cd Godot-MCP/server
npm install
npm run build
cd ../../aseprite-mcp
uv sync
```
