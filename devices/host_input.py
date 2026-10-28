"""BRYES — HostInput: the one module that touches `pyautogui`.

Everything above this file speaks **absolute screen coordinates** and semantic key names
(`Enter`, `ctrl+a`), because that is what the Brain already emits and what the Windows body
translates image space into. Everything below it is one library call.

Three things the library does not give us live here instead:

- **Fail-safe off.** Measured: with `FAILSAFE` on, a target outside the primary screen is
  treated as a screen corner and raises `FailSafeException` instead of moving, and the restore
  afterwards fails the same way. The body's foreground guard is the safety property that
  matters for this use; this flag only protects a human who yanks the mouse to a corner.
- **A seam.** The class is bound to `pyautogui` (or to a fake), so `act()` can be tested with
  no real pointer movement. A test that clicks the developer's desktop is not a test.
- **Layout-independent typing.** `write()` follows the active keyboard layout, so Indonesian
  text cannot be typed through it; anything non-ASCII goes via the clipboard instead.
"""
import time

import pyautogui
import pyperclip

# The Brain names keys the way a person does. PyAutoGUI already accepts most of these; the
# aliases are the synonyms a model reaches for that the library would reject.
_KEY_ALIASES = {
    "return": "enter",
    "esc": "escape",
    "del": "delete",
    "ins": "insert",
    "pgup": "pageup",
    "pgdn": "pagedown",
    "control": "ctrl",
    "win": "winleft",
    "cmd": "winleft",
    "super": "winleft",
}


def _key(name):
    token = str(name).strip().lower()
    return _KEY_ALIASES.get(token, token)


class HostInput:
    """Real pointer and keyboard events, in absolute screen pixels.

    `bind` and `clipboard` exist for tests: pass a recorder instead of the live modules and
    nothing moves.
    """

    def __init__(self, bind=None, clipboard=None):
        self._py = bind or pyautogui
        self._clipboard = clipboard or pyperclip
        # Measured: with the fail-safe on, a target outside the primary screen is treated as a
        # screen corner and raises instead of moving. Set here, not at import, so importing this
        # module never changes another user of pyautogui in the same process.
        self._py.FAILSAFE = False

    def hover(self, x, y):
        self._py.moveTo(x, y, duration=0)

    def move(self, x, y):
        """Put the pointer at (x, y) without clicking. Used to bring it back into the target."""
        self._py.moveTo(x, y, duration=0)

    def click(self, x, y, button="left"):
        self._py.click(x, y, button=button)

    def double_click(self, x, y):
        self._py.doubleClick(x, y)

    def right_click(self, x, y):
        self._py.rightClick(x, y)

    def scroll(self, x, y, clicks):
        """`clicks` is positive for up, negative for down (the library's own convention)."""
        self._py.moveTo(x, y, duration=0)
        self._py.scroll(clicks)

    def drag(self, x1, y1, x2, y2):
        self._py.moveTo(x1, y1, duration=0)
        self._py.dragTo(x2, y2, duration=0.2, button="left")

    def press(self, chord):
        """`Enter` presses once; `ctrl+a` is a hotkey. Unknown tokens pass through."""
        keys = [_key(part) for part in str(chord).split("+") if part.strip()]
        if not keys:
            return
        if len(keys) == 1:
            self._py.press(keys[0])
        else:
            self._py.hotkey(*keys)

    def hold(self, chord, seconds):
        """Press a key/chord DOWN, keep it down for `seconds`, then release it.

        A game samples key state every frame, so this is continuous movement where
        `press` is one tap. A single `Enter` holds one key; a chord holds every part
        and releases them in reverse order. The release lives in a `finally` because
        an exception mid-hold would otherwise leave a key down on the real desktop,
        and nothing here can press a key back up after the process dies.
        """
        keys = [_key(part) for part in str(chord).split("+") if part.strip()]
        if not keys:
            return
        pressed = []
        try:
            for key in keys:
                self._py.keyDown(key)
                pressed.append(key)      # only a key that actually went down
            time.sleep(max(0.0, float(seconds)))
        finally:
            # A partial press must be undone too: if the SECOND key of a chord raises,
            # the first is already down and nothing else will ever lift it.
            for key in reversed(pressed):
                self._py.keyUp(key)

    def type_text(self, text):
        """ASCII through the keyboard, anything else through the clipboard. Newlines are Enter."""
        text = str(text)
        if text.isascii():
            for index, line in enumerate(text.split("\n")):
                if index:
                    self._py.press("enter")
                if line:
                    self._py.write(line, interval=0)
        else:
            self._clipboard.copy(text)
            self._py.hotkey("ctrl", "v")

    def pointer(self):
        x, y = self._py.position()
        return (int(x), int(y))
