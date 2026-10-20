"""BRYES — WindowsDevice: the real Windows desktop as a Device (ADR-002).

The body Unreal Editor lives on. Built for RECORDING first: it screenshots (the whole
desktop, or one window by title) and runs a PowerShell command, and it advertises NO
pointer verbs. That last part is deliberate. Capture is what authoring a lesson needs;
driving the real desktop is a separate and unproven job, and an empty `verbs` set means
the loop can never offer the Brain a click this body cannot perform (ADR-006's one-body
rule still holds).

DPI is the trap this file exists to defuse. Unless the process declares itself
per-monitor DPI aware, `GetWindowRect` answers in LOGICAL pixels while `ImageGrab`
returns PHYSICAL ones on a scaled display, so the crop lands somewhere else entirely, or
misses the window. The awareness call runs once at import, before anything measures.

Why a window rect rather than a full grab: a lesson screenshot should show the editor,
not the desktop behind it. `window="Unreal"` is the normal case, and a title that matches
nothing RAISES, because falling back to the whole desktop would silently bake a worse
image into a tutorial.
"""
import ctypes
import io
import subprocess
import sys
import time
from ctypes import wintypes

from PIL import ImageGrab

from .base import Capabilities

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    try:                                      # PROCESS_PER_MONITOR_DPI_AWARE (Win 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass                              # measurement below is then best-effort


def _virtual_screen():
    """(width, height) of the WHOLE virtual desktop, the space a grab lands in.

    Not the primary screen: on a multi-monitor desk `ImageGrab(all_screens=True)` returns the
    union of every display (measured here as 2705x2520 on a 2560x1440 primary), and a window
    rect can even start at a negative origin. Advertising the primary would make the body lie
    about the size of the image it hands back.
    """
    if not _IS_WINDOWS:
        return (0, 0)
    user32 = ctypes.windll.user32
    return (user32.GetSystemMetrics(78), user32.GetSystemMetrics(79))   # SM_C[XY]VIRTUALSCREEN


_W, _H = _virtual_screen()

# Capture-only body: no pointer verbs, because none of them are implemented yet. The loop
# can still use it for wait/screenshot/done/fail and the PowerShell channel.
WINDOWS_CAPS = Capabilities(
    name="windows-desktop",
    width=_W,
    height=_H,
    verbs=frozenset(),
    has_shell=True,
    shell_flavor="powershell",
    keys={},
)


def _enum_windows():
    """[(hwnd, title, rect)] for every VISIBLE titled top-level window."""
    if not _IS_WINDOWS:
        return []
    user32 = ctypes.windll.user32
    found = []
    prototype = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            found.append((hwnd, buf.value,
                          (rect.left, rect.top, rect.right, rect.bottom)))
        return True

    user32.EnumWindows(prototype(visit), 0)
    return found


def list_windows():
    """[(title, (left, top, right, bottom))] for every VISIBLE titled top-level window."""
    return [(title, rect) for _hwnd, title, rect in _enum_windows()]


def find_window(title):
    """(hwnd, title, rect) of the LARGEST visible window whose title contains `title`.

    Largest, not first: a substring like "Unreal" also matches tooltips and helper windows,
    and the editor itself is the big one. Windows smaller than 200x200 are ignored outright.
    """
    needle = str(title).strip().lower()
    if not needle:
        return None
    best = None
    best_area = 0
    for hwnd, name, rect in _enum_windows():
        if needle not in str(name).lower():
            continue
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w < 200 or h < 200:
            continue
        if w * h > best_area:
            best, best_area = (hwnd, name, rect), w * h
    return best


def find_window_rect(title, windows=None):
    """The rect from find_window; `windows` is an injectable [(title, rect)] list for tests."""
    if windows is not None:
        best, best_area = None, 0
        needle = str(title).strip().lower()
        if not needle:
            return None
        for name, rect in windows:
            if needle not in str(name).lower():
                continue
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            if w < 200 or h < 200:
                continue
            if w * h > best_area:
                best, best_area = rect, w * h
        return best
    found = find_window(title)
    return found[2] if found else None


class WindowsDevice:
    """The real Windows desktop as a Device. Screenshot + PowerShell only, for now."""

    caps = WINDOWS_CAPS

    def __init__(self, window=None, raise_window=True):
        """`window` is a title substring; None captures the whole virtual desktop.

        `raise_window` brings the matched window to the foreground before the grab, because a
        screen grab returns whatever is RENDERED in that rect: a browser on top would be baked
        into the lesson as if it were the editor.
        """
        self._window = window
        self._raise = raise_window

    def _grab(self):
        if self._window:
            found = find_window(self._window)
            if found is None:
                raise RuntimeError(
                    f"no visible window matching {self._window!r} "
                    f"(run: python capture.py --list-windows)")
            hwnd, _name, rect = found
            if self._raise and _IS_WINDOWS:
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                time.sleep(0.25)                 # let the repaint land before grabbing
            return ImageGrab.grab(bbox=rect, all_screens=True)
        return ImageGrab.grab(all_screens=True)

    def screenshot(self):
        buf = io.BytesIO()
        self._grab().save(buf, "PNG")
        return buf.getvalue()

    def act(self, action):
        raise NotImplementedError(
            f"WindowsDevice is a capture-only body: {action.get('type')!r} is not built. "
            "ADRs 002/006 keep one body per run; driving the real desktop is a separate job.")

    def clear_field(self):
        raise NotImplementedError("WindowsDevice is a capture-only body: no clear gesture yet")

    def type_into(self, text, *, click_xy=None, clear_first=False, press_enter=False):
        raise NotImplementedError("WindowsDevice is a capture-only body: no text entry yet")

    def shell(self, command, timeout=None, stdin=None):
        """Run a NON-interactive PowerShell command; same result shape as the other bodies."""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", str(command)],
                input=stdin, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "exit_code": -1, "stdout": "", "stderr": "",
                    "timed_out": True}
        return {"ok": res.returncode == 0, "exit_code": res.returncode,
                "stdout": res.stdout, "stderr": res.stderr}

    def pointer(self):
        """The current cursor position, so a capture can be checked against the pointer's space."""
        if not _IS_WINDOWS:
            return None
        point = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
        return (point.x, point.y)
