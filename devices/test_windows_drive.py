"""BRYES — WindowsDevice driving tests (model-free: no real mouse, simulated origin).

The body under test is real. The input is a recorder, and the virtual origin is simulated, so
the translation can be proved on a desk whose origin happens to be (0,0) today.

Run:  python devices/test_windows_drive.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402
from devices import Device, WindowsDevice  # noqa: E402

FLAGS = ("BRYES_ALLOW_HOST", "BRYES_ALLOW_HOST_SHELL")


class FakeInput:
    """Records what the body asked for, in screen coordinates."""

    def __init__(self):
        self.calls = []

    def hover(self, x, y):
        self.calls.append(("hover", x, y))

    def click(self, x, y, button="left"):
        self.calls.append(("click", x, y, button))

    def double_click(self, x, y):
        self.calls.append(("double_click", x, y))

    def right_click(self, x, y):
        self.calls.append(("right_click", x, y))

    def scroll(self, x, y, clicks):
        self.calls.append(("scroll", x, y, clicks))

    def drag(self, x1, y1, x2, y2):
        self.calls.append(("drag", x1, y1, x2, y2))

    def press(self, chord):
        self.calls.append(("press", chord))

    def hold(self, chord, seconds):
        self.calls.append(("hold", chord, seconds))

    def type_text(self, text):
        self.calls.append(("type_text", text))

    def pointer(self):
        return (0, 0)


def set_flags(host=False, shell=False):
    """Set or clear both gates, without leaking the previous environment."""
    for name, on in (("BRYES_ALLOW_HOST", host), ("BRYES_ALLOW_HOST_SHELL", shell)):
        if on:
            os.environ[name] = "1"
        else:
            os.environ.pop(name, None)


def expect_raise(fn, name):
    try:
        fn()
    except RuntimeError:
        return
    raise AssertionError(f"{name} did not refuse without its gate")


def main():
    saved = {name: os.environ.get(name) for name in FLAGS}
    try:
        # ---- gates: nothing acts without the switch ------------------------------------
        set_flags()
        d = WindowsDevice(input=FakeInput())
        assert isinstance(d, Device), "WindowsDevice no longer satisfies the Device Protocol"
        expect_raise(lambda: d.act({"type": "click", "x": 1, "y": 2}), "act")
        expect_raise(lambda: d.clear_field(), "clear_field")
        expect_raise(lambda: d.type_into("x"), "type_into")
        expect_raise(lambda: d.shell("Write-Output x"), "shell")
        print("PASS: act / clear_field / type_into / shell all refuse without BRYES_ALLOW_HOST")

        # Capture must keep working with both gates off: the lesson pipeline depends on it.
        png = d.screenshot()
        assert png[:8] == b"\x89PNG\r\n\x1a\n", "screenshot must not be gated"
        w, h = Image.open(io.BytesIO(png)).size
        print(f"PASS: screenshot still works ungated ({w}x{h})")

        # ---- the coordinate translation ------------------------------------------------
        set_flags(host=True)
        fake = FakeInput()
        d = WindowsDevice(input=fake)
        d._origin_xy = lambda: (100, -200)          # a desk with a monitor above the primary
        d.act({"type": "click", "x": 10, "y": 20})
        assert fake.calls[-1] == ("click", 110, -180, "left"), fake.calls[-1]
        d.act({"type": "double_click", "x": 1, "y": 2})
        assert fake.calls[-1] == ("double_click", 101, -198), fake.calls[-1]
        d.act({"type": "right_click", "x": 1, "y": 2})
        assert fake.calls[-1] == ("right_click", 101, -198), fake.calls[-1]
        d.act({"type": "hover", "x": 3, "y": 4})
        assert fake.calls[-1] == ("hover", 103, -196), fake.calls[-1]
        print("PASS: image coordinates are translated by the live origin on every verb")

        d.act({"type": "scroll", "x": 5, "y": 6, "direction": "up"})
        assert fake.calls[-1] == ("scroll", 105, -194, 3), fake.calls[-1]
        d.act({"type": "scroll", "x": 5, "y": 6, "direction": "down"})
        assert fake.calls[-1] == ("scroll", 105, -194, -3), fake.calls[-1]
        d.act({"type": "drag", "x": 7, "y": 8, "x2": 9, "y2": 10})
        assert fake.calls[-1] == ("drag", 107, -192, 109, -190), fake.calls[-1]
        print("PASS: scroll is signed by direction, drag translates both ends")

        # key_hold: no coordinates to translate, and the span is clamped at the verb.
        d.act({"type": "key_hold", "key": "w", "seconds": 2})
        assert fake.calls[-1] == ("hold", "w", 2.0), fake.calls[-1]
        d.act({"type": "key_hold", "key": "w", "seconds": 99})
        assert fake.calls[-1] == ("hold", "w", 5.0), fake.calls[-1]
        d.act({"type": "key_hold", "key": "w"})
        assert fake.calls[-1] == ("hold", "w", 1.0), fake.calls[-1]
        print("PASS: key_hold passes the key through and clamps the span")

        d.act({"type": "type", "text": "hello"})
        assert fake.calls[-1] == ("type_text", "hello"), fake.calls[-1]
        d.act({"type": "key", "key": "ctrl+a"})
        assert fake.calls[-1] == ("press", "ctrl+a"), fake.calls[-1]
        d.clear_field()
        assert fake.calls[-2:] == [("press", "ctrl+a"), ("press", "delete")], fake.calls[-2:]
        print("PASS: type, key and clear_field reach the adapter")

        try:
            d.act({"type": "teleport"})
        except ValueError:
            pass
        else:
            raise AssertionError("an unknown verb was accepted")
        print("PASS: an unknown verb is refused, not ignored")

        # ---- the focus guard ------------------------------------------------------------
        d = WindowsDevice(window="NoSuchWindowAnywhere", input=FakeInput())
        d._origin_xy = lambda: (0, 0)
        expect_raise(lambda: d.act({"type": "click", "x": 1, "y": 1}), "act on a missing window")
        print("PASS: with a window named but absent, acting refuses instead of clicking blind")

        # ---- the target rect guard ------------------------------------------------------
        fake = FakeInput()
        d = WindowsDevice(hwnd=4242, input=fake)
        d._origin_xy = lambda: (0, 0)
        d._ensure_foreground = lambda *a, **k: None     # focus is a separate, live property
        d._target_rect = lambda: (100, 100, 400, 300)
        d.act({"type": "click", "x": 150, "y": 150})
        assert fake.calls[-1] == ("click", 150, 150, "left"), fake.calls[-1]
        for point in ((50, 150), (150, 350), (400, 200)):
            expect_raise(lambda p=point: d.act({"type": "click", "x": p[0], "y": p[1]}),
                         f"click outside the target at {point}")
        print("PASS: a click inside the target's rect lands; a click outside it is refused")

        # ---- shell has its own gate -----------------------------------------------------
        set_flags(host=True)                        # host allowed, shell NOT
        d = WindowsDevice(input=FakeInput())
        expect_raise(lambda: d.shell("Write-Output x"), "shell with only the host gate")
        print("PASS: shell refuses while BRYES_ALLOW_HOST_SHELL is unset")

        set_flags(host=True, shell=True)
        out = d.shell("Write-Output bryes-host-shell-ok")
        assert out["ok"] and "bryes-host-shell-ok" in out["stdout"], out
        print("PASS: shell round-trips with both gates set")

        print("\nPASS: all WindowsDevice driving checks green")
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    main()
