"""The .rfx parameter file format, and the parameter space behind it.

An .rfx file is rfxgen's saved sound: a 8-byte header followed by the raw
WaveParams struct. Verified against rfxgen v5.0 source (src/rfxgen.h,
SaveWaveParams) and empirically -- a file written by this module renders
through `rfxgen --input` to real audio.

    offset | size | contents
    -------+------+------------------------------------
    0      | 4    | signature "rFX "
    4      | 2    | version, little-endian u16 (200)
    6      | 2    | payload length (96 = sizeof WaveParams)
    8      | 96   | WaveParams: 2 x int32 + 22 x float32, little-endian

The CLI presets are deterministic -- the same seven sounds every run -- so
authoring these files is what turns rfxgen into an instrument rather than a
jukebox: 24 parameters of square/sawtooth/sine/noise synthesis, sfxr-style.
"""

from __future__ import annotations

import random
import struct
from dataclasses import dataclass, field
from pathlib import Path

SIGNATURE = b"rFX "
VERSION = 200
PAYLOAD_LENGTH = 96

WAVE_TYPES = ("square", "sawtooth", "sine", "noise")

# Parameter ranges, sfxr conventions: most are unipolar [0, 1]; the sweep and
# slide parameters are bipolar [-1, 1]. Order here IS the struct order -- do
# not reorder.
_UNIPOLAR = (0.0, 1.0)
_BIPOLAR = (-1.0, 1.0)

PARAM_RANGES: dict[str, tuple[float, float]] = {
    "attack_time": _UNIPOLAR,
    "sustain_time": _UNIPOLAR,
    "sustain_punch": _UNIPOLAR,
    "decay_time": _UNIPOLAR,
    "start_frequency": _UNIPOLAR,
    "min_frequency": _UNIPOLAR,
    "slide": _BIPOLAR,
    "delta_slide": _BIPOLAR,
    "vibrato_depth": _UNIPOLAR,
    "vibrato_speed": _UNIPOLAR,
    "change_amount": _BIPOLAR,
    "change_speed": _UNIPOLAR,
    "square_duty": _UNIPOLAR,
    "duty_sweep": _BIPOLAR,
    "repeat_speed": _UNIPOLAR,
    "phaser_offset": _BIPOLAR,
    "phaser_sweep": _BIPOLAR,
    "lpf_cutoff": _UNIPOLAR,
    "lpf_cutoff_sweep": _BIPOLAR,
    "lpf_resonance": _UNIPOLAR,
    "hpf_cutoff": _UNIPOLAR,
    "hpf_cutoff_sweep": _BIPOLAR,
}

PARAM_DOCS: dict[str, str] = {
    "attack_time": "Fade-in time before the sound reaches full volume.",
    "sustain_time": "How long the sound holds at full volume.",
    "sustain_punch": "Extra loudness spike at the start of the sustain.",
    "decay_time": "Fade-out time. The main lever for how long a sound feels.",
    "start_frequency": "Base pitch. ~0.2 is a low rumble, ~0.8 a bright zap.",
    "min_frequency": "Pitch floor; a downward slide stops (cuts off) here.",
    "slide": "Pitch glide per unit time. Negative = falling (laser), positive = rising (powerup).",
    "delta_slide": "Acceleration applied to the slide itself.",
    "vibrato_depth": "Pitch wobble amount.",
    "vibrato_speed": "Pitch wobble rate.",
    "change_amount": "Size of a sudden mid-sound pitch jump (coin pickups use a positive jump).",
    "change_speed": "How soon the pitch jump happens.",
    "square_duty": "Square wave pulse width; only audible on wave_type=square.",
    "duty_sweep": "Pulse-width drift over time; square wave only.",
    "repeat_speed": "Retriggers the sound from its start at this rate (machine-gun effect).",
    "phaser_offset": "Phaser comb-filter offset; gives metallic flavour.",
    "phaser_sweep": "Phaser offset drift over time.",
    "lpf_cutoff": "Low-pass filter cutoff; below 1.0 darkens the sound.",
    "lpf_cutoff_sweep": "Low-pass cutoff drift over time.",
    "lpf_resonance": "Emphasis at the low-pass cutoff; whistly when high.",
    "hpf_cutoff": "High-pass filter cutoff; above 0 thins the sound.",
    "hpf_cutoff_sweep": "High-pass cutoff drift over time.",
}


@dataclass
class WaveParams:
    """One rfxgen sound, in authoring order. All floats are clamped on pack."""

    wave_type: int = 0  # index into WAVE_TYPES
    rand_seed: int = 0
    attack_time: float = 0.0
    sustain_time: float = 0.3
    sustain_punch: float = 0.0
    decay_time: float = 0.4
    start_frequency: float = 0.3
    min_frequency: float = 0.0
    slide: float = 0.0
    delta_slide: float = 0.0
    vibrato_depth: float = 0.0
    vibrato_speed: float = 0.0
    change_amount: float = 0.0
    change_speed: float = 0.0
    square_duty: float = 0.0
    duty_sweep: float = 0.0
    repeat_speed: float = 0.0
    phaser_offset: float = 0.0
    phaser_sweep: float = 0.0
    lpf_cutoff: float = 1.0
    lpf_cutoff_sweep: float = 0.0
    lpf_resonance: float = 0.0
    hpf_cutoff: float = 0.0
    hpf_cutoff_sweep: float = 0.0
    _extra: dict = field(default_factory=dict, repr=False)

    def clamped(self) -> "WaveParams":
        """A copy with every parameter forced into its legal range."""
        values = {}
        for name, (lo, hi) in PARAM_RANGES.items():
            values[name] = min(hi, max(lo, float(getattr(self, name))))
        return WaveParams(
            wave_type=min(len(WAVE_TYPES) - 1, max(0, int(self.wave_type))),
            rand_seed=int(self.rand_seed),
            **values,
        )


