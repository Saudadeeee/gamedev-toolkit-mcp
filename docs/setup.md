# Setup Guide

Complete installation guide for `GameDev Toolkit MCP` on Windows, macOS, and Linux.

## Requirements

| Tool | Version | Purpose |
|---|---|---|
| [Python](https://python.org) | 3.12+ | Runs the `aseprite` server and every setup helper |
| [uv](https://github.com/astral-sh/uv) | latest | Python dependency manager |
| [Node.js](https://nodejs.org) | 18+ | Runs `servers/godot/server` |
| [Git](https://git-scm.com) | any | Cloning this repo; updating the vendored servers |
| [Godot Engine](https://godotengine.org) | 4.x | Godot editor and plugin host |
| [Aseprite](https://aseprite.org) | 1.3+ | Pixel art tool with `--batch` support |

`Aseprite` can be the paid build or a source build, as long as CLI batch mode works.

## How the repo is arranged

All five MCP servers live under [`servers/`](../servers/) and are tracked in git.
`toolkit.json` records an `origin` for each, which decides only who fixes its
bugs and how an update arrives:

| `origin` | Servers | Who fixes bugs |
|---|---|---|
| `first-party` | `aseprite`, `godot-mcp` | this repo |
| `vendored` | `audacity`, `obsidian`, `blockbench` | upstream — see [COPYRIGHT](../COPYRIGHT) |

`blockbench` is vendored for licence compliance and reference, but it runs as a
plugin *inside* the Blockbench application; this repo does not build it.

**[`toolkit.json`](../toolkit.json) is the single source of truth.** It lists
every server, its origin and runtime, how it installs, how it is configured and
how it is probed. The setup scripts and every script under `scripts/` read it, so
nothing hardcodes the server list. Add a server there and the whole toolchain
picks it up.

This project is **GPL-3.0-or-later**; see [COPYRIGHT](../COPYRIGHT).

## Quick Setup

### Windows

```powershell
git clone https://github.com/Saudadeeee/gamedev-toolkit-mcp.git
cd gamedev-toolkit-mcp
.\setup.ps1
```

### macOS / Linux

```bash
git clone https://github.com/Saudadeeee/gamedev-toolkit-mcp.git
cd gamedev-toolkit-mcp
chmod +x setup.sh
./setup.sh
```

The setup script:

1. Checks the required tools.
2. Installs the `aseprite` server's dependencies (`uv sync`).
3. Builds `servers/godot/server/dist/index.js` (`npm run build`).
4. Builds a virtualenv for each vendored server from the in-tree source.
5. Writes `mcp_config.json` covering **all five** servers, with this machine's
   absolute paths and detected application paths filled in.

`mcp_config.json` contains absolute local paths and API keys and is gitignored.
Never commit it.

## Manual Setup

### 1. Clone the repository

```bash
git clone https://github.com/Saudadeeee/gamedev-toolkit-mcp.git
cd gamedev-toolkit-mcp
```

Every command below is run from the repository root.

### 2. Install the `aseprite` server

```bash
uv sync --directory servers/aseprite
```

Fallback if `uv` is unavailable:

```bash
python -m pip install -r servers/aseprite/requirements.txt
```

### 3. Build the `godot-mcp` server

```bash
npm --prefix servers/godot/server install
npm --prefix servers/godot/server run build
```

This generates `servers/godot/server/dist/index.js`.

### 4. Build the vendored servers

```bash
python scripts/install_vendored.py
```

Their source is already in the tree, so this only creates each one's virtualenv
and installs it. Useful flags:

```bash
python scripts/install_vendored.py obsidian   # just one
python scripts/install_vendored.py --check    # report status, change nothing
python scripts/install_vendored.py --force    # rebuild the venvs from scratch
```

The dependency pins in `toolkit.json` matter. The `audacity` server imports
`mcp.server.fastmcp`, which `mcp` 2.0 removed, and its own dependency is
unpinned — without the `<2` pin a fresh install picks 2.x and dies at startup
with `ModuleNotFoundError`.

### 5. Load the Blockbench plugin

Nothing to build here — the source in `servers/blockbench/` is vendored for
reference and licence compliance, but the plugin is loaded by the app itself:

1. `Blockbench > File > Plugins > Load Plugin from URL`
2. `https://jasonjgardner.github.io/blockbench-mcp-plugin/mcp.js`
3. Grant the network permission it asks for.
4. Leave Blockbench open. It serves the MCP endpoint from inside the app.

The plugin does not always land on port `3000`; `write_mcp_config.py` probes the
candidates in `toolkit.json` and pins whichever answers. If none do, check the
plugin's status bar and set the port by hand.

### 6. Enable the Godot plugin

```bash
python scripts/install_godot_plugin.py /path/to/your/godot/project
```

Or by hand:

1. Open your Godot 4 project in the editor.
2. Copy `servers/godot/addons/godot_mcp/` into the project's `addons/` folder.
3. `Project > Project Settings > Plugins`.
4. Enable `Godot MCP`.
5. Confirm the plugin starts its WebSocket server on port `9080`.

To use multiple Godot projects, install the addon into each one.

### 7. Configure Obsidian

Install the **Local REST API** community plugin in Obsidian, open it once so it
generates a key, then:

```bash
python scripts/configure_obsidian.py
```

That copies the key into `mcp_config.json`. The server starts without it, but
every call fails.

### 8. Generate the client config

```bash
python scripts/write_mcp_config.py            # writes mcp_config.json
python scripts/write_mcp_config.py --print    # preview it, write nothing
```

Re-running is safe: values you already have in `mcp_config.json` — API keys, a
path you corrected by hand — are carried over rather than reset to placeholders.

Then merge it into your MCP client:

- Claude Desktop — Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Claude Desktop — macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Claude Desktop — Linux: `~/.config/Claude/claude_desktop_config.json`
- Claude Code: `claude mcp add`, or a project `.mcp.json`

#### Example generated config

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "/abs/path/to/servers/obsidian/.venv/bin/mcp-obsidian",
      "args": [],
      "env": {
        "OBSIDIAN_API_KEY": "...",
        "OBSIDIAN_HOST": "127.0.0.1",
        "OBSIDIAN_PORT": "27123"
      }
    },
    "aseprite": {
      "command": "uv",
      "args": ["--directory", "/abs/path/to/servers/aseprite", "run", "-m", "aseprite_mcp"],
      "cwd": "/abs/path/to/servers/aseprite",
      "env": { "ASEPRITE_PATH": "/abs/path/to/aseprite" }
    },
    "blockbench": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:3000/bb-mcp"]
    },
    "audacity": {
      "command": "/abs/path/to/servers/audacity/.venv/bin/audacity-mcp",
      "args": []
    },
    "godot-mcp": {
      "command": "node",
      "args": ["/abs/path/to/servers/godot/server/dist/index.js"],
      "env": { "MCP_TRANSPORT": "stdio" }
    }
  }
}
```

`cwd` on the `aseprite` entry is what keeps the `python -m aseprite_mcp` fallback
valid when `uv` is not installed.

The `audacity` entry invokes the console script `audacity-mcp`, not
`python -m audacity_mcp` — that package has no `__main__.py`.

## Which servers need their application running

| Server | App must be open? | Extra setup |
|---|---|---|
| `aseprite` | **No** — spawns `aseprite --batch` per call | none |
| `godot-mcp` scene tools | **Yes** — editor open, `godot_mcp` plugin enabled | WebSocket on `9080` |
| `godot-mcp` headless tools | **No** — drives the binary directly | none |
| `blockbench` | **Yes** — app open with the MCP plugin loaded | HTTP, usually `3000` |
| `audacity` | **Yes** — Audacity 3.x with `mod-script-pipe` | 4.x is unsupported upstream |
| `obsidian` | **Yes** — app open with Local REST API | `OBSIDIAN_API_KEY` |

## Platform Notes

### Windows

- Use forward slashes or escaped backslashes in JSON.
- Typical Aseprite paths:
  - `C:/Program Files/Aseprite/Aseprite.exe`
  - `C:/Program Files (x86)/Steam/steamapps/common/Aseprite/Aseprite.exe`
- If `uv` is missing after install, restart the terminal or add
  `%LOCALAPPDATA%\Programs\uv\bin` to `PATH`.

### macOS

- Common Aseprite path: `/Applications/Aseprite.app/Contents/MacOS/aseprite`
- If `setup.sh` is not executable: `chmod +x setup.sh`

### Linux

- Common Aseprite paths:
  - `~/.local/share/Steam/steamapps/common/Aseprite/aseprite`
  - `/usr/local/bin/aseprite`
- Ensure the binary is executable: `chmod +x /path/to/aseprite`

## Verify the Setup

One command checks everything — prerequisites, application discovery, installs,
live bridges, an MCP handshake against every configured server, and the test
suites:

```bash
python scripts/verify_toolkit.py            # everything runnable
python scripts/verify_toolkit.py --quick    # skip the slow app-driven suites
```

It exits 0 when every automated check passed. Manual steps still outstanding are
listed under **Still needs you** and do not fail the run.

`get_toolkit_status` (on the `aseprite` server) reports the same application and
bridge state from inside an MCP session.

## Troubleshooting

### A vendored server suddenly stops starting

Console scripts bake in an absolute interpreter path, so **moving or renaming the
repo breaks every virtualenv** while leaving the files looking present. Rebuild:

```bash
python scripts/install_vendored.py --force
python scripts/write_mcp_config.py
```

`scripts/install_vendored.py --check` reports this as `venv missing or stale`.

### `aseprite`: Aseprite not found

- Verify `ASEPRITE_PATH` in `mcp_config.json` points at the executable.
- Test it directly: `"/path/to/aseprite" --batch --version`
- On macOS or Linux, verify execute permission.

### `godot-mcp`: WebSocket connection refused

- The Godot editor must be open with the plugin enabled.
- The project must have `addons/godot_mcp/` installed.
- Check whether port `9080` is already in use:

```powershell
netstat -ano | findstr 9080      # Windows
```

```bash
netstat -an | grep 9080          # macOS / Linux
```

### `godot-mcp`: cannot find `dist/index.js`

```bash
npm --prefix servers/godot/server run build
```

`dist/` is generated and is not committed.

### `blockbench`: no MCP server found

The plugin picks its own port. Check the Blockbench status bar, then either
re-run `python scripts/write_mcp_config.py` with the app open (it probes) or
edit the port in `mcp_config.json`.

### `audacity`: tools list but every call fails

`mod-script-pipe` is not running. `Edit > Preferences > Modules >
mod-script-pipe = Enabled`, then restart Audacity. Audacity 3.x only.

### `obsidian`: every call returns an auth error

`OBSIDIAN_API_KEY` is unset or stale. Re-run `python scripts/configure_obsidian.py`.

### `uv` not found

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh    # macOS / Linux
```

```powershell
winget install astral-sh.uv                        # Windows
```

Fallback: `python -m pip install uv`

### Node.js is too old

```bash
nvm install 20 && nvm use 20                       # macOS / Linux
```

On Windows, install a current release from `https://nodejs.org`, or use
`nvm-windows`.

## Updating

```bash
git pull
uv sync --directory servers/aseprite
npm --prefix servers/godot/server install
npm --prefix servers/godot/server run build
python scripts/install_vendored.py
python scripts/write_mcp_config.py
```

### Pulling a newer upstream into a vendored server

Vendoring means upstream fixes no longer arrive on their own, and that this repo
is the one redistributing them. Treat an update as a licensing operation as much
as a technical one.

```bash
git clone --depth 1 <upstream-url> /tmp/upstream
diff -ru servers/<name> /tmp/upstream --exclude=.git --exclude=.venv --exclude=.venv-test
```

Review the diff before overwriting — nothing else is tracking local changes now.
Copy in what you want, **keep the `LICENSE` file**, then:

```bash
python scripts/install_vendored.py --force <name>
python scripts/checks/test_vendored.py <name>      # upstream's own suite
python scripts/write_mcp_config.py
python scripts/verify_toolkit.py --quick
```

Record the update in [`CREDITS.md`](../CREDITS.md). If you modified anything
rather than copying verbatim, [`COPYRIGHT`](../COPYRIGHT) has to say so — that
is a licence requirement, not a style preference.

### Running the vendored suites

```bash
python scripts/checks/test_vendored.py             # all of them
python scripts/checks/test_vendored.py obsidian    # just one
python scripts/checks/test_vendored.py --keep      # leave .venv-test for debugging
```

Each suite runs in a throwaway `.venv-test`, never in the runtime venv. That is
deliberate: installing pytest into a runtime venv re-resolves it, and an
unpinned transitive dependency moving major version breaks the server
invisibly — which is exactly how the `audacity` server once ended up with
`mcp` 2.0 and no `mcp.server.fastmcp`. The test environment repeats the runtime
pins; see `install.testPackages` in `toolkit.json`.
