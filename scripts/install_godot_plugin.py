"""Install this repo's godot_mcp addon into a Godot project and enable it.

The Godot MCP server talks to a plugin that lives inside your project, so the
addon has to be copied there and switched on before any scene tool works. The
Plugins tab shows an empty list until it is.

    python scripts/install_godot_plugin.py <project>      # install or update
    python scripts/install_godot_plugin.py --list         # projects found nearby
    python scripts/install_godot_plugin.py <project> --check

Safe to re-run: it overwrites the addon with the current version and leaves the
rest of the project alone.
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "servers" / "godot" / "addons" / "godot_mcp"
PLUGIN_LINE = "res://addons/godot_mcp/plugin.cfg"

# Where to look when asked to list projects.
SEARCH_ROOTS = [
    Path("D:/Code/SourceCode/GameDev"),
    Path("C:/Code"),
    Path.home() / "Documents",
]


def find_projects() -> list[Path]:
    found: list[Path] = []
    for root in SEARCH_ROOTS:
        if not root.is_dir():
            continue
        for candidate in root.glob("*/project.godot"):
            found.append(candidate.parent)
    return sorted(set(found))


def resolve_project(raw: str) -> Path | None:
    path = Path(raw).expanduser().resolve()
    if path.name == "project.godot":
        path = path.parent
    return path if (path / "project.godot").exists() else None


def addon_state(project: Path) -> str:
    """Compare the project's copy of the addon with this repo's."""
    installed = project / "addons" / "godot_mcp"
    if not installed.exists():
        return "missing"

    comparison = filecmp.dircmp(str(SOURCE), str(installed))

    def differs(node: filecmp.dircmp) -> bool:
        if node.left_only or node.right_only or node.diff_files:
            return True
        return any(differs(sub) for sub in node.subdirs.values())

    return "outdated" if differs(comparison) else "current"


def enabled_in_project(project: Path) -> bool:
    text = (project / "project.godot").read_text(encoding="utf-8", errors="replace")
    return PLUGIN_LINE in text


def enable_in_project(project: Path) -> bool:
    """Add the plugin to project.godot's enabled list. True if it changed."""
    config = project / "project.godot"
    text = config.read_text(encoding="utf-8", errors="replace")
    if PLUGIN_LINE in text:
        return False

    if "[editor_plugins]" in text:
        # Append to the existing enabled= array rather than adding a second
        # section, which Godot would ignore.
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("enabled=PackedStringArray("):
                inner = line[len("enabled=PackedStringArray("):].rstrip(")")
                entries = [e.strip() for e in inner.split(",") if e.strip()]
                entries.append(f'"{PLUGIN_LINE}"')
                lines[i] = f"enabled=PackedStringArray({', '.join(entries)})"
                text = "\n".join(lines) + "\n"
                break
        else:
            text = text.replace(
                "[editor_plugins]",
                f'[editor_plugins]\n\nenabled=PackedStringArray("{PLUGIN_LINE}")',
                1,
            )
    else:
        text = text.rstrip() + (
            f'\n\n[editor_plugins]\n\nenabled=PackedStringArray("{PLUGIN_LINE}")\n'
        )

    config.write_text(text, encoding="utf-8")
    return True


def install(project: Path) -> None:
    target = project / "addons" / "godot_mcp"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SOURCE, target)
    print(f"  copied the addon -> {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", help="Godot project folder")
    parser.add_argument("--list", action="store_true", help="list nearby projects")
    parser.add_argument("--check", action="store_true", help="report only, change nothing")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"Addon source missing: {SOURCE}")
        return 1

    if args.list or not args.project:
        projects = find_projects()
        if not projects:
            print("No Godot projects found in the usual places. Pass a path instead.")
            return 1
        print("Godot projects found:\n")
        for path in projects:
            state = addon_state(path)
            enabled = "enabled" if enabled_in_project(path) else "not enabled"
            print(f"  {path}")
            print(f"      addon: {state}, {enabled}")
        print("\nInstall with: python scripts/install_godot_plugin.py <project>")
        return 0

    project = resolve_project(args.project)
    if project is None:
        print(f"No project.godot under {args.project}")
        return 1

    print(f"Project: {project}\n")
    state = addon_state(project)
    enabled = enabled_in_project(project)
    print(f"  addon   : {state}")
    print(f"  enabled : {'yes' if enabled else 'no'}")

    if args.check:
        return 0

    if state != "current":
        install(project)
    else:
        print("  addon already matches this repo")

    if enable_in_project(project):
        print("  enabled it in project.godot")
    elif not enabled:
        print("  could not enable it automatically -- do it in the Plugins tab")
    else:
        print("  already enabled in project.godot")

    print(
        "\nReload the project in Godot (Project > Reload Current Project) so the\n"
        "plugin loads. It then serves the MCP bridge on port 9080."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
