"""BRYES - the host frame and the window rule, model-free (SP-2, R9 and R10).

    python devices/test_host_frame.py

Geometry is injected, so this runs on any desk and on CI: `monitor_rect` and `find_window` are
replaced with fixed answers, and ImageGrab is replaced with a recorder. What is asserted is the
behaviour a wrong frame would break: the frame is the target's monitor, the coordinate origin is
that monitor's corner, and a host run cannot start without a target.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from devices import windows as win  # noqa: E402

MONITOR = (785, -1080, 2705, 0)          # a 1920x1080 display, not at the origin
WINDOW = (777, -1088, 2713, -40)         # the maximised window: 8 px of overshoot each side


class FakeGrab:
    """Records the bbox ImageGrab was asked for and returns a blank image of that size."""

    def __init__(self):
        self.calls = []

    def grab(self, bbox=None, all_screens=False):
        self.calls.append((bbox, all_screens))
        left, top, right, bottom = bbox
        return Image.new("RGB", (right - left, bottom - top), (20, 20, 20))


def with_injected(monitor=MONITOR, window=WINDOW):
    """Point the module at a fixed desk: one monitor, one matching window."""
    win.monitor_rect = lambda hwnd: monitor if hwnd else None
    win.find_window = lambda title: (4242, title, window) if title else None


def test_frame_is_the_monitor_and_the_origin_follows_it():
    with_injected()
    fake = FakeGrab()
    saved_grab = win.ImageGrab
    win.ImageGrab = fake
    try:
        device = win.WindowsDevice(window="Unreal Editor")
        assert device._frame_rect() == MONITOR, device._frame_rect()
        png = device.screenshot()
        assert fake.calls == [(MONITOR, True)], fake.calls
        width, height = Image.open(__import__("io").BytesIO(png)).size
        assert (width, height) == (1920, 1080), (width, height)
        assert (device.caps.width, device.caps.height) == (1920, 1080), "caps is the frame"
        assert device.screen_xy(10, 20) == (785 + 10, -1080 + 20), device.screen_xy(10, 20)
    finally:
        win.ImageGrab = saved_grab
    print("PASS: the frame is the target's monitor, caps matches it, and the origin is its corner")


def test_no_target_keeps_the_whole_desktop():
    with_injected()
    fake = FakeGrab()
    saved_grab = win.ImageGrab
    win.ImageGrab = fake
    try:
        device = win.WindowsDevice()
        rect = device._frame_rect()
        assert fake.calls == [], "nothing has been grabbed yet"
        device.screenshot()
        assert fake.calls == [(rect, True)], fake.calls
        origin = device._origin_xy()
        assert rect[:2] == origin, (rect, origin)
        assert device.screen_xy(1, 2) == (origin[0] + 1, origin[1] + 2)
    finally:
        win.ImageGrab = saved_grab
    print("PASS: with no target the frame is the whole virtual desktop, anchored at its origin")


def test_a_vanished_window_raises_instead_of_changing_shape():
    with_injected()
    win.find_window = lambda title: None            # named, but no longer on screen
    device = win.WindowsDevice(window="Unreal Editor")
    assert device._frame_rect_or_none() is None
    try:
        device.screenshot()
    except RuntimeError as e:
        assert "frame is unknown" in str(e), str(e)
    else:
        raise AssertionError("a vanished target must raise, not silently grab the desktop")
    print("PASS: a vanished target raises rather than silently changing the frame")


def test_host_run_without_a_target_is_refused():
    from agent import loop

    saved = os.environ.get("BRYES_ALLOW_HOST")
    os.environ["BRYES_ALLOW_HOST"] = "1"
    try:
        try:
            loop._make_device("windows")
        except RuntimeError as e:
            assert "target window" in str(e), str(e)
        else:
            raise AssertionError("a windows body was built with no window")
        device = loop._make_device("windows", window="Unreal Editor")
        assert device.caps.name == "windows-desktop", device.caps.name
        # A body you built yourself already carries its target (or does not). Accepting `window`
        # here would drop it, so it must refuse rather than ignore.
        try:
            loop.run("g", device=device, window="Unreal Editor", verbose=False)
        except ValueError as e:
            assert "cannot be applied" in str(e), str(e)
        else:
            raise AssertionError("a built Device plus window was accepted silently")
    finally:
        if saved is None:
            os.environ.pop("BRYES_ALLOW_HOST", None)
        else:
            os.environ["BRYES_ALLOW_HOST"] = saved
    print("PASS: a host run without a window is refused; with one it is built")


if __name__ == "__main__":
    test_frame_is_the_monitor_and_the_origin_follows_it()
    test_no_target_keeps_the_whole_desktop()
    test_a_vanished_window_raises_instead_of_changing_shape()
    test_host_run_without_a_target_is_refused()
    print("PASS: all host frame rules green")
