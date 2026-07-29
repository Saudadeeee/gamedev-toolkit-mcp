"""Unit tests for the pure-Python core.

These need no Aseprite install, so they run in CI. Everything that touches the
editor lives in smoke_test.py instead.

The focus is the logic that silently produces wrong output rather than an
error: colour parsing, Lua escaping, traversal rejection, perceptual matching
and wildcard path expansion.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aseprite_mcp.core.color_space import (  # noqa: E402
    build_ramp,
    lab_distance,
    nearest_palette_index,
    relative_luminance,
    rgb_to_hsl,
    rgb_to_lab,
    sort_palette,
)
from aseprite_mcp.core.colors import parse_hex_color  # noqa: E402
from aseprite_mcp.core.commands import lua_escape, reject_traversal  # noqa: E402
from aseprite_mcp.core.dither import (  # noqa: E402
    PATTERNS,
    PATTERN_NAMES,
    get_pattern,
    pattern_lua,
    to_lua_table,
)
from aseprite_mcp.core.path_resolver import _first_existing, _glob  # noqa: E402


# --------------------------------------------------------------------- #
# Colour parsing
# --------------------------------------------------------------------- #

class TestParseHexColor:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("#FF0000", (255, 0, 0, 255)),
            ("FF0000", (255, 0, 0, 255)),
            ("#f00", (255, 0, 0, 255)),
            ("#F00F", (255, 0, 0, 255)),
            ("#FF000080", (255, 0, 0, 128)),
            ("#00000000", (0, 0, 0, 0)),
            ("  #ffffff  ", (255, 255, 255, 255)),
        ],
    )
    def test_valid(self, value, expected):
        assert parse_hex_color(value) == expected

    @pytest.mark.parametrize(
        "value", ["", None, "#", "#12", "#12345", "#1234567", "#GGGGGG", "red", "#123456789"]
    )
    def test_rejected(self, value):
        assert parse_hex_color(value) is None

    def test_shorthand_expands_by_doubling(self):
        # #abc means #aabbcc, not #0a0b0c.
        assert parse_hex_color("#abc") == (0xAA, 0xBB, 0xCC, 255)


# --------------------------------------------------------------------- #
# Lua escaping and traversal
# --------------------------------------------------------------------- #

class TestLuaEscape:
    def test_quote_cannot_close_the_literal(self):
        escaped = lua_escape('x" print("pwned") --')
        assert '\\"' in escaped
        # No bare quote survives to end the string literal.
        assert not any(
            escaped[i] == '"' and (i == 0 or escaped[i - 1] != '\\')
            for i in range(len(escaped))
        )

    def test_backslash_doubled_first(self):
        # A single backslash before a quote must not escape the escape.
        assert lua_escape('a\\"b') == 'a\\\\\\"b'

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("\n", "\\n"),
            ("\r", "\\r"),
            ("\0", "\\0"),
            ("plain", "plain"),
            ("", ""),
        ],
    )
    def test_control_characters(self, raw, expected):
        assert lua_escape(raw) == expected

    def test_unicode_passes_through(self):
        assert lua_escape("layer é ü 日本") == "layer é ü 日本"


class TestRejectTraversal:
    @pytest.mark.parametrize(
        "path",
        [
            "../etc/passwd",
            "a/../../b",
            "..",
            "..\\windows\\system32",
            "assets/../../secret",
        ],
    )
    def test_rejects_escaping_paths(self, path):
        assert reject_traversal(path) is not None

    @pytest.mark.parametrize(
        "path",
        [
            "sprite.aseprite",
            "assets/sprite.aseprite",
            # A filename that merely contains dots is not traversal; the old
            # substring check flagged these.
            "foo..bar.aseprite",
            "v1.2..3/sprite.png",
            "C:/absolute/path.png",
            "/usr/share/x.png",
            # Normalises to "." -- it descends and comes back, so it never
            # leaves the starting directory and is not an escape.
            "foo/..",
            "a/b/../..",
        ],
    )
    def test_allows_paths_that_do_not_escape(self, path):
        assert reject_traversal(path) is None

    def test_normalisation_is_what_decides(self):
        # The check runs on normalised components, so a path only fails when
        # ".." survives normalisation -- i.e. when it actually climbs out.
        assert reject_traversal("a/b/../c") is None
        assert reject_traversal("a/../../c") is not None


# --------------------------------------------------------------------- #
# Perceptual colour
# --------------------------------------------------------------------- #

class TestColorSpace:
    def test_lab_reference_values(self):
        # Known CIELAB values for sRGB primaries, D65.
        assert rgb_to_lab((0, 0, 0))[0] == pytest.approx(0, abs=0.1)
        assert rgb_to_lab((255, 255, 255))[0] == pytest.approx(100, abs=0.1)

        red = rgb_to_lab((255, 0, 0))
        assert red[0] == pytest.approx(53.24, abs=0.1)
        assert red[1] == pytest.approx(80.09, abs=0.2)
        assert red[2] == pytest.approx(67.20, abs=0.2)

    def test_identical_colors_have_zero_distance(self):
        assert lab_distance(rgb_to_lab((12, 34, 56)), rgb_to_lab((12, 34, 56))) == 0

    def test_nearest_is_perceptual_not_rgb(self):
        # Pure green sits far from mid-grey in RGB terms, yet a bright olive
        # is the perceptually closer match for a yellow-green. Plain RGB
        # distance is what gets this wrong.
        palette = [(0, 0, 0), (128, 128, 128), (255, 255, 255), (154, 205, 50)]
        assert nearest_palette_index((150, 200, 60), palette) == 3

    def test_nearest_exact_match(self):
        palette = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        assert nearest_palette_index((0, 255, 0), palette) == 1

    def test_nearest_rejects_empty_palette(self):
        with pytest.raises(ValueError):
            nearest_palette_index((0, 0, 0), [])

    def test_luminance_weights_green_above_red(self):
        # Rec. 709: a flat channel average would rank these equal.
        assert relative_luminance((0, 255, 0)) > relative_luminance((255, 0, 0))
        assert relative_luminance((255, 0, 0)) > relative_luminance((0, 0, 255))

    def test_luminance_bounds(self):
        assert relative_luminance((0, 0, 0)) == pytest.approx(0.0)
        assert relative_luminance((255, 255, 255)) == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "rgb,hue",
        [((255, 0, 0), 0), ((0, 255, 0), 120), ((0, 0, 255), 240), ((255, 255, 0), 60)],
    )
    def test_hsl_hue(self, rgb, hue):
        assert rgb_to_hsl(rgb)[0] == pytest.approx(hue, abs=0.5)

    def test_hsl_grey_has_no_saturation(self):
        h, s, l = rgb_to_hsl((128, 128, 128))
        assert s == 0
        assert l == pytest.approx(0.502, abs=0.01)


class TestSortPalette:
    PALETTE = [(255, 255, 255), (0, 0, 0), (255, 0, 0), (0, 0, 255), (128, 128, 128)]

    def test_luminance_is_dark_to_light(self):
        result = sort_palette(self.PALETTE, "luminance")
        assert result[0] == (0, 0, 0)
        assert result[-1] == (255, 255, 255)
        lums = [relative_luminance(c) for c in result]
        assert lums == sorted(lums)

    def test_hue_parks_greys_first(self):
        result = sort_palette(self.PALETTE, "hue")
        greys = {(0, 0, 0), (128, 128, 128), (255, 255, 255)}
        # Every grey precedes every chromatic colour.
        first_chromatic = next(i for i, c in enumerate(result) if c not in greys)
        assert all(c in greys for c in result[:first_chromatic])

    def test_preserves_all_entries(self):
        for key in ("luminance", "hue", "saturation", "lightness"):
            assert sorted(sort_palette(self.PALETTE, key)) == sorted(self.PALETTE)

    def test_rejects_unknown_key(self):
        with pytest.raises(ValueError):
            sort_palette(self.PALETTE, "vibes")

    def test_build_ramp_is_luminance_order(self):
        assert build_ramp(self.PALETTE) == sort_palette(self.PALETTE, "luminance")

    def test_empty_palette(self):
        assert sort_palette([], "luminance") == []


# --------------------------------------------------------------------- #
# Dither matrices
# --------------------------------------------------------------------- #

class TestDither:
    def test_all_patterns_are_rectangular(self):
        for name, matrix in PATTERNS.items():
            widths = {len(row) for row in matrix}
            assert len(widths) == 1, f"{name} has ragged rows"
            assert len(matrix) > 0

    def test_all_patterns_start_at_zero(self):
        # The threshold maths assumes the minimum is 0; a matrix that starts
        # at 1 would never emit the first colour at low density.
        for name, matrix in PATTERNS.items():
            assert min(min(row) for row in matrix) == 0, f"{name} does not start at 0"

    def test_bayer_matrices_are_complete_permutations(self):
        for name, size in (("bayer2x2", 2), ("bayer4x4", 4), ("bayer8x8", 8)):
            flat = sorted(v for row in PATTERNS[name] for v in row)
            assert flat == list(range(size * size)), f"{name} is not a full permutation"

    def test_named_lookup_matches_registry(self):
        for name in PATTERN_NAMES:
            assert get_pattern(name) is PATTERNS[name]

    def test_unknown_pattern_lists_alternatives(self):
        with pytest.raises(ValueError) as excinfo:
            get_pattern("swirl")
        assert "bayer4x4" in str(excinfo.value)

    def test_lua_table_round_trips(self):
        assert to_lua_table([[0, 1], [2, 3]]) == "{{0, 1}, {2, 3}}"

    def test_pattern_lua_reports_dimensions_and_divisor(self):
        table, width, height, divisor = pattern_lua("bayer4x4")
        assert (width, height, divisor) == (4, 4, 16)
        assert table.startswith("{{0, 8, 2, 10}")

    def test_divisor_is_one_past_maximum(self):
        for name in PATTERN_NAMES:
            _, _, _, divisor = pattern_lua(name)
            assert divisor == max(max(r) for r in PATTERNS[name]) + 1


# --------------------------------------------------------------------- #
# Path globbing
# --------------------------------------------------------------------- #

class TestGlob:
    @pytest.fixture
    def tree(self, tmp_path):
        (tmp_path / "Aseprite-1.3" / "aseprite" / "build" / "bin").mkdir(parents=True)
        (tmp_path / "Aseprite-1.3" / "aseprite" / "build" / "bin" / "aseprite.exe").write_text("x")
        (tmp_path / "Godot").mkdir()
        (tmp_path / "Godot" / "Godot_v4.3.exe").write_text("x")
        (tmp_path / "Godot" / "Godot_v3.5.exe").write_text("x")
        return tmp_path

    def test_wildcard_in_filename(self, tree):
        matches = _glob(str(tree / "Godot" / "Godot_v4*.exe"))
        assert [p.name for p in matches] == ["Godot_v4.3.exe"]

    def test_wildcard_in_directory_component(self, tree):
        # The case the old implementation could not express: it globbed only
        # the basename, so a wildcard directory made the whole pattern dead.
        matches = _glob(str(tree / "Aseprite*" / "*" / "build" / "bin" / "aseprite.exe"))
        assert len(matches) == 1
        assert matches[0].name == "aseprite.exe"

    def test_no_wildcard_checks_existence(self, tree):
        assert _glob(str(tree / "Godot" / "Godot_v4.3.exe"))
        assert _glob(str(tree / "Godot" / "nope.exe")) == []

    def test_missing_root_is_empty_not_an_error(self):
        assert _glob("/definitely/not/here/*/x.exe") == []

    def test_first_existing_prefers_earlier_candidates(self, tree):
        found = _first_existing([
            str(tree / "missing.exe"),
            str(tree / "Godot" / "Godot_v3.5.exe"),
            str(tree / "Godot" / "Godot_v4.3.exe"),
        ])
        assert found.endswith("Godot_v3.5.exe")

    def test_first_existing_returns_none_when_nothing_matches(self, tree):
        assert _first_existing([str(tree / "a.exe"), str(tree / "b*.exe")]) is None


class TestSteamDiscovery:
    """Steam installs are the case hard-coded paths get wrong.

    Steam can live on any drive and add libraries anywhere, and it names the
    Godot editor `godot.windows.opt.tools.64.exe` rather than the `Godot_v4*`
    of the official downloads. Guessing at either loses a real install.
    """

    @pytest.fixture
    def steam(self, tmp_path):
        client = tmp_path / "Games" / "Steam"
        (client / "steamapps" / "common" / "Godot Engine").mkdir(parents=True)
        (client / "steamapps" / "common" / "Godot Engine" /
         "godot.windows.opt.tools.64.exe").write_text("x")

        second = tmp_path / "Elsewhere" / "SteamLibrary"
        (second / "steamapps" / "common" / "Aseprite").mkdir(parents=True)
        (second / "steamapps" / "common" / "Aseprite" / "Aseprite.exe").write_text("x")

        (client / "steamapps" / "libraryfolders.vdf").write_text(
            '"libraryfolders"\n{\n'
            f'\t"0"\n\t{{\n\t\t"path"\t\t"{str(client).replace(chr(92), chr(92) * 2)}"\n\t}}\n'
            f'\t"1"\n\t{{\n\t\t"path"\t\t"{str(second).replace(chr(92), chr(92) * 2)}"\n\t}}\n'
            "}\n",
            encoding="utf-8",
        )
        return client, second

    def test_reads_extra_libraries_from_vdf(self, steam, monkeypatch):
        from aseprite_mcp.core import path_resolver

        client, second = steam
        monkeypatch.setattr(path_resolver, "_steam_registry_roots", lambda: [str(client)])

        libraries = path_resolver._steam_libraries()
        resolved = {os.path.normcase(os.path.abspath(p)) for p in libraries}
        assert os.path.normcase(os.path.abspath(str(client))) in resolved
        # The second library is only discoverable through the vdf.
        assert os.path.normcase(os.path.abspath(str(second))) in resolved

    def test_deduplicates_case_variant_roots(self, steam, monkeypatch):
        from aseprite_mcp.core import path_resolver

        client, _ = steam
        monkeypatch.setattr(
            path_resolver,
            "_steam_registry_roots",
            lambda: [str(client), str(client).upper(), str(client).lower()],
        )
        libraries = path_resolver._steam_libraries()
        keys = [os.path.normcase(os.path.abspath(p)) for p in libraries]
        assert len(keys) == len(set(keys))

    def test_app_candidates_cover_every_library(self, steam, monkeypatch):
        from aseprite_mcp.core import path_resolver

        client, _ = steam
        monkeypatch.setattr(path_resolver, "_steam_registry_roots", lambda: [str(client)])

        candidates = path_resolver._steam_app_candidates(r"Godot Engine\godot.windows.opt.tools.64.exe")
        assert any(os.path.exists(c) for c in candidates), candidates

    def test_finds_the_steam_named_godot_binary(self, steam, monkeypatch):
        from aseprite_mcp.core import path_resolver

        client, _ = steam
        monkeypatch.setattr(path_resolver, "_steam_registry_roots", lambda: [str(client)])

        found = _first_existing(
            path_resolver._steam_app_candidates(
                r"Godot Engine\godot.windows.opt.tools.64.exe"
            )
        )
        assert found is not None
        assert found.endswith("godot.windows.opt.tools.64.exe")
