"""Unit tests. Deliberately need no ffmpeg install -- pure logic only.

The suite that drives a real ffmpeg lives in smoke_test.py, excluded from
collection in pyproject.toml.
"""

import json

import pytest

from ffmpeg_mcp.core import runner
from ffmpeg_mcp.tools import audio, video


class TestResolve:
    def test_wrong_env_override_does_not_fall_through(self, tmp_path, monkeypatch):
        monkeypatch.setenv(runner.ENV_VAR, str(tmp_path / "missing.exe"))
        monkeypatch.setattr(runner, "_cached", {})
        assert runner.resolve_ffmpeg(refresh=True) is None

    def test_env_override_accepts_the_binary(self, tmp_path, monkeypatch):
        fake = tmp_path / "ffmpeg.exe"
        fake.write_bytes(b"MZ")
        monkeypatch.setenv(runner.ENV_VAR, str(fake))
        monkeypatch.setattr(runner, "_cached", {})
        assert runner.resolve_ffmpeg(refresh=True) == str(fake)

    def test_env_override_accepts_the_directory(self, tmp_path, monkeypatch):
        (tmp_path / "ffmpeg.exe").write_bytes(b"MZ")
        monkeypatch.setenv(runner.ENV_VAR, str(tmp_path))
        monkeypatch.setattr(runner, "_cached", {})
        import os
        expected = str(tmp_path / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
        if os.name == "nt":
            assert runner.resolve_ffmpeg(refresh=True) == expected

    def test_missing_binary_raises_with_guidance(self, monkeypatch):
        monkeypatch.setattr(runner, "resolve_ffmpeg", lambda refresh=False: None)
        with pytest.raises(runner.FfmpegError, match="FFMPEG_PATH"):
            runner.run_ffmpeg(["-version"])


class TestVerifyOutput:
    def test_missing_stream_kind_is_an_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(runner, "media_summary", lambda p: {
            "path": str(p), "bytes": 5000, "format": "wav", "seconds": 1.0,
            "streams": [{"type": "video", "codec": "png"}],
        })
        with pytest.raises(runner.FfmpegError, match="no audio stream"):
            runner.verify_output(tmp_path / "x.wav", expect_stream="audio")

    def test_zero_duration_audio_is_an_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(runner, "media_summary", lambda p: {
            "path": str(p), "bytes": 5000, "format": "ogg", "seconds": 0.0,
            "streams": [{"type": "audio", "codec": "vorbis"}],
        })
        with pytest.raises(runner.FfmpegError, match="zero duration"):
            runner.verify_output(tmp_path / "x.ogg", expect_stream="audio")

    def test_tiny_file_is_an_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr(runner, "media_summary", lambda p: {
            "path": str(p), "bytes": 10, "format": "gif", "seconds": 0,
            "streams": [{"type": "video"}],
        })
        with pytest.raises(runner.FfmpegError, match="bytes"):
            runner.verify_output(tmp_path / "x.gif", expect_stream="video")


class TestToolValidation:
    """Argument validation must reject before ffmpeg is ever invoked."""

    def test_convert_rejects_bad_channels(self, tmp_path):
        source = tmp_path / "in.wav"
        source.write_bytes(b"\0" * 100)
        result = audio.convert_audio(str(source), str(tmp_path / "out.ogg"), channels=3)
        assert result.startswith("ERROR") and "channels" in result

    def test_convert_rejects_bad_quality(self, tmp_path):
        source = tmp_path / "in.wav"
        source.write_bytes(b"\0" * 100)
        result = audio.convert_audio(str(source), str(tmp_path / "out.ogg"), quality=11)
        assert result.startswith("ERROR") and "quality" in result

    def test_convert_missing_input(self, tmp_path):
        result = audio.convert_audio(str(tmp_path / "nope.wav"), str(tmp_path / "out.ogg"))
        assert result.startswith("ERROR") and "not found" in result

    def test_trim_fade_out_requires_duration(self, tmp_path):
        source = tmp_path / "in.wav"
        source.write_bytes(b"\0" * 100)
        result = audio.trim_audio(str(source), str(tmp_path / "out.wav"), fade_out=0.5)
        assert result.startswith("ERROR") and "duration" in result

    def test_batch_rejects_missing_dir(self, tmp_path):
        result = audio.batch_convert_audio(str(tmp_path / "nope"), str(tmp_path / "out"))
        assert result.startswith("ERROR")

    def test_batch_rejects_empty_match(self, tmp_path):
        result = audio.batch_convert_audio(str(tmp_path), str(tmp_path / "out"))
        assert result.startswith("ERROR") and "matches" in result

    def test_gif_requires_gif_extension(self, tmp_path):
        result = video.make_gif(str(tmp_path / "in.mp4"), str(tmp_path / "out.png"))
        assert result.startswith("ERROR") and ".gif" in result

    def test_video_rejects_unknown_container(self, tmp_path):
        result = video.make_video("f_%03d.png", str(tmp_path / "out.avi"))
        assert result.startswith("ERROR")

    def test_extract_requires_pattern_slot(self, tmp_path):
        source = tmp_path / "in.mp4"
        source.write_bytes(b"\0" * 100)
        result = video.extract_frames(str(source), str(tmp_path / "frame.png"))
        assert result.startswith("ERROR") and "%d" in result


class TestToolRegistration:
    def test_every_tool_registers_without_duplicates(self):
        import anyio

        from ffmpeg_mcp import mcp
        import ffmpeg_mcp.tools  # noqa: F401

        names = [t.name for t in anyio.run(mcp.list_tools)]
        assert len(names) == len(set(names)), "duplicate tool names"
        expected = {"get_ffmpeg_info", "get_media_info", "convert_audio",
                    "trim_audio", "batch_convert_audio", "make_waveform_image",
                    "make_gif", "make_video", "extract_frames"}
        assert expected <= set(names)


class TestMediaSummaryShape:
    def test_summary_extracts_the_useful_facts(self, monkeypatch, tmp_path):
        monkeypatch.setattr(runner, "probe", lambda p: {
            "format": {"size": "12345", "format_name": "ogg", "duration": "2.5"},
            "streams": [{"codec_type": "audio", "codec_name": "vorbis",
                         "sample_rate": "44100", "channels": 2}],
        })
        summary = runner.media_summary(tmp_path / "x.ogg")
        assert summary["seconds"] == 2.5
        assert summary["streams"][0] == {
            "type": "audio", "codec": "vorbis", "sample_rate": 44100, "channels": 2}
