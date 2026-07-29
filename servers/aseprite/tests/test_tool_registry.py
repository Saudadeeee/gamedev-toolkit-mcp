"""Tests for the toolkit's application registry and resolver.

The registry is what makes adding a fifth application a data change instead of
a fourth hand-written finder. These check the table stays coherent and that
lookup honours env overrides, version gates and aliases.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aseprite_mcp.core import path_resolver  # noqa: E402
from aseprite_mcp.core.path_resolver import (  # noqa: E402
    PathResolver,
    get_application_info,
    get_tool_path,
)
from aseprite_mcp.core.tool_registry import SPECS, TOOL_KEYS, get_spec  # noqa: E402


class TestRegistryShape:
    def test_every_supported_tool_is_registered(self):
        assert set(TOOL_KEYS) == {
            "aseprite",
            "godot",
            "blockbench",
            "obsidian",
            "audacity",
        }

    def test_keys_match_their_spec(self):
        for key, spec in SPECS.items():
            assert spec.key == key

    def test_every_spec_has_the_basics(self):
        for spec in SPECS.values():
            assert spec.display_name
            assert spec.mcp_transport, f"{spec.key} does not say how it is reached"
            # Every tool must be findable on at least one platform.
            assert spec.windows or spec.darwin or spec.linux

    def test_sweep_specs_declare_what_to_look_for(self):
        # A sweep root with no filename to match would walk the disk for nothing.
        for spec in SPECS.values():
            if spec.sweep_windows:
                assert spec.sweep_names, f"{spec.key} sweeps without target names"

    def test_registry_lookups_expose_a_version_requirement_when_gated(self):
        for spec in SPECS.values():
            if spec.version_gate is not None:
                assert spec.version_requirement, (
                    f"{spec.key} gates on version but never says why"
                )


class TestSpecLookup:
    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("aseprite", "aseprite"),
            ("Aseprite.exe", "aseprite"),
            ("GODOT", "godot"),
            ("godot4", "godot"),
            ("Godot_Engine", "godot"),
            ("blockbench", "blockbench"),
            ("bb", "blockbench"),
            ("  Audacity  ", "audacity"),
        ],
    )
    def test_aliases_resolve(self, alias, expected):
        spec = get_spec(alias)
        assert spec is not None
        assert spec.key == expected

    def test_unknown_tool_is_none(self):
        assert get_spec("photoshop") is None
        assert get_tool_path("photoshop") is None


class TestVersionGate:
    def test_godot_gate_rejects_3_and_accepts_4(self):
        gate = SPECS["godot"].version_gate
        assert gate is not None
        assert gate("4.7.1.stable.steam.a13da4feb")
        assert gate("4.2.2.stable.official")
        assert not gate("3.5.3.stable.official")

    def test_ungated_tools_accept_anything(self):
        for key in ("aseprite", "blockbench", "audacity"):
            assert SPECS[key].version_gate is None

    def test_unreadable_version_does_not_reject(self, tmp_path, monkeypatch):
        # A locked-down machine where --version cannot run must not lose a
        # perfectly good install.
        exe = tmp_path / "godot.exe"
        exe.write_text("x")

        resolver = PathResolver()
        monkeypatch.setattr(PathResolver, "get_version", lambda self, path, spec=None: None)
        assert resolver._version_ok(SPECS["godot"], str(exe))

    def test_wrong_major_is_skipped_for_the_next_candidate(self, tmp_path, monkeypatch):
        old = tmp_path / "old" / "godot.exe"
        new = tmp_path / "new" / "godot.exe"
        old.parent.mkdir()
        new.parent.mkdir()
        old.write_text("x")
        new.write_text("x")

        versions = {str(old): "3.5.3.stable", str(new): "4.7.1.stable"}
        resolver = PathResolver()
        monkeypatch.setattr(
            PathResolver, "get_version", lambda self, path, spec=None: versions.get(path)
        )

        found = resolver._first_acceptable(SPECS["godot"], [str(old), str(new)])
        assert found == str(new)

    def test_all_candidates_rejected_returns_none(self, tmp_path, monkeypatch):
        only = tmp_path / "godot.exe"
        only.write_text("x")
        resolver = PathResolver()
        monkeypatch.setattr(PathResolver, "get_version", lambda self, path, spec=None: "3.5.3")
        assert resolver._first_acceptable(SPECS["godot"], [str(only)]) is None


class TestEnvOverrides:
    @pytest.mark.parametrize(
        "key,env_name",
        [
            ("aseprite", "ASEPRITE_PATH"),
            ("godot", "GODOT_PATH"),
            ("blockbench", "BLOCKBENCH_PATH"),
            ("audacity", "AUDACITY_PATH"),
        ],
    )
    def test_override_wins_when_it_resolves(self, key, env_name, tmp_path, monkeypatch):
        exe = tmp_path / f"{key}.exe"
        exe.write_text("x")
        monkeypatch.setenv(env_name, str(exe))
        assert get_tool_path(key) == str(exe)

    def test_stale_override_falls_through_to_detection(self, monkeypatch):
        monkeypatch.setenv("BLOCKBENCH_PATH", "/gone/Blockbench.exe")
        monkeypatch.setattr(
            path_resolver._resolver, "find", lambda k: "/found/Blockbench.exe"
        )
        assert get_tool_path("blockbench") == "/found/Blockbench.exe"

    def test_every_tool_has_an_override(self):
        assert set(path_resolver._ENV_OVERRIDES) == set(TOOL_KEYS)


class TestApplicationInfo:
    def test_reports_every_tool_even_when_missing(self, monkeypatch):
        monkeypatch.setattr(path_resolver, "get_tool_path", lambda key: None)
        info = get_application_info()

        assert set(info) == set(TOOL_KEYS)
        for key, entry in info.items():
            assert entry["found"] is False
            assert entry["path"] == "Not found"
            # A miss must still say how the tool would be reached and how to
            # point at it manually, or the report is not actionable.
            assert entry["mcp_transport"]
            assert entry["env_var"]

    def test_found_entries_carry_a_version(self, tmp_path, monkeypatch):
        exe = tmp_path / "thing.exe"
        exe.write_text("x")
        monkeypatch.setattr(path_resolver, "get_tool_path", lambda key: str(exe))
        monkeypatch.setattr(
            path_resolver._resolver, "get_version", lambda path, spec=None: "1.2.3"
        )

        info = get_application_info()
        for entry in info.values():
            assert entry["found"] is True
            assert entry["version"] == "1.2.3"


class TestCandidateBuilding:
    def test_platform_selects_the_right_candidate_list(self, monkeypatch):
        resolver = PathResolver()

        resolver.platform = "Windows"
        windows = resolver._candidates(SPECS["blockbench"])
        assert any("Blockbench.exe" in c for c in windows)

        resolver.platform = "Darwin"
        mac = resolver._candidates(SPECS["blockbench"])
        assert any(".app/Contents/MacOS" in c for c in mac)

        resolver.platform = "Linux"
        linux = resolver._candidates(SPECS["blockbench"])
        assert any(c.startswith("/usr") or c.startswith("/opt") for c in linux)

    def test_steam_candidates_are_appended_when_declared(self, monkeypatch):
        monkeypatch.setattr(
            path_resolver, "_steam_app_candidates", lambda *rel: [f"STEAM::{r}" for r in rel]
        )
        resolver = PathResolver()
        resolver.platform = "Windows"

        godot = resolver._candidates(SPECS["godot"])
        assert any(c.startswith("STEAM::") for c in godot)

        # Blockbench is not on Steam, so no Steam entries should appear.
        blockbench = resolver._candidates(SPECS["blockbench"])
        assert not any(c.startswith("STEAM::") for c in blockbench)


class TestVersionSource:
    """Where a version comes from, and what must not happen while getting it.

    Running `<exe> --version` on a GUI application is not harmless: Audacity
    answers "Obtaining pipe", Blockbench reports its bundled Node version, and
    both briefly launch the app. A read-only probe must not do that.
    """

    def test_gui_apps_do_not_declare_a_version_flag(self):
        for key in ("blockbench", "obsidian", "audacity"):
            assert SPECS[key].supports_version_flag is False, (
                f"{key} would be probed by launching it"
            )

    def test_cli_apps_still_declare_one(self):
        for key in ("aseprite", "godot"):
            assert SPECS[key].supports_version_flag is True

    def test_no_subprocess_for_a_gui_app(self, tmp_path, monkeypatch):
        exe = tmp_path / "Blockbench.exe"
        exe.write_text("x")

        def explode(*args, **kwargs):
            raise AssertionError("get_version must not spawn a process here")

        monkeypatch.setattr(path_resolver.subprocess, "run", explode)
        monkeypatch.setattr(path_resolver, "_windows_file_version", lambda p: None)

        resolver = PathResolver()
        assert resolver.get_version(str(exe), SPECS["blockbench"]) is None

    def test_file_metadata_wins_when_available(self, tmp_path, monkeypatch):
        exe = tmp_path / "anything.exe"
        exe.write_text("x")
        monkeypatch.setattr(path_resolver, "_windows_file_version", lambda p: "9.9.9")

        resolver = PathResolver()
        resolver.platform = "Windows"
        # True even for a tool that does support the flag: metadata is free.
        assert resolver.get_version(str(exe), SPECS["godot"]) == "9.9.9"

    def test_missing_file_is_none(self):
        assert PathResolver().get_version("/definitely/not/here.exe") is None
