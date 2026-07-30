"""Audio conversion and shaping for game engines.

The reason this server exists: nothing else in the toolkit writes .ogg, and
.ogg Vorbis is what Godot wants for music and ambience. rfxgen and Audacity
produce the sounds; these tools deliver them in engine shape.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import mcp
from ..core import runner

_AUDIO_QUALITY_RANGE = (0.0, 10.0)  # libvorbis -q scale


def _out(path: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


@mcp.tool()
def get_ffmpeg_info() -> str:
    """Report the ffmpeg/ffprobe binaries this server will use.

    Run this first when a conversion tool fails.
    """
    ffmpeg = runner.resolve_ffmpeg(refresh=True)
    ffprobe = runner.resolve_ffprobe()
    if ffmpeg is None:
        return json.dumps({
            "found": False,
            "note": f"ffmpeg not found. Set {runner.ENV_VAR} or install it.",
        }, indent=2)
    version = runner.run_ffmpeg(["-version"], timeout=30).splitlines()[0]
    return json.dumps({
        "found": True,
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe or "MISSING -- output verification needs it",
        "version": version,
        "note": "Spawned per call; no running application needed.",
    }, indent=2)


@mcp.tool()
def get_media_info(file: str) -> str:
    """Inspect any media file: container, duration, streams, codecs.

    The verification companion to every render tool.
    """
    try:
        return json.dumps(runner.media_summary(file), indent=2)
    except runner.FfmpegError as error:
        return f"ERROR: {error}"


@mcp.tool()
def convert_audio(input_file: str, output_file: str,
                  sample_rate: int | None = None, channels: int | None = None,
                  quality: float | None = None) -> str:
    """Convert audio to whatever the output extension says.

    The pipeline case: WAV from rfxgen/Audacity -> .ogg for Godot music and
    ambience (music should be .ogg; short SFX can stay .wav). quality is the
    Vorbis -q scale 0..10 (default 5, ~160 kbps) and is ignored for lossless
    outputs.
    """
    source = Path(input_file)
    if not source.is_file():
        return f"ERROR: input file not found: {source}"
    try:
        args = ["-i", str(source)]
        if sample_rate:
            args += ["-ar", str(sample_rate)]
        if channels:
            if channels not in (1, 2):
                return "ERROR: channels must be 1 (mono) or 2 (stereo)"
            args += ["-ac", str(channels)]
        if quality is not None:
            lo, hi = _AUDIO_QUALITY_RANGE
            if not lo <= quality <= hi:
                return f"ERROR: quality must be within {lo}..{hi} (Vorbis -q scale)"
            args += ["-q:a", str(quality)]
        target = _out(output_file)
        runner.run_ffmpeg([*args, str(target)])
        info = runner.verify_output(target, expect_stream="audio")
    except runner.FfmpegError as error:
        return f"ERROR: {error}"
    return json.dumps({"input": str(source.resolve()), **info}, indent=2)


@mcp.tool()
def trim_audio(input_file: str, output_file: str,
               start: float = 0.0, duration: float | None = None,
               fade_in: float = 0.0, fade_out: float = 0.0) -> str:
    """Cut a section out of an audio file, with optional edge fades.

    start/duration/fades are seconds. A fade_out needs a known end, so it
    requires duration. The workhorse for turning a long render into a loopable
    bed or a stinger.
    """
    source = Path(input_file)
    if not source.is_file():
        return f"ERROR: input file not found: {source}"
    if fade_out > 0 and duration is None:
        return "ERROR: fade_out needs duration, so the fade knows where the end is"
    try:
        args = ["-i", str(source), "-ss", str(max(0.0, start))]
        if duration is not None:
            if duration <= 0:
                return "ERROR: duration must be positive"
            args += ["-t", str(duration)]
        filters = []
        if fade_in > 0:
            filters.append(f"afade=t=in:st=0:d={fade_in}")
        if fade_out > 0:
            filters.append(f"afade=t=out:st={max(0.0, duration - fade_out)}:d={fade_out}")
        if filters:
            args += ["-af", ",".join(filters)]
        target = _out(output_file)
        runner.run_ffmpeg([*args, str(target)])
        info = runner.verify_output(target, expect_stream="audio")
    except runner.FfmpegError as error:
        return f"ERROR: {error}"
    return json.dumps({"input": str(source.resolve()), "start": start,
                       "duration": duration, **info}, indent=2)


@mcp.tool()
def batch_convert_audio(input_dir: str, output_dir: str,
                        to_format: str = "ogg", pattern: str = "*.wav",
                        sample_rate: int | None = None,
                        quality: float | None = None) -> str:
    """Convert every matching file in a directory. The SFX-folder-to-ogg sweep.

    Skips files whose output already exists and is newer than the input, so
    re-running after adding a few sounds only does the new work.
    """
    source_dir = Path(input_dir)
    if not source_dir.is_dir():
        return f"ERROR: input directory not found: {source_dir}"
    to_format = to_format.lstrip(".").lower()
    files = sorted(source_dir.glob(pattern))
    if not files:
        return f"ERROR: nothing in {source_dir} matches {pattern!r}"

    converted, skipped, failures = [], [], []
    for source in files:
        target = Path(output_dir) / source.with_suffix(f".{to_format}").name
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime:
            skipped.append(target.name)
            continue
        result = convert_audio(str(source), str(target),
                               sample_rate=sample_rate, quality=quality)
        if result.startswith("ERROR"):
            failures.append({"file": source.name, "error": result[:160]})
        else:
            converted.append(target.name)

    return json.dumps({
        "converted": converted,
        "skipped_up_to_date": skipped,
        "failures": failures,
        "output_dir": str(Path(output_dir).resolve()),
    }, indent=2)


@mcp.tool()
def make_waveform_image(input_file: str, output_file: str,
                        width: int = 800, height: int = 240) -> str:
    """Render an audio file's waveform to a PNG.

    Sight for the audio pipeline: after generating an SFX, look at its shape --
    a silent render, a clipped one, or a wrong-length loop is obvious at a
    glance where a duration number is not.
    """
    source = Path(input_file)
    if not source.is_file():
        return f"ERROR: input file not found: {source}"
    if not 64 <= width <= 4096 or not 64 <= height <= 2048:
        return "ERROR: width must be 64..4096 and height 64..2048"
    try:
        target = _out(output_file)
        runner.run_ffmpeg([
            "-i", str(source),
            "-filter_complex",
            f"showwavespic=s={width}x{height}:colors=white",
            "-frames:v", "1", str(target),
        ])
        info = runner.verify_output(target, expect_stream="video")
    except runner.FfmpegError as error:
        return f"ERROR: {error}"
    return json.dumps({"input": str(source.resolve()), **info}, indent=2)
