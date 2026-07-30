"""Probe an MCP stdio server: initialize, then tools/list, robustly.

    python scripts/checks/probe_stdio_server.py [--cwd DIR] -- <command> [args...]

Exit 0 when the server answers both, printing the advertised tool count.

This exists because the obvious probe -- write the requests, close stdin, read
what comes back -- has a race: closing stdin tells a well-behaved MCP server to
shut down, and on a slow machine it can exit before flushing the tools/list
response. That probe passed for days and then failed once on a cold CI runner.
_mcp_probe.mcp_handshake holds stdin open, reads responses as they arrive, and
kills the process only after both answers are in, so CI and local verification
now share the one implementation that does this correctly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _mcp_probe import mcp_handshake  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cwd", default=".", help="working directory for the server")
    parser.add_argument("--timeout", type=int, default=120,
                        help="seconds to wait for both responses")
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="server command (prefix with -- to stop option parsing)")
    args = parser.parse_args()

    command = [c for c in args.command if c != "--"]
    if not command:
        parser.error("no server command given")

    ok, count, message = mcp_handshake(command, Path(args.cwd).resolve(),
                                       timeout=args.timeout)
    if not ok:
        print(f"handshake FAILED: {message}")
        return 1
    print(f"handshake OK, {count} tools advertised")
    return 0


if __name__ == "__main__":
    sys.exit(main())
