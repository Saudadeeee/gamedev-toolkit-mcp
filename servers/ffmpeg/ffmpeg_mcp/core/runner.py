"""Locating and driving ffmpeg/ffprobe.

Same model as the rfxgen and aseprite servers: one short-lived process per
call, no running application. Unlike rfxgen, ffmpeg's exit codes are honest --
but an output can still be silently wrong (zero-length stream, truncated
container), so every product is verified with ffprobe rather than trusted.
"""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

ENV_VAR = "FFMPEG_PATH"

_WINDOWS_CANDIDATES = [
    r"D:\Apps\ffmpeg\bin\ffmpeg.exe",
    r"C:\Apps\ffmpeg\bin\ffmpeg.exe",
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"%LOCALAPPDATA%\Programs\ffmpeg\bin\ffmpeg.exe",
    r"C:\Tools\ffmpeg\bin\ffmpeg.exe",
    r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
]
_POSIX_CANDIDATES = [
    "/usr/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
]

_cached: dict[str, str] = {}


class FfmpegError(RuntimeError):
    """Raised when a run failed or produced something that does not probe."""


def resolve_ffmpeg(refresh: bool = False) -> str | None:
    """Absolute path to ffmpeg, or None. FFMPEG_PATH wins outright."""
    if not refresh and _cached.get("ffmpeg") and Path(_cached["ffmpeg"]).is_file():
        return _cached["ffmpeg"]

    override = os.environ.get(ENV_VAR, "").strip()
    if override:
        expanded = os.path.expandvars(os.path.expanduser(override))
        # Accept either the binary itself or its directory.
        candidate = Path(expanded)
        if candidate.is_dir():
            candidate = candidate / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if candidate.is_file():
            _cached["ffmpeg"] = str(candidate)
            return _cached["ffmpeg"]
        # A set-but-wrong override is a configuration error worth surfacing.
        return None

    candidates = _WINDOWS_CANDIDATES if os.name == "nt" else _POSIX_CANDIDATES
    for raw in candidates:
        for match in sorted(glob.glob(os.path.expandvars(os.path.expanduser(raw)))):
            if Path(match).is_file():
                _cached["ffmpeg"] = match
                return match

    found = shutil.which("ffmpeg")
    if found:
        _cached["ffmpeg"] = found
    return found


def resolve_ffprobe() -> str | None:
    """ffprobe ships beside ffmpeg; look there first, then PATH."""
    if _cached.get("ffprobe") and Path(_cached["ffprobe"]).is_file():
        return _cached["ffprobe"]
    ffmpeg = resolve_ffmpeg()
    if ffmpeg:
        sibling = Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if sibling.is_file():
            _cached["ffprobe"] = str(sibling)
            return _cached["ffprobe"]
    found = shutil.which("ffprobe")
    if found:
        _cached["ffprobe"] = found
    return found


def run_ffmpeg(args: list[str], timeout: int = 300) -> str:
    """Run ffmpeg with args; return its log. Raises on failure or absence."""
    binary = resolve_ffmpeg()
    if binary is None:
        raise FfmpegError(
            f"ffmpeg not found. Set {ENV_VAR} or install it (https://ffmpeg.org)."
        )
    try:
        proc = subprocess.run(
            # -y: tools state their output path explicitly; interactive
            # overwrite prompts would hang a headless server.
            [binary, "-hide_banner", "-y", *args],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired as error:
        raise FfmpegError(f"ffmpeg timed out after {timeout}s") from error
    except OSError as error:
        raise FfmpegError(f"could not run ffmpeg: {error}") from error

    log = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        tail = "\n".join(log.splitlines()[-6:])
        raise FfmpegError(f"ffmpeg failed (exit {proc.returncode}):\n{tail}")
    return log


def probe(path: str | Path) -> dict:
    """ffprobe facts for a media file: format, duration, streams."""
    binary = resolve_ffprobe()
    if binary is None:
        raise FfmpegError("ffprobe not found beside ffmpeg or on PATH.")
    source = Path(path)
    if not source.is_file():
        raise FfmpegError(f"file not found: {source}")
    try:
        proc = subprocess.run(
            [binary, "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(source)],
            capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise FfmpegError(f"could not run ffprobe: {error}") from error
    if proc.returncode != 0:
        raise FfmpegError(f"ffprobe rejected {source.name}: {(proc.stderr or '').strip()[:200]}")
    try:
        return json.loads(proc.stdout)
    except ValueError:
        raise FfmpegError(f"ffprobe produced no JSON for {source.name}") from None


def media_summary(path: str | Path) -> dict:
    """The probe facts a tool result actually needs."""
    data = probe(path)
    fmt = data.get("format", {})
    summary: dict = {
        "path": str(Path(path).resolve()),
        "bytes": int(fmt.get("size", 0) or 0),
        "format": fmt.get("format_name", ""),
        "seconds": round(float(fmt.get("duration", 0) or 0), 3),
        "streams": [],
    }
    for stream in data.get("streams", []):
        kind = stream.get("codec_type")
        entry = {"type": kind, "codec": stream.get("codec_name")}
        if kind == "audio":
            entry.update(sample_rate=int(stream.get("sample_rate", 0) or 0),
                         channels=stream.get("channels"))
        elif kind == "video":
            entry.update(width=stream.get("width"), height=stream.get("height"),
                         fps=stream.get("avg_frame_rate"))
        summary["streams"].append(entry)
    return summary


def verify_output(path: str | Path, expect_stream: str | None = None) -> dict:
    """Prove a render produced real media; return its summary.

    expect_stream: 'audio' or 'video' -- the product must contain a non-empty
    stream of that kind. A container with zero streams probes cleanly, so
    "ffprobe accepted it" alone is not proof of content.
    """
    summary = media_summary(path)
    if summary["bytes"] < 64:
        raise FfmpegError(f"{path} is only {summary['bytes']} bytes -- render failed part-way.")
    if expect_stream:
        kinds = {s["type"] for s in summary["streams"]}
        if expect_stream not in kinds:
            raise FfmpegError(
                f"{path} contains no {expect_stream} stream (found: {sorted(kinds) or 'none'}).")
        if expect_stream == "audio" and summary["seconds"] <= 0:
            raise FfmpegError(f"{path} has an audio stream but zero duration.")
    return summary
