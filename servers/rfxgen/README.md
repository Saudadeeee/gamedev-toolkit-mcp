# rfxgen MCP server

Retro sound-effect synthesis for the game pipeline, by driving
[rfxgen](https://github.com/raysan5/rfxgen) (raylib's sfxr-style generator)
through its CLI. Spawned per call — no running application needed, same model
as this toolkit's `aseprite` server.

## What it adds over the raw CLI

The CLI's seven presets are **deterministic**: the same bytes every run. The
real range comes from `.rfx` parameter files — 22 synthesis parameters plus a
wave type — and this server authors those files directly (format verified
against rfxgen v5.0 source and empirically). That turns rfxgen from a jukebox
of seven sounds into an instrument.

| Tool | Does |
|---|---|
| `get_rfxgen_info` | Binary path, version, reachability — run first on failures |
| `generate_preset` | The seven CLI presets: coin, laser, explosion, powerup, hit, jump, blip |
| `design_sound` | Full parametric synthesis; optional named starting points; can save the `.rfx` |
| `generate_variations` | N mutated takes on a base sound, each with its `.rfx` for exact reload |
| `describe_sound_params` | Parameter reference (ranges + what each one does), as JSON |
| `convert_audio` | `.rfx/.wav/.qoa/.ogg/.flac/.mp3` → `.wav/.qoa/.raw/.h`, with resampling |
| `export_wave_header` | Sound as a compilable C array (`.h`) |
| `get_sound_info` | WAV facts, or the parameters inside an `.rfx` |

## The trap this server exists to handle

rfxgen exits 0 no matter what. A bad preset, an unreadable input, an
unwritable output — all exit 0, print nothing, write nothing. Every render
here is verified by inspecting the output file (existence, size, WAV header,
non-zero frames) and failures come back as loud `ERROR:` strings.

## Setup

Needs the rfxgen binary — `RFXGEN_PATH` or a standard install location
(`D:\Apps\rfxgen`, Program Files, PATH). `toolkit.json` carries the client
entry; `scripts/write_mcp_config.py` resolves it.

```bash
uv sync --directory servers/rfxgen        # deps
uv run python -m pytest                   # unit tests (no binary needed)
uv run tests/smoke_test.py --clean        # end-to-end against a real rfxgen
```

Pipeline position: **rfxgen generates → audacity edits/masters → godot
consumes.** See `AGENTS.md` for the routing rules.

rfxgen itself is © raylib technologies, zlib licence — driven as an external
application, not redistributed here. This server's code is original to the
toolkit, GPL-3.0-or-later like the whole.
