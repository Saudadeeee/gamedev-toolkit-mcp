"""Locating and driving the rfxgen binary.

rfxgen is a console application: every operation is one short-lived process,
the same model as the aseprite server. No running instance is needed.

The trap this module exists for: rfxgen exits 0 no matter what. A bad preset
name, an unreadable input, an unwritable output -- all exit 0, print nothing,
and write nothing. The exit code carries no information, so the only honest
check is the output file itself: it must exist, be non-trivial, and (for .wav)
parse as a WAV with actual frames in it. Every render goes through
run_and_verify; nothing trusts the exit code alone.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import wave
from pathlib import Path

ENV_VAR = "RFXGEN_PATH"

_WINDOWS_CANDIDATES = [
    r"D:\Apps\rfxgen\rfxgen.exe",
    r"C:\Apps\rfxgen\rfxgen.exe",
    r"C:\Program Files\rfxgen\rfxgen.exe",
    r"C:\Program Files (x86)\rfxgen\rfxgen.exe",
    r"%LOCALAPPDATA%\Programs\rfxgen\rfxgen.exe",
    r"C:\Tools\rfxgen\rfxgen.exe",
    r"D:\Tools\rfxgen\rfxgen.exe",
]
_POSIX_CANDIDATES = [
    "/usr/local/bin/rfxgen",
    "/usr/bin/rfxgen",
    "~/Applications/rfxgen/rfxgen",
    "/opt/rfxgen/rfxgen",
]

_cached_path: str | None = None


def resolve_rfxgen(refresh: bool = False) -> str | None:
    """Absolute path to the rfxgen binary, or None.

    RFXGEN_PATH wins outright; then known install locations; then PATH.
    """
    global _cached_path
    if _cached_path and not refresh and Path(_cached_path).is_file():
        return _cached_path

    override = os.environ.get(ENV_VAR, "").strip()
    if override:
        expanded = os.path.expandvars(os.path.expanduser(override))
        if Path(expanded).is_file():
            _cached_path = expanded
            return expanded
        # A set-but-wrong override is a configuration error worth surfacing,
        # not something to silently fall past.
        return None

    candidates = _WINDOWS_CANDIDATES if os.name == "nt" else _POSIX_CANDIDATES
    for raw in candidates:
        pattern = os.path.expandvars(os.path.expanduser(raw))
        for match in sorted(glob.glob(pattern)):
            if Path(match).is_file():
                _cached_path = match
                return match

    found = shutil.which("rfxgen")
    if found:
        _cached_path = found
    return found


class RfxgenError(RuntimeError):
    """Raised when a render did not produce what it claimed to."""


def run_rfxgen(args: list[str], timeout: int = 60) -> str:
    """Run rfxgen with args and return its combined output. Raises if absent."""
    binary = resolve_rfxgen()
    if binary is None:
        raise RfxgenError(
            f"rfxgen not found. Set {ENV_VAR} to the executable, or install it "
            "from https://raysan5.itch.io/rfxgen / github.com/raysan5/rfxgen"
        )
    try:
        proc = subprocess.run(
            [binary, *args], capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
            # rfxgen resolves relative output paths against its cwd; pin it so
            # tool-relative paths behave predictably.
            cwd=str(Path.cwd()),
        )
    except subprocess.TimeoutExpired as error:
        raise RfxgenError(f"rfxgen timed out after {timeout}s: {' '.join(args)}") from error
    except OSError as error:
        raise RfxgenError(f"could not run rfxgen: {error}") from error
    return ((proc.stdout or "") + (proc.stderr or "")).strip()


def verify_output(path: str | Path, *, min_bytes: int = 64) -> dict:
    """Prove a render produced a real file; return facts about it.

    rfxgen's exit code is always 0, so this is the actual success check.
    """
    path = Path(path)
    if not path.is_file():
        raise RfxgenError(
            f"rfxgen exited without writing {path}. It reports nothing on "
            "failure -- check the preset/parameter names and that the output "
            "directory exists."
        )
    size = path.stat().st_size
    if size < min_bytes:
        raise RfxgenError(f"{path} is only {size} bytes -- the render failed part-way.")

    info: dict = {"path": str(path.resolve()), "bytes": size}
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path)) as handle:
                frames = handle.getnframes()
                rate = handle.getframerate()
                info.update(
                    sample_rate=rate,
                    bits=handle.getsampwidth() * 8,
                    channels=handle.getnchannels(),
                    frames=frames,
                    seconds=round(frames / rate, 3) if rate else 0.0,
                )
        except wave.Error as error:
            raise RfxgenError(f"{path} is not a valid WAV: {error}") from None
        if info["frames"] == 0:
            raise RfxgenError(f"{path} parsed as WAV but contains zero frames.")
    return info


def run_and_verify(args: list[str], output: str | Path, timeout: int = 60) -> dict:
    """One render, honestly checked. Returns verify_output's facts."""
    log = run_rfxgen(args, timeout=timeout)
    try:
        return verify_output(output)
    except RfxgenError as error:
        detail = f" rfxgen output: {log[-300:]}" if log else ""
        raise RfxgenError(f"{error}{detail}") from None


def format_args(sample_rate: int | None, bits: int | None, channels: int | None) -> list[str]:
    """--format arguments, validated against what rfxgen accepts."""
    if sample_rate is None and bits is None and channels is None:
        return []
    sample_rate = sample_rate or 44100
    bits = bits or 16
    channels = channels or 1
    if sample_rate not in (22050, 44100):
        raise ValueError("sample_rate must be 22050 or 44100")
    if bits not in (8, 16, 32):
        raise ValueError("bits must be 8, 16 or 32")
    if channels not in (1, 2):
        raise ValueError("channels must be 1 (mono) or 2 (stereo)")
    return ["--format", f"{sample_rate},{bits},{channels}"]
