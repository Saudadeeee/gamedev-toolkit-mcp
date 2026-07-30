"""Unit tests. Deliberately need no rfxgen install -- pure logic only.

The suites that drive a real binary live in smoke_test.py, excluded from
collection in pyproject.toml.
"""

import random
import struct
import wave

import pytest

from rfxgen_mcp.core import rfx_format, runner
from rfxgen_mcp.core.rfx_format import (PARAM_RANGES, WAVE_TYPES, WaveParams,
                                        pack_rfx, params_from_kwargs,
                                        resolve_wave_type, unpack_rfx)


class TestRfxFormat:
    def test_pack_produces_the_documented_layout(self):
        blob = pack_rfx(WaveParams())
        assert blob[:4] == b"rFX "
        version, length = struct.unpack_from("<HH", blob, 4)
        assert (version, length) == (200, 96)
        assert len(blob) == 8 + 96

    def test_roundtrip_preserves_every_parameter(self):
        original = WaveParams(wave_type=2, start_frequency=0.73, slide=-0.41,
                              vibrato_depth=0.2, lpf_cutoff=0.5, hpf_cutoff=0.1)
        recovered = unpack_rfx(pack_rfx(original))
        assert recovered.wave_type == 2
        for name in PARAM_RANGES:
            assert getattr(recovered, name) == pytest.approx(getattr(original, name), abs=1e-6), name

    def test_pack_clamps_out_of_range_values(self):
        wild = WaveParams(start_frequency=7.0, slide=-9.0, wave_type=99)
        recovered = unpack_rfx(pack_rfx(wild))
        assert recovered.start_frequency == pytest.approx(1.0)
        assert recovered.slide == pytest.approx(-1.0)
        assert recovered.wave_type == len(WAVE_TYPES) - 1

    @pytest.mark.parametrize("blob,message", [
        (b"nope", "signature"),
        (b"rFX " + struct.pack("<HH", 100, 96) + b"\0" * 96, "version"),
        (b"rFX " + struct.pack("<HH", 200, 42) + b"\0" * 42, "length"),
    ])
    def test_unpack_rejects_garbage(self, blob, message):
        with pytest.raises(ValueError, match=message):
            unpack_rfx(blob)

    def test_bipolar_and_unipolar_ranges_are_as_documented(self):
        assert PARAM_RANGES["slide"] == (-1.0, 1.0)
        assert PARAM_RANGES["attack_time"] == (0.0, 1.0)
        # The struct order commitment: 22 floats exactly.
        assert len(PARAM_RANGES) == 22


class TestWaveType:
    def test_accepts_names_and_indices(self):
        assert resolve_wave_type("noise") == 3
        assert resolve_wave_type("SQUARE") == 0
        assert resolve_wave_type(1) == 1

    def test_rejects_unknown(self):
        with pytest.raises(ValueError):
            resolve_wave_type("triangle")
        with pytest.raises(ValueError):
            resolve_wave_type(4)


class TestParamsFromKwargs:
    def test_rejects_unknown_parameter_names(self):
        with pytest.raises(ValueError, match="unknown parameter"):
            params_from_kwargs({"frequency": 0.5})  # the right name is start_frequency

    def test_accepts_wave_type_by_name(self):
        params = params_from_kwargs({"wave_type": "sine", "decay_time": 0.5})
        assert params.wave_type == 2
        assert params.decay_time == pytest.approx(0.5)


class TestMutate:
    def test_same_seed_same_variation(self):
        base = params_from_kwargs({"wave_type": "square", "start_frequency": 0.5})
        a = rfx_format.mutate(base, 0.2, random.Random(7))
        b = rfx_format.mutate(base, 0.2, random.Random(7))
        assert pack_rfx(a) == pack_rfx(b)

    def test_keeps_wave_type_and_stays_in_range(self):
        base = params_from_kwargs({"wave_type": "noise", "start_frequency": 0.99})
        for seed in range(20):
            variant = rfx_format.mutate(base, 0.5, random.Random(seed))
            assert variant.wave_type == base.wave_type
            for name, (lo, hi) in PARAM_RANGES.items():
                assert lo <= getattr(variant, name) <= hi, name

    def test_zero_amount_is_identity(self):
        base = params_from_kwargs({"start_frequency": 0.42, "slide": -0.3})
        assert pack_rfx(rfx_format.mutate(base, 0.0, random.Random(1))) == pack_rfx(base)


