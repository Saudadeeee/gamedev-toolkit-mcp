"""Wire the Obsidian MCP server up to a vault.

Installs and enables the Local REST API plugin if it is missing, then — once
Obsidian has been opened at least once and the plugin has generated its API
key — copies that key into mcp_config.json and checks the API answers.

    python scripts/configure_obsidian.py             # the currently open vault
    python scripts/configure_obsidian.py --vault "C:/path/to/vault"
    python scripts/configure_obsidian.py --list      # show known vaults

Run it once before opening Obsidian to install the plugin, and again
afterwards to pick up the key. Nothing is overwritten that already looks
configured.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "mcp_config.json"

PLUGIN_ID = "obsidian-local-rest-api"
RELEASE = "5.0.2"
FILES = ("main.js", "manifest.json", "styles.css")
BASE_URL = f"https://github.com/coddingtonbear/{PLUGIN_ID}/releases/download/{RELEASE}"

DEFAULT_HTTP_PORT = 27123
DEFAULT_HTTPS_PORT = 27124


def known_vaults() -> list[tuple[Path, bool]]:
    """Every vault Obsidian remembers, and whether it is the open one."""
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    config = Path(appdata) / "obsidian" / "obsidian.json"
    if not config.exists():
        return []

    data = json.loads(config.read_text(encoding="utf-8"))
    vaults = []
    for entry in data.get("vaults", {}).values():
        vaults.append((Path(entry["path"]), bool(entry.get("open"))))
    return vaults


def pick_vault(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.exists() else None

    vaults = known_vaults()
    for path, is_open in vaults:
        if is_open and path.exists():
            return path
    for path, _ in vaults:
        if path.exists():
            return path
    return None


def install_plugin(vault: Path) -> bool:
    """Download the plugin into the vault. Returns True if anything changed."""
    target = vault / ".obsidian" / "plugins" / PLUGIN_ID
    target.mkdir(parents=True, exist_ok=True)

    changed = False
    for name in FILES:
        destination = target / name
        if destination.exists() and destination.stat().st_size > 0:
            continue
        try:
            with urllib.request.urlopen(f"{BASE_URL}/{name}", timeout=60) as response:
                destination.write_bytes(response.read())
            print(f"  downloaded {name} ({destination.stat().st_size} bytes)")
            changed = True
        except (urllib.error.URLError, OSError) as error:
            print(f"  could not download {name}: {error}")
            return changed
    return changed


def enable_plugin(vault: Path) -> None:
    """Add the plugin to the enabled list and leave restricted mode."""
    config = vault / ".obsidian"

    enabled_file = config / "community-plugins.json"
    enabled = (
        json.loads(enabled_file.read_text(encoding="utf-8"))
        if enabled_file.exists()
        else []
    )
    if PLUGIN_ID not in enabled:
        enabled.append(PLUGIN_ID)
        enabled_file.write_text(json.dumps(enabled, indent=2) + "\n", encoding="utf-8")
        print(f"  enabled {PLUGIN_ID}")

    # Obsidian ignores community plugins entirely while restricted mode is on.
    app_file = config / "app.json"
    app = json.loads(app_file.read_text(encoding="utf-8")) if app_file.exists() else {}
    if app.get("communityPluginsEnabled") is not True:
        app["communityPluginsEnabled"] = True
        app_file.write_text(json.dumps(app, indent=2) + "\n", encoding="utf-8")
        print("  turned off restricted mode")


def prime_settings(vault: Path) -> None:
    """Turn on the plain-HTTP listener.

    mcp-obsidian talks HTTP; the plugin ships with only its HTTPS listener on,
    and that certificate is self-signed, so the client rejects it.
    """
    data_file = vault / ".obsidian" / "plugins" / PLUGIN_ID / "data.json"
    data = json.loads(data_file.read_text(encoding="utf-8")) if data_file.exists() else {}
    if data.get("enableInsecureServer") is True:
        return
    data.setdefault("port", DEFAULT_HTTPS_PORT)
    data.setdefault("insecurePort", DEFAULT_HTTP_PORT)
    data["enableInsecureServer"] = True
    data_file.parent.mkdir(parents=True, exist_ok=True)
    data_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("  enabled the plain-HTTP listener")


def read_settings(vault: Path) -> dict:
    data_file = vault / ".obsidian" / "plugins" / PLUGIN_ID / "data.json"
    if not data_file.exists():
        return {}
    try:
        return json.loads(data_file.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.6):
            return True
    except OSError:
        return False


def api_answers(port: int, key: str) -> tuple[bool, str]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
            return True, body.get("versions", {}).get("obsidian", "connected")
    except urllib.error.HTTPError as error:
        return False, f"HTTP {error.code} -- the API key may be wrong"
    except (urllib.error.URLError, OSError, ValueError) as error:
        return False, str(error)


def write_config(key: str, port: int) -> None:
    """Put the key into mcp_config.json without disturbing anything else."""
    if not CONFIG.exists():
        print(f"  {CONFIG} not found; skipping")
        return

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    server = config.get("mcpServers", {}).get("obsidian")
    if server is None:
        print("  no 'obsidian' entry in mcp_config.json; skipping")
        return

    env = server.setdefault("env", {})
    env["OBSIDIAN_API_KEY"] = key
    env["OBSIDIAN_HOST"] = "127.0.0.1"
    env["OBSIDIAN_PORT"] = str(port)
    CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote the key and port {port} into mcp_config.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", help="vault path; defaults to the open one")
    parser.add_argument("--list", action="store_true", help="list known vaults and exit")
    args = parser.parse_args()

    if args.list:
        vaults = known_vaults()
        if not vaults:
            print("No vaults found. Has Obsidian been run on this machine?")
            return 1
        for path, is_open in vaults:
            print(f"  {'[open] ' if is_open else '       '}{path}")
        return 0

    vault = pick_vault(args.vault)
    if vault is None:
        print("No usable vault found. Pass --vault, or run --list to see the options.")
        return 1

    print(f"Vault: {vault}\n")

    print("Plugin")
    install_plugin(vault)
    enable_plugin(vault)
    prime_settings(vault)

    print("\nAPI key")
    settings = read_settings(vault)
    key = settings.get("apiKey", "")
    if not key:
        print("  not generated yet.")
        print("  Open Obsidian on this vault, let the plugin load, then re-run this script.")
        print("  (If Obsidian is already open, reload it: Ctrl+R.)")
        return 0

    port = int(settings.get("insecurePort", DEFAULT_HTTP_PORT))
    print(f"  found: {key[:8]}... ({len(key)} chars)")

    print("\nConnection")
    if not port_open(port):
        print(f"  port {port} closed -- open Obsidian on this vault, then re-run.")
        write_config(key, port)
        return 0

    ok, detail = api_answers(port, key)
    print(f"  {'reachable' if ok else 'unreachable'}: {detail}")

    print("\nConfig")
    write_config(key, port)

    if ok:
        print("\nDone. Restart your MCP client to pick up the new config.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
