"""Sound synthesis: presets, full parametric design, and variations.

The CLI presets are deterministic -- identical bytes every run -- so
design_sound and generate_variations are where the range comes from: they
author .rfx parameter files (see core/rfx_format.py) and render them.
"""

from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path

from .. import mcp
from ..core import rfx_format, runner
from ..core.rfx_format import (DESIGN_STARTING_POINTS, PARAM_DOCS, PARAM_RANGES,
                               WAVE_TYPES, WaveParams)

CLI_PRESETS = ("coin", "laser", "explosion", "powerup", "hit", "jump", "blip")


def _render_params(params: WaveParams, output: str,
                   sample_rate: int | None, bits: int | None, channels: int | None,
                   keep_rfx: str | None = None) -> dict:
    """Write params to .rfx, render to output, verify, clean up."""
    fmt = runner.format_args(sample_rate, bits, channels)
    if keep_rfx:
        rfx_path = rfx_format.write_rfx(keep_rfx, params)
        info = runner.run_and_verify(
            ["--input", str(rfx_path), "--output", output, *fmt], output)
        info["rfx"] = str(rfx_path.resolve())
        return info

    with tempfile.TemporaryDirectory(prefix="rfxgen-") as scratch:
        rfx_path = rfx_format.write_rfx(Path(scratch) / "sound.rfx", params)
        return runner.run_and_verify(
            ["--input", str(rfx_path), "--output", output, *fmt], output)


@mcp.tool()
def get_rfxgen_info() -> str:
    """Report the rfxgen binary this server will use and whether it works.

    Run this first when a generation tool fails.
    """
    binary = runner.resolve_rfxgen(refresh=True)
    if binary is None:
        return json.dumps({
            "found": False,
            "note": f"rfxgen not found. Set {runner.ENV_VAR} to the executable path.",
        }, indent=2)
    output = runner.run_rfxgen(["--help"], timeout=30)
    version = next((line.strip("/ ").strip() for line in output.splitlines()
                    if "rFXGen v" in line), "")
    return json.dumps({
        "found": True,
        "path": binary,
        "version": version or "unknown",
        "reachable": bool(output),
        "note": "Spawned per call; no running application needed.",
    }, indent=2)


@mcp.tool()
def generate_preset(preset: str, output_file: str,
                    sample_rate: int | None = None, bits: int | None = None,
                    channels: int | None = None) -> str:
    """Generate a sound from one of rfxgen's built-in presets.

    Presets: coin, laser, explosion, powerup, hit, jump, blip. Deterministic --
    the same preset always renders the same audio. For variety, use
    design_sound or generate_variations instead.

    output_file extension picks the format: .wav, .qoa, .raw, or .h (C array).
    """
    preset = preset.strip().lower()
    if preset not in CLI_PRESETS:
        return f"ERROR: unknown preset {preset!r}. Valid: {', '.join(CLI_PRESETS)}"
    try:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        fmt = runner.format_args(sample_rate, bits, channels)
        info = runner.run_and_verify(
            ["--generate", preset, "--output", output_file, *fmt], output_file)
    except (runner.RfxgenError, ValueError) as error:
        return f"ERROR: {error}"
    return json.dumps({"preset": preset, **info}, indent=2)


@mcp.tool()
def design_sound(output_file: str,
                 wave_type: str = "square",
                 starting_point: str | None = None,
                 params: dict | None = None,
                 save_rfx: str | None = None,
                 sample_rate: int | None = None, bits: int | None = None,
                 channels: int | None = None) -> str:
    """Design a sound from explicit synthesis parameters and render it.

    This is the full instrument: 22 float parameters plus a wave type
    (square, sawtooth, sine, noise). Call describe_sound_params for what each
    does and its range; out-of-range values are clamped, not rejected.

    starting_point optionally seeds the parameters from a named recipe
    (pickup, laser, explosion, powerup, hurt, jump, blip); anything in params
    then overrides it. save_rfx additionally writes the .rfx parameter file so
    the sound can be reloaded, tweaked, or varied later.
    """
    try:
        base: dict = {}
        if starting_point:
            recipe = DESIGN_STARTING_POINTS.get(starting_point.strip().lower())
            if recipe is None:
                return (f"ERROR: unknown starting_point {starting_point!r}. "
                        f"Valid: {', '.join(DESIGN_STARTING_POINTS)}")
            base.update(recipe)
        else:
            base["wave_type"] = wave_type
        if params:
            base.update(params)
        wave = rfx_format.params_from_kwargs(base)

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        info = _render_params(wave, output_file, sample_rate, bits, channels,
                              keep_rfx=save_rfx)
    except (runner.RfxgenError, ValueError) as error:
        return f"ERROR: {error}"
    return json.dumps({
        "wave_type": WAVE_TYPES[wave.wave_type],
        "parameters": {name: round(getattr(wave, name), 4) for name in PARAM_RANGES},
        **info,
    }, indent=2)


