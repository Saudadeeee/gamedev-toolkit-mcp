# Licensing

GameDev Toolkit MCP is **GPL-3.0-or-later**. It was MIT through commit `c5f32f4`.

- [`LICENSE`](../LICENSE) — the GPL-3.0 text, verbatim and unmodified.
- [`COPYRIGHT`](../COPYRIGHT) — who holds copyright on what, and each component's own licence.
- [`CREDITS.md`](../CREDITS.md) — what each upstream contributes functionally.

## Why it changed

The Blockbench MCP plugin is GPL-3.0. As long as it was merely *cloned* on the
user's machine and never redistributed here, that imposed nothing — GPL
obligations attach to distribution, not to use.

Vendoring it into this repository changes that: the project now redistributes
GPL-3.0 code, and GPL-3.0 code cannot be redistributed under a more permissive
licence. Every other component (MIT, Apache-2.0) flows one-way *into* GPL-3.0,
so GPL-3.0 is the only licence the combined work can carry.

```
MIT        ──┐
Apache-2.0 ──┼──►  GPL-3.0        (one-way; there is no path back)
GPL-3.0    ──┘
```

## What this means for you

### Using the toolkit

Nothing changes. Run it, drive it from an AI assistant, use it privately,
modify it for yourself — GPL-3.0 attaches obligations only when you **convey**
(distribute) the software to someone else.

### Art, audio, models and code it produces

Yours. GPL-3.0 covers the program, not its output. A sprite drawn through the
`aseprite` server, a scene built through `godot-mcp`, a GDScript file it wrote —
none of that becomes GPL. Licence your game however you like.

### Distributing a modified toolkit

If you fork this and give the fork to anyone, GPL-3.0 requires you to:

1. Release the **complete corresponding source** of your version under GPL-3.0.
2. Keep the copyright notices, `LICENSE`, and each component's licence file.
3. **State that you changed it, and when** — GPL-3.0 §5(a).
4. Pass the same freedoms on; you may not add further restrictions.

### Distributing the Godot addon

`servers/godot/addons/godot_mcp/` is designed to be copied into your Godot
project, which puts GPL-3.0 files inside a project you may want to keep
proprietary. In practice:

- It is an `EditorPlugin`. It runs in the Godot **editor**, not in your game.
- Godot does not load `addons/` at runtime in an exported build, and export
  presets normally exclude it. Check your export filters if you want certainty.
- Shipping a game whose exported build contains none of the addon's code
  conveys nothing, so no GPL obligation arises for the game.

If you do ship a build that bundles the addon, you are distributing GPL-3.0
code and the obligations above apply to that code.

## Obligations this repository itself meets

| Requirement | Where |
|---|---|
| Full licence text, unmodified | [`LICENSE`](../LICENSE) |
| Copyright notices for every component | [`COPYRIGHT`](../COPYRIGHT) |
| Each upstream's own licence retained in place | `servers/*/LICENSE` |
| Upstream identified, with a link | [`COPYRIGHT`](../COPYRIGHT), [`CREDITS.md`](../CREDITS.md) |
| Modification status recorded | below |

### Modification status of vendored components

GPL-3.0 §5(a) and Apache-2.0 §4(b) both require that modified files be marked.
As of the relicensing commit:

| Component | Modified here? |
|---|---|
| `servers/aseprite/` | **Yes** — extensively; a fork, see CREDITS.md |
| `servers/godot/` | **Yes** — extensively; a fork, see CREDITS.md |
| `servers/audacity/` | No — vendored verbatim from upstream |
| `servers/obsidian/` | No — vendored verbatim from upstream |
| `servers/blockbench/` | No — vendored verbatim from upstream |

If you change a vendored component, add a note at the top of each file you
touch saying what changed and when, and update the table above. That is a
licence requirement, not a style preference.

## Updating a vendored component

Vendoring means upstream fixes no longer arrive on their own. To pull one in:

```bash
git clone --depth 1 <upstream-url> /tmp/upstream
# review the diff before overwriting -- local modifications live here now
diff -ru servers/<name> /tmp/upstream --exclude=.git --exclude=.venv
```

Copy in what you want, keep the `LICENSE` file, then:

```bash
python scripts/install_vendored.py --force <name>
python scripts/write_mcp_config.py
python scripts/verify_toolkit.py --quick
```

Record the update in `CREDITS.md` and, if you modified anything, in the table
above.

## If you would rather not be GPL

The only component forcing GPL-3.0 is `servers/blockbench/`. Remove that
directory and its entry from `toolkit.json`, and the remaining components (MIT,
MIT, Apache-2.0, MIT) permit a permissive licence again. You would then reach
Blockbench the way this repo did before — cloned on the user's machine, never
redistributed.
