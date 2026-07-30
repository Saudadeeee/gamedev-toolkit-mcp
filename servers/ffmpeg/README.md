# ffmpeg MCP server

The game pipeline's format glue, by driving [ffmpeg](https://ffmpeg.org)
through its CLI. Spawned per call — no running application, same model as the
`aseprite` and `rfxgen` servers.

## Why it exists

Nothing else in this toolkit writes `.ogg`, and `.ogg` Vorbis is what Godot
wants for music and ambience. rfxgen and Audacity make the sounds; this server
delivers them in engine shape — and turns godot-mcp's captures into devlog
GIFs and trailer clips.

| Tool | Does |
|---|---|
| `get_ffmpeg_info` | Binary paths, version — run first on failures |
| `get_media_info` | Container, duration, streams, codecs for any file |
| `convert_audio` | Anything → what the extension says; the wav→ogg Godot path |
| `trim_audio` | Cut a section, optional edge fades — loops and stingers |
| `batch_convert_audio` | Directory sweep, skips up-to-date outputs |
| `make_waveform_image` | Waveform PNG — *see* a silent/clipped render at a glance |
| `make_gif` | Video or frame sequence → palette-optimized GIF (nearest-neighbour, pixel-art safe) |
| `make_video` | Frame sequence or re-encode → `.webm`/`.mp4` trailer clips |
| `extract_frames` | Video → PNGs; reference frames for aseprite rotoscoping |

Every render is verified with ffprobe (real streams, non-zero duration) —
a container with no content probes cleanly, so "ffmpeg exited 0" is not
trusted alone.

## Setup

Needs the ffmpeg binary (with ffprobe beside it) — `FFMPEG_PATH` or a standard
install location (`D:\Apps\ffmpeg\bin`, PATH). `toolkit.json` carries the
client entry; `scripts/write_mcp_config.py` resolves it.

```bash
uv sync --directory servers/ffmpeg        # deps
uv run python -m pytest                   # unit tests (no binary needed)
uv run tests/smoke_test.py --clean        # end-to-end; inputs synthesized via lavfi
```

Pipeline position: **rfxgen/audacity produce → ffmpeg delivers (ogg) →
godot consumes**, and **godot captures → ffmpeg → GIF/webm for the devlog.**

ffmpeg itself is an external application under its own licence (GPL/LGPL
build), driven through its CLI and not redistributed here. This server's code
is original to the toolkit, GPL-3.0-or-later like the whole.
