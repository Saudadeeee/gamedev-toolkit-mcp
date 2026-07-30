"""Compare each vendored server against its upstream HEAD.

Vendoring means upstream fixes stop arriving on their own; this is the alarm
that says one is waiting. It clones each `"origin": "vendored"` entry from
toolkit.json at depth 1 and diffs the trees.

    python scripts/checks/check_upstream_drift.py            # all vendored
    python scripts/checks/check_upstream_drift.py obsidian   # just one

Exit code 1 when any server differs from upstream HEAD -- which means either
upstream moved (pull it in: see docs/setup.md, "Pulling a newer upstream") or
someone edited a vendored tree locally (mark it: see COPYRIGHT, MODIFICATION
STATUS). Both deserve a look; neither is automatically wrong. A scheduled
workflow runs this monthly, so a red run is the notification.

Servers with `"modified": true` in the registry are reported but never fail the
run -- they are expected to differ.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _toolkit import BAD, OK, ROOT, SKIP, heading, load_registry, paint, which  # noqa: E402

# Build artefacts and local state; never part of what upstream ships.
IGNORE_DIRS = {".git", ".venv", ".venv-test", "__pycache__", "node_modules",
               ".pytest_cache", ".ruff_cache", "dist"}


def tree_digest(root: Path) -> dict[str, str]:
    """Relative path -> content hash for every file under root."""
    digest: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.relative_to(root).parts):
            continue
        # Normalise line endings: the vendored copy passed through
        # .gitattributes, the fresh clone did not, and CRLF-vs-LF is not drift.
        content = path.read_bytes().replace(b"\r\n", b"\n")
        digest[path.relative_to(root).as_posix()] = hashlib.sha256(content).hexdigest()
    return digest


def compare(name: str, spec: dict, scratch: Path) -> tuple[str, str]:
    """Clone upstream and diff. Returns (status, detail)."""
    repo = spec.get("repo")
    vendored = ROOT / spec["path"]
    if not repo:
        return BAD, "no upstream repo recorded in toolkit.json"
    if not vendored.is_dir():
        return BAD, f"{spec['path']} is missing from the tree"

    clone = scratch / name
    proc = subprocess.run(
        [which("git") or "git", "clone", "--depth", "1", "--quiet", repo, str(clone)],
        capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return SKIP, f"clone failed: {tail[-1][:80] if tail else 'unknown error'}"

    ours, theirs = tree_digest(vendored), tree_digest(clone)
    only_ours = sorted(set(ours) - set(theirs))
    only_theirs = sorted(set(theirs) - set(ours))
    changed = sorted(f for f in set(ours) & set(theirs) if ours[f] != theirs[f])

    if not (only_ours or only_theirs or changed):
        return OK, f"{len(ours)} files, byte-identical to upstream HEAD"

    detail = (f"{len(changed)} changed, {len(only_theirs)} new upstream, "
              f"{len(only_ours)} only here")
    samples = [f"~{f}" for f in changed[:3]] + [f"+{f}" for f in only_theirs[:3]] \
            + [f"-{f}" for f in only_ours[:3]]
    if samples:
        detail += "  e.g. " + ", ".join(samples[:5])

    if spec.get("modified"):
        return SKIP, f"declared modified; {detail}"
    return BAD, detail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="server names; default is all vendored")
    args = parser.parse_args()

    if which("git") is None:
        print(f"{BAD} git is not on PATH")
        return 1

    servers = {name: spec for name, spec in load_registry().get("servers", {}).items()
               if spec.get("origin") == "vendored"}
    wanted = set(args.names)
    unknown = wanted - set(servers)
    if unknown:
        print(f"{BAD} not vendored or unknown: {', '.join(sorted(unknown))}")
        return 1
    if wanted:
        servers = {n: s for n, s in servers.items() if n in wanted}

    print(paint("Vendored servers vs upstream HEAD", "1"))
    heading("Comparing")

    drifted = 0
    with tempfile.TemporaryDirectory(prefix="drift-") as scratch:
        for name, spec in servers.items():
            status, detail = compare(name, spec, Path(scratch))
            print(f"  {status}  {name}  --  {detail}")
            if status == BAD:
                drifted += 1

    heading("Summary")
    if drifted:
        print(f"  {drifted} server(s) differ from upstream HEAD.")
        print("\n  Upstream moved -> pull it in: docs/setup.md, 'Pulling a newer upstream'.")
        print("  Local edits   -> mark them:   COPYRIGHT, MODIFICATION STATUS.")
        print(f"\n{BAD}")
        return 1
    print(f"\n{OK} -- every vendored tree matches upstream (or is declared modified).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
