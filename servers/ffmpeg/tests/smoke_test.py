"""Drive a real ffmpeg end to end. Needs the binary; excluded from unit runs.

    uv run tests/smoke_test.py [--clean]

Self-contained: every input is synthesized with ffmpeg's lavfi sources (sine
tones, test cards), so no external media is required. Exit 0 only when
everything passed.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ffmpeg_mcp.core import runner  # noqa: E402
from ffmpeg_mcp.tools import audio, video  # noqa: E402

OUT = Path(__file__).parent / "smoke_output"
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  -- {detail[:70]}" if detail else ""))


def parsed(result: str) -> dict | None:
    try:
        return json.loads(result)
    except ValueError:
        return None


def main() -> int:
    if runner.resolve_ffmpeg(refresh=True) is None:
        print("ffmpeg not found -- set FFMPEG_PATH. Nothing to smoke-test.")
        return 1
    OUT.mkdir(exist_ok=True)

    info = parsed(audio.get_ffmpeg_info())
    check("get_ffmpeg_info", bool(info and info.get("found")),
          str(info and info.get("version", ""))[:40])

    # Synthesize inputs: a 2s sine tone and a 2s test-card clip.
    runner.run_ffmpeg(["-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                       str(OUT / "tone.wav")])
    runner.run_ffmpeg(["-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=15",
                       str(OUT / "clip.mp4")])

    r = parsed(audio.convert_audio(str(OUT / "tone.wav"), str(OUT / "tone.ogg"),
                                   quality=5))
    check("wav -> ogg (the Godot music path)",
          bool(r and r["streams"][0]["codec"] == "vorbis" and r["seconds"] > 1.9),
          str(r and r.get("seconds")))

    r = parsed(audio.trim_audio(str(OUT / "tone.wav"), str(OUT / "stinger.wav"),
                                start=0.5, duration=1.0, fade_in=0.1, fade_out=0.2))
    check("trim with fades", bool(r and abs(r["seconds"] - 1.0) < 0.1),
          str(r and r.get("seconds")))

    r = parsed(audio.batch_convert_audio(str(OUT), str(OUT / "batch"), pattern="*.wav"))
    check("batch convert", bool(r and len(r["converted"]) >= 2 and not r["failures"]),
          str(r and r.get("converted")))
    r2 = parsed(audio.batch_convert_audio(str(OUT), str(OUT / "batch"), pattern="*.wav"))
    check("batch skips up-to-date", bool(r2 and not r2["converted"] and r2["skipped_up_to_date"]))

    r = parsed(audio.make_waveform_image(str(OUT / "tone.wav"), str(OUT / "wave.png")))
    check("waveform image", bool(r and r["streams"][0].get("width") == 800))

    r = parsed(video.make_gif(str(OUT / "clip.mp4"), str(OUT / "clip.gif"),
                              fps=10, width=160))
    check("video -> gif", bool(r and r["bytes"] > 1000), str(r and r.get("bytes")))

    r = parsed(video.extract_frames(str(OUT / "clip.mp4"), str(OUT / "frames" / "f_%03d.png"),
                                    fps=2))
    check("extract frames", bool(r and r["frames_written"] >= 3),
          str(r and r.get("frames_written")))

    r = parsed(video.make_video(str(OUT / "frames" / "f_%03d.png"),
                                str(OUT / "rebuilt.webm"), fps=2))
    check("frames -> webm", bool(r and r["streams"][0]["codec"] == "vp9"))

    bad = audio.convert_audio(str(OUT / "never.wav"), str(OUT / "x.ogg"))
    check("missing input is a loud error", bad.startswith("ERROR:"))

    failed = sum(1 for _, ok, _ in CHECKS if not ok)
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} passed")
    if "--clean" in sys.argv and failed == 0:
        shutil.rmtree(OUT, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