class TestFormatArgs:
    def test_empty_when_nothing_given(self):
        assert runner.format_args(None, None, None) == []

    def test_fills_defaults_when_partial(self):
        assert runner.format_args(22050, None, None) == ["--format", "22050,16,1"]

    @pytest.mark.parametrize("kwargs", [
        {"sample_rate": 48000}, {"bits": 24}, {"channels": 3},
    ])
    def test_rejects_unsupported_values(self, kwargs):
        merged = {"sample_rate": None, "bits": None, "channels": None, **kwargs}
        with pytest.raises(ValueError):
            runner.format_args(**merged)


class TestVerifyOutput:
    """rfxgen exits 0 no matter what, so this IS the success check."""

    def test_missing_file_is_an_error_that_explains_the_tool(self, tmp_path):
        with pytest.raises(runner.RfxgenError, match="reports nothing on"):
            runner.verify_output(tmp_path / "never_written.wav")

    def test_truncated_file_is_an_error(self, tmp_path):
        stub = tmp_path / "tiny.wav"
        stub.write_bytes(b"RIFF")
        with pytest.raises(runner.RfxgenError, match="bytes"):
            runner.verify_output(stub)

    def test_non_wav_bytes_are_an_error(self, tmp_path):
        fake = tmp_path / "fake.wav"
        fake.write_bytes(b"x" * 1000)
        with pytest.raises(runner.RfxgenError, match="not a valid WAV"):
            runner.verify_output(fake)

    def test_valid_wav_reports_its_facts(self, tmp_path):
        path = tmp_path / "ok.wav"
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(44100)
            handle.writeframes(b"\0\1" * 4410)
        info = runner.verify_output(path)
        assert info["sample_rate"] == 44100
        assert info["seconds"] == pytest.approx(0.1)

    def test_non_wav_extension_only_checks_size(self, tmp_path):
        raw = tmp_path / "sound.raw"
        raw.write_bytes(b"\0" * 500)
        assert runner.verify_output(raw)["bytes"] == 500


class TestResolveRfxgen:
    def test_wrong_env_override_does_not_fall_through(self, tmp_path, monkeypatch):
        """A set-but-wrong RFXGEN_PATH is a config error, not a shrug.

        Falling back to auto-detection would silently use a different binary
        than the one the user pointed at.
        """
        monkeypatch.setenv(runner.ENV_VAR, str(tmp_path / "not_there.exe"))
        monkeypatch.setattr(runner, "_cached_path", None)
        assert runner.resolve_rfxgen(refresh=True) is None

    def test_env_override_wins(self, tmp_path, monkeypatch):
        fake = tmp_path / "rfxgen.exe"
        fake.write_bytes(b"MZ")
        monkeypatch.setenv(runner.ENV_VAR, str(fake))
        monkeypatch.setattr(runner, "_cached_path", None)
        assert runner.resolve_rfxgen(refresh=True) == str(fake)

    def test_missing_binary_raises_with_guidance(self, monkeypatch):
        monkeypatch.setattr(runner, "resolve_rfxgen", lambda refresh=False: None)
        with pytest.raises(runner.RfxgenError, match="RFXGEN_PATH"):
            runner.run_rfxgen(["--help"])


class TestToolRegistration:
    def test_every_tool_registers_without_duplicates(self):
        import anyio

        from rfxgen_mcp import mcp
        import rfxgen_mcp.tools  # noqa: F401

        names = [t.name for t in anyio.run(mcp.list_tools)]
        assert len(names) == len(set(names)), "duplicate tool names"
        expected = {"get_rfxgen_info", "generate_preset", "design_sound",
                    "generate_variations", "describe_sound_params",
                    "convert_audio", "export_wave_header", "get_sound_info"}
        assert expected <= set(names)
