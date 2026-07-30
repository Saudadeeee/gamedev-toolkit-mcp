"""Video and GIF tools: turning captures into shareable clips.

godot-mcp's capture tools produce stills and the engine can record movies;
these turn that raw material into devlog GIFs, trailer clips and reference
frames.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import mcp
from ..core import runner


def _out(path: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


@mcp.tool()
def make_gif(input_file: str, output_file: str,
             fps: int = 15, width: int | None = 480,
             start: float = 0.0, duration: float | None = None) -> str:
    """Turn a video (or image sequence pattern like frame_%04d.png) into an
    optimized GIF.

    Two-pass palette generation, so the result looks right for pixel art
    instead of dither soup. width scales proportionally (None keeps source
    size); fps 10-15 is plenty for a devlog GIF.
    """
    if not output_file.lower().endswith(".gif"):
        return "ERROR: output_file must end in .gif"
    if not 1 <= fps <= 50:
        return "ERROR: fps must be 1..50"
    is_sequence = "%" in Path(input_file).name
    if not is_sequence and not Path(input_file).is_file():
        return f"ERROR: input file not found: {input_file}"
    try:
        scale = f",scale={width}:-1:flags=neighbor" if width else ""
        args: list[str] = []
        if start > 0:
            args += ["-ss", str(start)]
        if duration is not None:
            args += ["-t", str(duration)]
        if is_sequence:
            args += ["-framerate", str(fps)]
        args += ["-i", input_file]
        # Palette in one pass via split; neighbor scaling keeps pixels crisp.
        args += ["-filter_complex",
                 f"[0:v]fps={fps}{scale},split[a][b];"
                 f"[a]palettegen=stats_mode=diff[p];"
                 f"[b][p]paletteuse=dither=bayer:bayer_scale=3"]
        target = _out(output_file)
        runner.run_ffmpeg([*args, str(target)])
        info = runner.verify_output(target, expect_stream="video")
    except runner.FfmpegError as error:
        return f"ERROR: {error}"
    return json.dumps({"input": input_file, "fps": fps, **info}, indent=2)


@mcp.tool()
def make_video(input_pattern: str, output_file: str,
               fps: int = 30, width: int | None = None,
               crf: int = 23) -> str:
    """Assemble an image sequence (frame_%04d.png) or re-encode a video into
    .webm or .mp4 -- trailer clips from engine captures.

    crf: quality, lower is better (18 near-lossless, 23 default, 30 small).
    Pixel-art scaling uses nearest-neighbour so sprites stay crisp.
    """
    suffix = Path(output_file).suffix.lower()
    if suffix not in (".webm", ".mp4"):
        return "ERROR: output_file must end in .webm or .mp4"
    if not 1 <= fps <= 120:
        return "ERROR: fps must be 1..120"
    if not 0 <= crf <= 51:
        return "ERROR: crf must be 0..51"
    is_sequence = "%" in Path(input_pattern).name
    if not is_sequence and not Path(input_pattern).is_file():
        return f"ERROR: input not found: {input_pattern}"
    try:
        args: list[str] = []
        if is_sequence:
            args += ["-framerate", str(fps)]
        args += ["-i", input_pattern]
        if width:
            args += ["-vf", f"scale={width}:-2:flags=neighbor"]
        if suffix == ".webm":
            args += ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", str(crf)]
        else:
            # yuv420p: without it, players (and itch embeds) refuse the file.
            args += ["-c:v", "libx264", "-crf", str(crf), "-pix_fmt", "yuv420p"]
        target = _out(output_file)
        runner.run_ffmpeg([*args, str(target)])
        info = runner.verify_output(target, expect_stream="video")
    except runner.FfmpegError as error:
        return f"ERROR: {error}"
    return json.dumps({"input": input_pattern, "fps": fps, "crf": crf, **info}, indent=2)


@mcp.tool()
def extract_frames(input_file: str, output_pattern: str,
                   fps: float | None = None, start: float = 0.0,
                   duration: float | None = None) -> str:
    """Pull still frames out of a video, as PNGs.

    output_pattern needs a frame number slot, e.g. ref_%03d.png. Use fps=1 for
    one frame per second, or omit fps for every frame. The bridge into
    aseprite: extract reference frames, then import_image_as_layer to
    rotoscope or study motion.
    """
    source = Path(input_file)
    if not source.is_file():
        return f"ERROR: input file not found: {source}"
    if "%" not in Path(output_pattern).name:
        return "ERROR: output_pattern needs a %d slot, e.g. frames/ref_%03d.png"
    try:
        args = []
        if start > 0:
            args += ["-ss", str(start)]
        args += ["-i", str(source)]
        if duration is not None:
            args += ["-t", str(duration)]
        if fps:
            args += ["-vf", f"fps={fps}"]
        target_dir = Path(output_pattern).parent
        target_dir.mkdir(parents=True, exist_ok=True)
        runner.run_ffmpeg([*args, output_pattern])
        written = sorted(target_dir.glob(
            Path(output_pattern).name.replace("%03d", "*").replace("%04d", "*").replace("%d", "*")))
        if not written:
            return "ERROR: ffmpeg ran but wrote no frames -- check start/duration against the clip length"
    except runner.FfmpegError as error:
        return f"ERROR: {error}"
    return json.dumps({
        "input": str(source.resolve()),
        "frames_written": len(written),
        "first": str(written[0]),
        "last": str(written[-1]),
    }, indent=2)
