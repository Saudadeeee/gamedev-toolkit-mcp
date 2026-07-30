"""Drive a real rfxgen end to end. Needs the binary; excluded from unit runs.

    uv run tests/smoke_test.py [--clean]

Exercises every tool against the real CLI and checks the audio that comes out,
not just that commands returned. Exit 0 only when everything passed.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rfxgen_mcp.core import runner  # noqa: E402
from rfxgen_mcp.tools import convert, generate  # noqa: E402

OUT = Path(__file__).parent / "smoke_output"
CHECKS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, ok, detail))
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + (f"  -- {detail[:70]}" if detail else ""))


def parsed(result: str) -> dict | None:
    try:
        return json.loads(result)
    except ValueError:
        return None


def main() -> int:
    binary = runner.resolve_rfxgen(refresh=True)
    if binary is None:
        print("rfxgen not found -- set RFXGEN_PATH. Nothing to smoke-test.")
        return 1
    print(f"rfxgen: {binary}\n")
    OUT.mkdir(exist_ok=True)

    info = parsed(generate.get_rfxgen_info())
    check("get_rfxgen_info", bool(info and info.get("found")), str(info and info.get("version")))

    r = parsed(generate.generate_preset("coin", str(OUT / "coin.wav")))
    check("generate_preset renders", bool(r and r.get("seconds", 0) > 0.01), str(r and r.get("seconds")))

    bad = generate.generate_preset("kaboom", str(OUT / "bad.wav"))
    check("bad preset is a loud error", bad.startswith("ERROR:"), bad[:60])

    r = parsed(generate.design_sound(str(OUT / "laser.wav"), wave_type="square",
                                     params={"start_frequency": 0.85, "slide": -0.35,
                                             "sustain_time": 0.15, "decay_time": 0.2},
                                     save_rfx=str(OUT / "laser.rfx")))
    check("design_sound renders", bool(r and r.get("seconds", 0) > 0.05), str(r and r.get("seconds")))
    check("design_sound saved .rfx", (OUT / "laser.rfx").is_file())

    r = parsed(generate.generate_variations(str(OUT / "vars"), count=3, seed=7,
                                            base_rfx=str(OUT / "laser.rfx")))
    check("variations render", bool(r and len(r.get("variations", [])) == 3))
    lengths = {v["bytes"] for v in (r or {}).get("variations", [])}
    check("variations actually differ", len(lengths) > 1, f"distinct sizes: {len(lengths)}")

    r = parsed(convert.convert_audio(str(OUT / "coin.wav"), str(OUT / "coin_22k.wav"),
                                     sample_rate=22050, bits=8, channels=1))
    check("convert_audio resamples", bool(r and r.get("sample_rate") == 22050), str(r and r.get("bits")))

    r = convert.export_wave_header(str(OUT / "laser.rfx"), str(OUT / "laser.h"))
    header_ok = not r.startswith("ERROR") and (OUT / "laser.h").stat().st_size > 200
    check("export_wave_header", header_ok)

    r = parsed(convert.get_sound_info(str(OUT / "laser.rfx")))
    check("get_sound_info reads .rfx back",
          bool(r and abs(r["parameters"]["start_frequency"] - 0.85) < 1e-4))

    failed = sum(1 for _, ok, _ in CHECKS if not ok)
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} passed")

    if "--clean" in sys.argv and failed == 0:
        shutil.rmtree(OUT, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
