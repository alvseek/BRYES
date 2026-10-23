"""BRYES — HostInput adapter tests (model-free, and mouse-free).

Every call goes into a recorder, so this file proves the mapping without touching the real
pointer. What it checks is the part that is ours rather than the library's: the key aliases,
the chord form, and the ASCII-versus-clipboard split.

Run:  python devices/test_host_input.py
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from devices import host_input as hi  # noqa: E402
from devices.host_input import HostInput  # noqa: E402


class RecorderPy:
    """Stands in for pyautogui. Records every call as (name, args, kwargs)."""

    def __init__(self):
        self.calls = []
        self.FAILSAFE = True

    def _rec(self, name, *args, **kwargs):
        self.calls.append((name, args, kwargs))

    def moveTo(self, x, y, duration=0):
        self._rec("moveTo", x, y, duration=duration)

    def click(self, x, y, button="left"):
        self._rec("click", x, y, button=button)

    def doubleClick(self, x, y):
        self._rec("doubleClick", x, y)

    def rightClick(self, x, y):
        self._rec("rightClick", x, y)

    def scroll(self, clicks):
        self._rec("scroll", clicks)

    def dragTo(self, x, y, duration=0, button="left"):
        self._rec("dragTo", x, y, duration=duration, button=button)

    def press(self, key):
        self._rec("press", key)

    def keyDown(self, key):
        self._rec("keyDown", key)

    def keyUp(self, key):
        self._rec("keyUp", key)

    def hotkey(self, *keys):
        self._rec("hotkey", *keys)

    def write(self, text, interval=0):
        self._rec("write", text, interval=interval)

    def position(self):
        return (11, 22)


class RecorderClipboard:
    def __init__(self):
        self.copied = []

    def copy(self, text):
        self.copied.append(text)


def names(py):
    return [call[0] for call in py.calls]


def main():
    py, clip = RecorderPy(), RecorderClipboard()
    h = HostInput(bind=py, clipboard=clip)

    h.click(100, 200)
    assert py.calls[-1] == ("click", (100, 200), {"button": "left"}), py.calls[-1]
    h.right_click(5, 6)
    assert names(py)[-1] == "rightClick", names(py)
    h.double_click(7, 8)
    assert names(py)[-1] == "doubleClick", names(py)
    h.hover(9, 10)
    assert py.calls[-1] == ("moveTo", (9, 10), {"duration": 0}), py.calls[-1]
    print("PASS: pointer verbs map one-to-one")

    h.scroll(50, 60, -3)
    assert py.calls[-2] == ("moveTo", (50, 60), {"duration": 0}), py.calls[-2]
    assert py.calls[-1] == ("scroll", (-3,), {}), py.calls[-1]
    print("PASS: scroll moves to the point first, then scrolls by the signed amount")

    h.drag(1, 2, 3, 4)
    assert names(py)[-2:] == ["moveTo", "dragTo"], names(py)[-2:]
    assert py.calls[-1][1] == (3, 4), py.calls[-1]
    print("PASS: drag moves to the start, then drags to the end")

    h.press("Enter")
    assert py.calls[-1] == ("press", ("enter",), {}), py.calls[-1]
    h.press("Esc")
    assert py.calls[-1] == ("press", ("escape",), {}), py.calls[-1]
    h.press("ctrl+a")
    assert py.calls[-1] == ("hotkey", ("ctrl", "a"), {}), py.calls[-1]
    h.press("ctrl+SHIFT+Escape")
    assert py.calls[-1] == ("hotkey", ("ctrl", "shift", "escape"), {}), py.calls[-1]
    print("PASS: keys alias, and a chord becomes a hotkey without the case surviving")

    # key_hold: down, keep down for the span, release. The sleep is recorded rather than
    # performed, and `hi.time` is swapped only on this module so the real clock is untouched.
    real_time = hi.time
    try:
        slept = []
        hi.time = SimpleNamespace(sleep=lambda s: slept.append(s))

        before = len(py.calls)
        h.hold("w", 2.0)
        got = [(c[0], c[1]) for c in py.calls[before:]]
        assert got == [("keyDown", ("w",)), ("keyUp", ("w",))], got
        assert slept == [2.0], slept
        print("PASS: key_hold presses down, holds for the span, releases")

        before = len(py.calls)
        h.hold("ctrl+SHIFT", 0.5)
        assert [c[0] for c in py.calls[before:]] == ["keyDown", "keyDown", "keyUp", "keyUp"]
        assert [c[1][0] for c in py.calls[before:]] == ["ctrl", "shift", "shift", "ctrl"]
        print("PASS: a held chord goes down in order and comes up in reverse")

        def _boom(_seconds):
            raise RuntimeError("killed mid-hold")

        hi.time = SimpleNamespace(sleep=_boom)
        before = len(py.calls)
        try:
            h.hold("w", 1.0)
        except RuntimeError:
            pass
        assert [c[0] for c in py.calls[before:]] == ["keyDown", "keyUp"], py.calls[before:]
        print("PASS: an exception mid-hold still releases the key")
    finally:
        hi.time = real_time

    # A chord whose SECOND key refuses must still lift the first: a stuck modifier
    # outlives the run, and no later action presses it up.
    class _RefuseSecond(RecorderPy):
        def keyDown(self, key):
            if key == "shift":
                raise RuntimeError("refused by the window manager")
            super().keyDown(key)

    refusing = _RefuseSecond()
    h2 = HostInput(bind=refusing, clipboard=RecorderClipboard())
    try:
        h2.hold("ctrl+shift", 1.0)
    except RuntimeError:
        pass
    assert [c[0] for c in refusing.calls] == ["keyDown", "keyUp"], refusing.calls
    assert refusing.calls[-1][1] == ("ctrl",), refusing.calls[-1]
    print("PASS: a refused chord still lifts the keys that did go down")

    h.type_text("hello world")
    assert py.calls[-1] == ("write", ("hello world",), {"interval": 0}), py.calls[-1]
    assert not clip.copied, "ASCII must not touch the clipboard"
    h.type_text("one\ntwo")
    assert [c[0] for c in py.calls[-3:]] == ["write", "press", "write"], py.calls[-3:]
    assert py.calls[-2] == ("press", ("enter",), {}), py.calls[-2]
    h.type_text("harga Rp1.250.000")
    assert py.calls[-1] == ("write", ("harga Rp1.250.000",), {"interval": 0}), \
        "digits and dots are ASCII, so they type directly"
    h.type_text("harga \u2014 diskon")            # em dash: not ASCII
    assert py.calls[-1] == ("hotkey", ("ctrl", "v"), {}), py.calls[-1]
    assert clip.copied == ["harga \u2014 diskon"], clip.copied
    print("PASS: ASCII types directly, non-ASCII pastes via the clipboard")

    assert h.pointer() == (11, 22), h.pointer()
    print("PASS: pointer reports the library position as ints")

    print("\nPASS: all HostInput checks green")


if __name__ == "__main__":
    main()
