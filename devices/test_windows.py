"""BRYES — deterministic WindowsDevice smoke (model-free), mirroring test_phone.

Checks the capture-only body: the Protocol shape, the safety property (no pointer verbs, so
the loop can never drive it), the window matcher (largest substring match, small windows
ignored), a real grab that produces a PNG, and the PowerShell channel.
Run:  python devices/test_windows.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402
from devices import Device, WindowsDevice  # noqa: E402
from devices.windows import find_window_rect  # noqa: E402


def test_window_matcher():
    """Pure function: no OS windows needed, so this half always runs."""
    windows = [
        ("Unreal Editor - LSGI", (100, 100, 1000, 700)),      # 900x600, the real one
        ("Unreal Editor tooltip", (0, 0, 150, 40)),           # too small, ignored
        ("unreal something", (2000, 200, 2100, 260)),         # small, ignored
        ("Calculator", (0, 0, 400, 600)),                     # wrong title
    ]
    assert find_window_rect("unreal", windows) == (100, 100, 1000, 700), "largest match"
    assert find_window_rect("UNREAL", windows) == (100, 100, 1000, 700), "case-insensitive"
    assert find_window_rect("nothing here", windows) is None, "no match -> None"
    assert find_window_rect("", windows) is None, "empty needle -> None"
    assert find_window_rect("calc", windows) == (0, 0, 400, 600), "other titles work"
    print("PASS: window matcher picks the largest substring match, ignores small windows")


def main():
    d = WindowsDevice()
    assert isinstance(d, Device), "WindowsDevice does not satisfy the Device Protocol"
    print(f"PASS: {d.caps.name} {d.caps.width}x{d.caps.height} "
          f"(shell={d.caps.shell_flavor})")

    # The safety property: capture-only. An empty verb set means the Brain is never offered
    # a click this body cannot perform.
    assert d.caps.verbs == frozenset(), f"capture-only body advertises verbs: {d.caps.verbs}"
    for call in (lambda: d.act({"type": "click", "x": 1, "y": 1}),
                 lambda: d.clear_field(),
                 lambda: d.type_into("x")):
        try:
            call()
        except NotImplementedError:
            pass
        else:
            raise AssertionError("capture-only body executed an action")
    print("PASS: no pointer verbs; act/clear_field/type_into refuse with NotImplementedError")

    test_window_matcher()

    png = d.screenshot()
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "screenshot is not a PNG"
    w, h = Image.open(io.BytesIO(png)).size
    assert (w, h) == (d.caps.width, d.caps.height), \
        f"png {w}x{h} != caps {d.caps.width}x{d.caps.height} (virtual-screen space)"
    print(f"PASS: full-desktop grab -> PNG {w}x{h} ({len(png)} bytes), matches caps")

    r = d.shell("Write-Output bryes-windows-ok")
    assert r["ok"] and "bryes-windows-ok" in r["stdout"], r
    print("PASS: PowerShell round-trips (Write-Output -> stdout, exit 0)")

    point = d.pointer()
    assert point is None or (isinstance(point, tuple) and len(point) == 2), point
    print(f"PASS: pointer -> {point}")

    print("\nPASS: all WindowsDevice smoke checks green")


if __name__ == "__main__":
    main()
