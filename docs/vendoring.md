# Vendoring

Every MCP server lives under [`servers/`](../servers/) and is tracked in git.
There is no separate directory for upstream code — that split existed until the
project relicensed to GPL-3.0, and the licence is what made merging possible.

## What changed, and why

Previously the upstream servers were *cloned* into a gitignored `external/`.
That kept GPL-3.0 code out of an MIT repo, at the cost of a two-tier layout
where half the servers were invisible to git, CI and code search.

Relicensing to GPL-3.0 removed the constraint: every component's licence
(MIT, Apache-2.0, GPL-3.0) flows one-way into GPL-3.0, so all of it can be
redistributed here. See [licensing.md](licensing.md).

## The one distinction that survives

`toolkit.json` records `origin` per server. It no longer decides *where* code
lives — only who fixes its bugs and how an update arrives:

| `origin` | Servers | Who fixes bugs | How to update |
|---|---|---|---|
| `first-party` | `aseprite`, `godot-mcp` | this repo | edit it |
| `vendored` | `audacity`, `obsidian`, `blockbench` | upstream | the procedure below |

A second field, `runtime`, says how the server is reached — `stdio` for the four
launched as subprocesses, `in-app` for Blockbench, whose plugin runs inside the
application and is reached over HTTP. Blockbench's source is vendored for
licence compliance and reference; this repo does not build it.

## Rules for vendored directories

1. **Do not edit them casually.** They are tracked as verbatim upstream copies,
   and `COPYRIGHT` says so. Anything worth changing goes upstream.
2. **If you must edit**, GPL-3.0 §5(a) and Apache-2.0 §4(b) require you to mark
   what you changed and when. Add a note at the top of each touched file and
   flip `"modified": true` in `toolkit.json`, then update the modification table
   in [licensing.md](licensing.md). CI checks the field exists; it cannot check
   that you were honest.
3. **Never remove a `LICENSE` file** from a vendored directory. That is the
   redistribution obligation itself, and CI fails without it.

## Updating a vendored server

```bash
git clone --depth 1 <upstream-url> /tmp/upstream
diff -ru servers/<name> /tmp/upstream --exclude=.git --exclude=.venv
```

Review the diff before overwriting — local modifications, if any, live here now
and nothing else is tracking them. Copy in what you want, keep `LICENSE`, then:

```bash
python scripts/install_vendored.py --force <name>
python scripts/write_mcp_config.py
python scripts/verify_toolkit.py --quick
```

Record the update in [`CREDITS.md`](../CREDITS.md).

## Rebuilding the virtualenvs

The vendored Python servers each get their own venv, which is gitignored:

```bash
python scripts/install_vendored.py            # install or repair all
python scripts/install_vendored.py obsidian   # just one
python scripts/install_vendored.py --check    # report, change nothing
python scripts/install_vendored.py --force    # rebuild from scratch
```

`setup.sh` / `setup.ps1` call this for you.

### If a server suddenly stops starting

Console scripts bake in an absolute interpreter path, so **moving or renaming
the repo breaks every venv** while leaving the files looking fine.
`install_vendored.py` detects that and rebuilds; `--check` reports it as
`venv missing or stale (repo moved?)`.

## Going back to a permissive licence

Only `servers/blockbench/` forces GPL-3.0. Remove that directory and its
`toolkit.json` entry and the rest (MIT, MIT, Apache-2.0) permits a permissive
licence again — at which point Blockbench would have to go back to being cloned
on the user's machine rather than redistributed here.
