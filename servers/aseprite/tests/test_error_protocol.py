"""Tests for the ERROR: protocol and executable resolution.

This is the safety-critical layer. Aseprite's batch runner always exits 0 and
discards a top-level Lua `return`, so a broken script is indistinguishable
from a working one unless this code catches it. A regression here does not
raise -- it silently reports success for work that never happened.

The subprocess is stubbed out, so these run without Aseprite installed.
"""

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aseprite_mcp.core.commands import AsepriteCommand  # noqa: E402


@pytest.fixture
def fake_run(monkeypatch):
    """Replace execute_lua_script so the checked wrapper can be tested alone."""

    def install(success, output):
        monkeypatch.setattr(
            AsepriteCommand,
            "execute_lua_script",
            staticmethod(lambda script, filename=None: (success, output)),
        )

    return install


class TestCheckedScript:
    def test_plain_output_is_success(self, fake_run):
        fake_run(True, "OK")
        assert AsepriteCommand.execute_lua_script_checked("x") == (True, "OK")

    def test_error_line_becomes_failure(self, fake_run):
        fake_run(True, "ERROR:Layer not found")
        ok, message = AsepriteCommand.execute_lua_script_checked("x")
        assert ok is False
        assert message == "Layer not found"

    def test_error_after_other_output_is_still_caught(self, fake_run):
        # Aseprite prints warnings before the script runs; the ERROR line is
        # rarely the first thing on stdout.
        fake_run(True, "Warning: something\nprogress=3\nERROR:Frame out of range")
        ok, message = AsepriteCommand.execute_lua_script_checked("x")
        assert ok is False
        assert message == "Frame out of range"

    def test_error_must_start_the_line(self, fake_run):
        # A tool that merely mentions the word in its output has not failed.
        fake_run(True, "wrote ERROR:handling.md")
        ok, _ = AsepriteCommand.execute_lua_script_checked("x")
        assert ok is True

    def test_process_failure_passes_through(self, fake_run):
        fake_run(False, "aseprite crashed")
        assert AsepriteCommand.execute_lua_script_checked("x") == (False, "aseprite crashed")

    def test_empty_output_is_success(self, fake_run):
        fake_run(True, "")
        ok, _ = AsepriteCommand.execute_lua_script_checked("x")
        assert ok is True


class TestRunCommand:
    def test_missing_executable_returns_error_not_exception(self, monkeypatch):
        # The regression this guards: an unresolvable binary used to raise
        # FileNotFoundError out of the tool call and take the server down.
        monkeypatch.setattr(
            AsepriteCommand, "get_aseprite_executable", staticmethod(lambda: "nope.exe")
        )

        def boom(*args, **kwargs):
            raise FileNotFoundError(2, "The system cannot find the file specified")

        monkeypatch.setattr(subprocess, "run", boom)

        ok, message = AsepriteCommand.run_command(["--version"])
        assert ok is False
        assert "Cannot run Aseprite" in message
        assert "ASEPRITE_PATH" in message

    def test_permission_error_is_also_handled(self, monkeypatch):
        monkeypatch.setattr(
            AsepriteCommand, "get_aseprite_executable", staticmethod(lambda: "x")
        )

        def boom(*args, **kwargs):
            raise PermissionError(13, "Permission denied")

        monkeypatch.setattr(subprocess, "run", boom)

        ok, message = AsepriteCommand.run_command(["--version"])
        assert ok is False
        assert "Cannot run Aseprite" in message

    def test_stderr_used_when_stdout_is_empty(self, monkeypatch):
        monkeypatch.setattr(
            AsepriteCommand, "get_aseprite_executable", staticmethod(lambda: "x")
        )

        class Result:
            stdout = "   "
            stderr = "Aseprite 1.3"

        monkeypatch.setattr(subprocess, "run", lambda *a, **k: Result())

        assert AsepriteCommand.run_command(["--version"]) == (True, "Aseprite 1.3")

    def test_called_process_error_prefers_stderr(self, monkeypatch):
        monkeypatch.setattr(
            AsepriteCommand, "get_aseprite_executable", staticmethod(lambda: "x")
        )

        def boom(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "x", output="out", stderr="the real reason")

        monkeypatch.setattr(subprocess, "run", boom)

        ok, message = AsepriteCommand.run_command(["--version"])
        assert ok is False
        assert message == "the real reason"


class TestExecutableResolution:
    def test_env_path_wins_when_it_exists(self, monkeypatch, tmp_path):
        exe = tmp_path / "aseprite.exe"
        exe.write_text("x")
        monkeypatch.setenv("ASEPRITE_PATH", str(exe))
        assert AsepriteCommand.get_aseprite_executable() == str(exe)

    def test_stale_env_path_falls_through_to_detection(self, monkeypatch):
        # A path left over from a previous install must not become a hard
        # failure; detection gets a turn.
        monkeypatch.setenv("ASEPRITE_PATH", "/gone/aseprite.exe")
        monkeypatch.setattr(
            "aseprite_mcp.core.commands.get_aseprite_path", lambda: "/found/aseprite"
        )
        assert AsepriteCommand.get_aseprite_executable() == "/found/aseprite"

    def test_falls_back_to_bare_name(self, monkeypatch):
        monkeypatch.delenv("ASEPRITE_PATH", raising=False)
        monkeypatch.setattr("aseprite_mcp.core.commands.get_aseprite_path", lambda: None)
        assert AsepriteCommand.get_aseprite_executable() == "aseprite"
