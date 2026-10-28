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

    # The body now advertises the full verb set, and every acting verb is gated rather than
    # absent: with BRYES_ALLOW_HOST unset, acting must REFUSE (RuntimeError), not pretend.
    from devices.base import ALL_VERBS
    assert d.caps.verbs == ALL_VERBS, f"windows body verbs: {d.caps.verbs}"
    saved = os.environ.pop("BRYES_ALLOW_HOST", None)
    try:
        for call in (lambda: d.act({"type": "click", "x": 1, "y": 1}),
                     lambda: d.clear_field(),
                     lambda: d.type_into("x")):
            try:
                call()
            except RuntimeError as exc:
                assert "BRYES_ALLOW_HOST" in str(exc), str(exc)
            else:
                raise AssertionError("acting succeeded without BRYES_ALLOW_HOST")
    finally:
        if saved is not None:
            os.environ["BRYES_ALLOW_HOST"] = saved
    print("PASS: full verb set advertised; acting refuses without BRYES_ALLOW_HOST")

    test_window_matcher()

    png = d.screenshot()
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "screenshot is not a PNG"
    w, h = Image.open(io.BytesIO(png)).size
    assert (w, h) == (d.caps.width, d.caps.height), \
        f"png {w}x{h} != caps {d.caps.width}x{d.caps.height} (virtual-screen space)"
    print(f"PASS: full-desktop grab -> PNG {w}x{h} ({len(png)} bytes), matches caps")

    # R10 moved the frame to the target's MONITOR, so image space stays screen space by the
    # frame's own origin (covered model-free in devices/test_host_frame.py). What must hold here
    # is the loud half: a named window that is gone raises, rather than quietly grabbing the
    # desktop and leaving every coordinate valid in the wrong space.
    try:
        WindowsDevice(window="NoSuchWindowAnywhere").screenshot()
    except RuntimeError as exc:
        assert "frame is unknown" in str(exc), str(exc)
    else:
        raise AssertionError("a vanished window grabbed a frame instead of raising")
    print("PASS: a named-but-missing window raises instead of grabbing the wrong frame")

    # The shell channel now sits behind its own gate; this smoke proves the transport, so it
    # opens both gates for the length of the call and restores whatever was there.
    shell_saved = {k: os.environ.get(k) for k in ("BRYES_ALLOW_HOST", "BRYES_ALLOW_HOST_SHELL")}
    os.environ["BRYES_ALLOW_HOST"] = "1"
    os.environ["BRYES_ALLOW_HOST_SHELL"] = "1"
    try:
        r = d.shell("Write-Output bryes-windows-ok")
    finally:
        for key, value in shell_saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    assert r["ok"] and "bryes-windows-ok" in r["stdout"], r
    print("PASS: PowerShell round-trips with both gates set (Write-Output -> stdout, exit 0)")

    point = d.pointer()
    assert point is None or (isinstance(point, tuple) and len(point) == 2), point
    print(f"PASS: pointer -> {point}")

    print("\nPASS: all WindowsDevice smoke checks green")


if __name__ == "__main__":
    main()