@mcp.tool()
def generate_variations(output_dir: str, count: int = 4,
                        mutation_amount: float = 0.15,
                        base_rfx: str | None = None,
                        starting_point: str | None = None,
                        params: dict | None = None,
                        seed: int | None = None,
                        sample_rate: int | None = None, bits: int | None = None,
                        channels: int | None = None) -> str:
    """Render several nearby variations of one sound, for picking the best.

    The base comes from base_rfx (a saved .rfx file), a starting_point recipe,
    or explicit params -- in that priority order. Each variation nudges every
    parameter within +/- mutation_amount of its range (wave type is kept).
    Writes variation_01.wav .. variation_NN.wav plus the matching .rfx files,
    so the chosen one can be reloaded exactly.
    """
    if not 1 <= count <= 16:
        return "ERROR: count must be between 1 and 16"
    try:
        if base_rfx:
            base = rfx_format.read_rfx(base_rfx)
        else:
            merged: dict = {}
            if starting_point:
                recipe = DESIGN_STARTING_POINTS.get(starting_point.strip().lower())
                if recipe is None:
                    return (f"ERROR: unknown starting_point {starting_point!r}. "
                            f"Valid: {', '.join(DESIGN_STARTING_POINTS)}")
                merged.update(recipe)
            merged.update(params or {})
            if not merged:
                return ("ERROR: give me a base -- base_rfx, starting_point, or params. "
                        "Mutating silence produces silence.")
            base = rfx_format.params_from_kwargs(merged)

        rng = random.Random(seed)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for index in range(1, count + 1):
            variant = rfx_format.mutate(base, mutation_amount, rng)
            stem = out_dir / f"variation_{index:02d}"
            rfx_format.write_rfx(stem.with_suffix(".rfx"), variant)
            fmt = runner.format_args(sample_rate, bits, channels)
            info = runner.run_and_verify(
                ["--input", str(stem.with_suffix('.rfx')), "--output",
                 str(stem.with_suffix('.wav')), *fmt],
                stem.with_suffix(".wav"))
            results.append({"rfx": str(stem.with_suffix('.rfx')),
                            "seconds": info.get("seconds"), **{k: info[k] for k in ("path", "bytes")}})
    except (runner.RfxgenError, ValueError) as error:
        return f"ERROR: {error}"
    return json.dumps({
        "base_wave_type": WAVE_TYPES[base.wave_type],
        "mutation_amount": mutation_amount,
        "variations": results,
    }, indent=2)


@mcp.tool()
def describe_sound_params(starting_point: str | None = None) -> str:
    """The full parameter reference for design_sound, as JSON.

    Give a starting_point name to also see that recipe's values -- useful as a
    baseline to tweak from.
    """
    doc = {
        "wave_types": list(WAVE_TYPES),
        "parameters": {
            name: {"range": list(PARAM_RANGES[name]), "doc": PARAM_DOCS[name]}
            for name in PARAM_RANGES
        },
        "starting_points": {name: dict(recipe)
                            for name, recipe in DESIGN_STARTING_POINTS.items()},
    }
    if starting_point:
        recipe = DESIGN_STARTING_POINTS.get(starting_point.strip().lower())
        if recipe is None:
            return (f"ERROR: unknown starting_point {starting_point!r}. "
                    f"Valid: {', '.join(DESIGN_STARTING_POINTS)}")
        doc["selected"] = {"name": starting_point, **recipe}
    return json.dumps(doc, indent=2)