def resolve_wave_type(value: int | str) -> int:
    """Accept either an index or a name for the wave type."""
    if isinstance(value, str):
        name = value.strip().lower()
        if name not in WAVE_TYPES:
            raise ValueError(f"unknown wave type {value!r}; use one of {WAVE_TYPES}")
        return WAVE_TYPES.index(name)
    index = int(value)
    if not 0 <= index < len(WAVE_TYPES):
        raise ValueError(f"wave type index {index} out of range 0..{len(WAVE_TYPES) - 1}")
    return index


def pack_rfx(params: WaveParams) -> bytes:
    """The complete .rfx file for these parameters."""
    p = params.clamped()
    payload = struct.pack("<ii", p.rand_seed, p.wave_type)
    payload += struct.pack(f"<{len(PARAM_RANGES)}f",
                           *(getattr(p, name) for name in PARAM_RANGES))
    assert len(payload) == PAYLOAD_LENGTH
    return SIGNATURE + struct.pack("<HH", VERSION, PAYLOAD_LENGTH) + payload


def unpack_rfx(blob: bytes) -> WaveParams:
    """Parse an .rfx file back into parameters. Raises ValueError on garbage."""
    if len(blob) < 8 or blob[:4] != SIGNATURE:
        raise ValueError("not an .rfx file (missing 'rFX ' signature)")
    version, length = struct.unpack_from("<HH", blob, 4)
    if version != VERSION:
        raise ValueError(f"unsupported .rfx version {version} (expected {VERSION})")
    if length != PAYLOAD_LENGTH or len(blob) < 8 + PAYLOAD_LENGTH:
        raise ValueError(f"bad payload length {length} (expected {PAYLOAD_LENGTH})")

    rand_seed, wave_type = struct.unpack_from("<ii", blob, 8)
    floats = struct.unpack_from(f"<{len(PARAM_RANGES)}f", blob, 16)
    return WaveParams(wave_type=wave_type, rand_seed=rand_seed,
                      **dict(zip(PARAM_RANGES, floats)))


def write_rfx(path: str | Path, params: WaveParams) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pack_rfx(params))
    return path


def read_rfx(path: str | Path) -> WaveParams:
    return unpack_rfx(Path(path).read_bytes())


def mutate(params: WaveParams, amount: float, rng: random.Random) -> WaveParams:
    """A nearby variation: each parameter nudged within +/- amount of its range.

    The wave type is kept -- changing it produces a different sound, not a
    variation of this one. Results are clamped, so amount can be generous.
    """
    values = {}
    for name, (lo, hi) in PARAM_RANGES.items():
        span = (hi - lo) * amount
        values[name] = getattr(params, name) + rng.uniform(-span, span)
    return WaveParams(wave_type=params.wave_type, rand_seed=params.rand_seed,
                      **values).clamped()


def params_from_kwargs(values: dict) -> WaveParams:
    """Build WaveParams from tool arguments, rejecting unknown names."""
    unknown = set(values) - set(PARAM_RANGES) - {"wave_type", "rand_seed"}
    if unknown:
        raise ValueError(f"unknown parameter(s): {sorted(unknown)}; "
                         f"valid: wave_type, {', '.join(PARAM_RANGES)}")
    kwargs = dict(values)
    if "wave_type" in kwargs:
        kwargs["wave_type"] = resolve_wave_type(kwargs["wave_type"])
    return WaveParams(**kwargs).clamped()


# Preset parameter sets, for describe_sound_params and as design starting
# points. These are illustrative sfxr-style starting values, not copies of the
# CLI presets -- the CLI renders its own.
DESIGN_STARTING_POINTS: dict[str, dict] = {
    "pickup": {"wave_type": "square", "start_frequency": 0.6, "change_amount": 0.4,
               "change_speed": 0.5, "sustain_time": 0.1, "decay_time": 0.35},
    "laser": {"wave_type": "square", "start_frequency": 0.8, "slide": -0.3,
              "sustain_time": 0.15, "decay_time": 0.2},
    "explosion": {"wave_type": "noise", "start_frequency": 0.12, "sustain_time": 0.3,
                  "sustain_punch": 0.5, "decay_time": 0.6, "phaser_offset": 0.3},
    "powerup": {"wave_type": "sawtooth", "start_frequency": 0.3, "slide": 0.25,
                "sustain_time": 0.4, "decay_time": 0.4},
    "hurt": {"wave_type": "noise", "start_frequency": 0.5, "slide": -0.4,
             "sustain_time": 0.08, "decay_time": 0.18},
    "jump": {"wave_type": "square", "start_frequency": 0.35, "slide": 0.2,
             "square_duty": 0.4, "sustain_time": 0.2, "decay_time": 0.25},
    "blip": {"wave_type": "square", "start_frequency": 0.5, "sustain_time": 0.05,
             "decay_time": 0.12},
}
