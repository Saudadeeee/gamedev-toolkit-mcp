"""Audio conversion and inspection through rfxgen's processing pipeline.

rfxgen reads .rfx, .wav, .qoa, .ogg, .flac and .mp3, and writes .wav, .qoa,
.raw and .h -- which makes it a small format/resample bridge for game audio
even when the sound came from somewhere else (Audacity, a download, a
recording).
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import mcp
from ..core import rfx_format, runner

_INPUT_EXTS = {".rfx", ".wav", ".qoa", ".ogg", ".flac", ".mp3"}
_OUTPUT_EXTS = {".wav", ".qoa", ".raw", ".h"}


@mcp.tool()
def convert_audio(input_file: str, output_file: str,
                  sample_rate: int | None = None, bits: int | None = None,
                  channels: int | None = None) -> str:
    """Convert or resample audio through rfxgen.

    Input: .rfx, .wav, .qoa, .ogg, .flac, .mp3. Output: .wav, .qoa, .raw, .h.
    Format defaults to 44100 Hz / 16-bit / mono when not given; sample_rate
    must be 22050 or 44100, bits 8/16/32, channels 1/2.
    """
    source = Path(input_file)
    if not source.is_file():
        return f"ERROR: input file not found: {source}"
    if source.suffix.lower() not in _INPUT_EXTS:
        return f"ERROR: unsupported input {source.suffix!r}; rfxgen reads {sorted(_INPUT_EXTS)}"
    if Path(output_file).suffix.lower() not in _OUTPUT_EXTS:
        return f"ERROR: unsupported output {Path(output_file).suffix!r}; rfxgen writes {sorted(_OUTPUT_EXTS)}"
    try:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        fmt = runner.format_args(sample_rate, bits, channels)
        info = runner.run_and_verify(
            ["--input", str(source), "--output", output_file, *fmt], output_file)
    except (runner.RfxgenError, ValueError) as error:
        return f"ERROR: {error}"
    return json.dumps({"input": str(source.resolve()), **info}, indent=2)


@mcp.tool()
def export_wave_header(input_file: str, output_file: str) -> str:
    """Export a sound as a C header (.h) with the wave embedded as an array.

    For engines or jam entries that compile assets straight in. The input can
    be an .rfx parameter file or any audio format rfxgen reads.
    """
    if not output_file.lower().endswith(".h"):
        return "ERROR: output_file must end in .h"
    return convert_audio(input_file, output_file)


@mcp.tool()
def get_sound_info(file: str) -> str:
    """Inspect a .wav or .rfx file: format facts for audio, parameters for .rfx.

    The verification companion to the generation tools -- "rendered
    successfully" only means rfxgen ran; this is how to see what came out.
    """
    path = Path(file)
    if not path.is_file():
        return f"ERROR: file not found: {path}"

    if path.suffix.lower() == ".rfx":
        try:
            params = rfx_format.read_rfx(path)
        except ValueError as error:
            return f"ERROR: {error}"
        return json.dumps({
            "path": str(path.resolve()),
            "wave_type": rfx_format.WAVE_TYPES[
                min(len(rfx_format.WAVE_TYPES) - 1, max(0, params.wave_type))],
            "parameters": {name: round(getattr(params, name), 4)
                           for name in rfx_format.PARAM_RANGES},
        }, indent=2)

    try:
        info = runner.verify_output(path)
    except runner.RfxgenError as error:
        return f"ERROR: {error}"
    return json.dumps(info, indent=2)
