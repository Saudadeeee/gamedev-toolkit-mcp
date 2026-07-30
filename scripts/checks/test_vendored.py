"""Run the vendored servers' own upstream test suites.

Vendoring made this repo the redistributor of these projects, so a bad update
is now our bug. Their suites are the cheapest way to notice one.

    python scripts/checks/test_vendored.py             # every server with a suite
    python scripts/checks/test_vendored.py obsidian    # just one
    python scripts/checks/test_vendored.py --keep      # leave the test venvs behind

Each suite runs in a throwaway `.venv-test` beside the server, never in the
runtime venv that scripts/install_vendored.py builds. That separation is the
point: installing pytest into the runtime venv re-resolves it, and an unpinned
transitive dependency moving major version silently breaks the server. The test
env therefore repeats the runtime pins -- see `install.testPackages` in
toolkit.json, which is the complete install list for a test environment rather
than an addition to `install.packages`.

Exit code 0 when every suite passed or was skipped for having none.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _toolkit import BAD, OK, ROOT, SKIP, heading, load_registry, paint, which  # noqa: E402

TEST_VENV = ".venv-test"


def venv_python(directory: Path) -> Path | None:
    for candidate in (directory / TEST_VENV / "Scripts" / "python.exe",
                      directory / TEST_VENV / "bin" / "python"):
        if candidate.exists():
            return candidate
    return None


def run(cmd: list[str], cwd: Path, timeout: int = 1800) -> tuple[bool, str]:
    """Run a command, returning (ok, last meaningful line of output)."""
    resolved = which(cmd[0]) if not Path(cmd[0]).exists() else cmd[0]
    if resolved is None:
        return False, f"{cmd[0]} not found on PATH"
    try:
        proc = subprocess.run(
            [str(resolved), *cmd[1:]], cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except OSError as error:
        return False, f"could not run {cmd[0]}: {error}"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"

    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    lines = [line for line in output.splitlines() if line.strip()]
    # pytest's summary is the useful line; it is usually last, but warnings can
    # follow it.
    summary = next((line for line in reversed(lines)
                    if " passed" in line or " failed" in line or " error" in line), "")
    return proc.returncode == 0, (summary or (lines[-1] if lines else ""))


def has_tests(directory: Path) -> bool:
    tests = directory / "tests"
    return tests.is_dir() and any(tests.glob("test_*.py"))


def test_server(name: str, spec: dict, *, keep: bool) -> str:
    directory = ROOT / spec["path"]
    install = spec.get("install") or {}
    packages = install.get("testPackages")

    if not packages:
        print(f"  {SKIP}  {name}  --  no testPackages declared in toolkit.json")
        return SKIP
    if not has_tests(directory):
        print(f"  {SKIP}  {name}  --  upstream ships no test suite")
        return SKIP

    venv = directory / TEST_VENV
    shutil.rmtree(venv, ignore_errors=True)

    ok, message = run(["uv", "venv", TEST_VENV], directory, timeout=300)
    if not ok:
        print(f"  {BAD}  {name}  --  uv venv failed: {message}")
        return BAD

    ok, message = run(["uv", "pip", "install", "--python", TEST_VENV, *packages],
                      directory, timeout=1800)
    if not ok:
        print(f"  {BAD}  {name}  --  install failed: {message}")
        return BAD

    python = venv_python(directory)
    if python is None:
        print(f"  {BAD}  {name}  --  no interpreter in {TEST_VENV}")
        return BAD

    # The pins have to survive the test install too, or the suite would be
    # exercising a different environment than the one that ships.
    module = install.get("verifyImport")
    if module:
        ok, message = run([str(python), "-c", f"import {module}"], directory, timeout=120)
        if not ok:
            print(f"  {BAD}  {name}  --  test env cannot import {module}: {message}")
            return BAD

    ok, message = run([str(python), "-m", "pytest", "-q"], directory, timeout=1800)
    print(f"  {OK if ok else BAD}  {name}  --  {message}")

    if not keep:
        shutil.rmtree(venv, ignore_errors=True)
    return OK if ok else BAD


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="*", help="server names; default is all vendored")
    parser.add_argument("--keep", action="store_true",
                        help=f"leave each {TEST_VENV} in place for debugging")
    args = parser.parse_args()

    if which("uv") is None:
        print(f"{BAD} uv is not on PATH -- see https://astral.sh/uv")
        return 1

    all_servers = load_registry().get("servers", {})
    wanted = set(args.names)
    unknown = wanted - set(all_servers)
    if unknown:
        print(f"{BAD} unknown server(s): {', '.join(sorted(unknown))}")
        return 1

    selected = {name: spec for name, spec in all_servers.items()
                if spec.get("origin") == "vendored" and (not wanted or name in wanted)}

    print(paint("Vendored servers -- upstream test suites", "1"))
    heading("Running")

    statuses = [test_server(name, spec, keep=args.keep) for name, spec in selected.items()]

    failed = statuses.count(BAD)
    heading("Summary")
    print(f"  {statuses.count(OK)} passed, {failed} failed, {statuses.count(SKIP)} skipped")

    if failed:
        print(f"\n{BAD} -- an upstream suite is failing. If you just updated a "
              f"vendored server, that update is the suspect.")
        return 1
    print(f"\n{OK} -- every vendored suite passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
