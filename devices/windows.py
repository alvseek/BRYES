"""BRYES — WindowsDevice: the real Windows desktop as a Device (ADR-002).

Two jobs in one body, gated separately:

- **Capture always works.** `screenshot()` grabs the monitor that holds the target window (or the
  whole virtual desktop when no window is named), which is what `capture.py` and the lesson
  pipeline need.
- **Driving needs `BRYES_ALLOW_HOST=1`**, and `shell()` needs `BRYES_ALLOW_HOST_SHELL=1` on top.
  Nothing above the body knows this: `_make_device` refuses early with a readable error, and any
  other caller meets the gate at the verb itself. The gate is deliberately not in the
  constructor, because capture constructs this body too.

Coordinates arrive in IMAGE space (what the Eyes saw) and are translated to SCREEN space by
`screen_xy`, which adds the FRAME origin on every action. The frame is the target's monitor
(R10), so a two-screen desk no longer hands the Eyes a 3440x2520 image with the editor in half
of it. The origin is read per action, never cached: on a desk with a monitor above the primary
it was once (0,-1080), and the layout moved again during the session that wrote this.

DPI is the other trap this file defuses. Unless the process declares per-monitor DPI awareness,
`GetWindowRect` answers in logical pixels while `ImageGrab` returns physical ones, so the crop
lands somewhere else entirely. The awareness call runs once, at import.
"""
import ctypes
import io
import os
import subprocess
import sys
import time
from ctypes import wintypes
from dataclasses import replace

from PIL import ImageGrab

from .base import ALL_VERBS, Capabilities, clamp_hold, default_type_into

try:                       # optional transcript logger (no-op when a run isn't logging)
    import runlog
except ImportError:
    runlog = None

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


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


def foreground_is_target(foreground, target, owner_of, limit=8):
    """True when the target holds focus, or a window it owns does.

    `owner_of(hwnd)` returns a window's owner (GetWindow GW_OWNER). A menu is its own top-level
    window, hosted in the same process and owned by the window that opened it, so while a graph
    context menu is open the foreground window is the menu rather than the editor. Raising the
    editor at that moment dismisses the very menu the next keystroke was meant for, which makes
    every keyboard-first interaction (right-click, type a node name) impossible.

    Measured 2026-10-28 on the Unreal editor: after a right-click the foreground was an untitled
    `UnrealWindow` whose GW_OWNER was the blueprint window, while its GA_ROOTOWNER was the main
    editor window. So the chain is walked by OWNER, not by root owner, or the popup is missed.
    """
    if not target:
        return False
    handle = foreground
    for _ in range(limit):
        if not handle:
            return False
        if handle == target:
            return True
        handle = owner_of(handle)
    return False


def monitor_rect(hwnd):
    """(left, top, right, bottom) of the monitor holding `hwnd`, or None.

    Deterministic: the OS answers which display a window is on, so nothing here matches titles
    or guesses from geometry. A window straddling two displays resolves to the one holding most
    of it, which is what MONITOR_DEFAULTTONEAREST means.
    """
    if not _IS_WINDOWS or not hwnd:
        return None
    user32 = ctypes.windll.user32
    handle = user32.MonitorFromWindow(wintypes.HWND(hwnd), 2)   # MONITOR_DEFAULTTONEAREST
    if not handle:
        return None
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not user32.GetMonitorInfoW(handle, ctypes.byref(info)):
        return None
    m = info.rcMonitor
    return (m.left, m.top, m.right, m.bottom)

# A full desktop body: every pointer verb, and a PowerShell channel. Driving is gated at the
# verb, not here, because capture constructs this same body and must keep working.
WINDOWS_CAPS = Capabilities(
    name="windows-desktop",
    width=_W,
    height=_H,
    verbs=ALL_VERBS,
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


def windows_of_pid(pid):
    """[(hwnd, title, rect)] for the visible titled top-level windows OWNED by `pid`.

    This is how a driver names its target safely: the body launches the application, keeps the
    pid, and acts only on a window that process owns. A title substring cannot tell two editors
    apart, and on 2026-10-21 it drove someone else's document.
    """
    if not _IS_WINDOWS:
        return []
    out = []
    for hwnd, title, rect in _enum_windows():
        owner = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == int(pid):
            out.append((hwnd, title, rect))
    return out


def top_window_of_pid(pid):
    """(hwnd, title, rect) of the largest visible window `pid` owns, or None."""
    best, best_area = None, 0
    for hwnd, title, rect in windows_of_pid(pid):
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w < 100 or h < 60:
            continue
        if w * h > best_area:
            best, best_area = (hwnd, title, rect), w * h
    return best


def window_title(hwnd):
    """The current title of a window handle ('' when it has none or is gone)."""
    if not _IS_WINDOWS or not hwnd:
        return ""
    user32 = ctypes.windll.user32
    length = user32.GetWindowTextLengthW(hwnd)
    if not length:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def _env_flag(name):
    """True when an environment variable is set to something that reads as 'on'."""
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def host_allowed():
    """May this process drive the REAL desktop? Read by `_make_device` for an early refusal."""
    return _env_flag("BRYES_ALLOW_HOST")


def host_shell_allowed():
    """May this process run a command on the REAL desktop? Its own switch, on purpose."""
    return _env_flag("BRYES_ALLOW_HOST_SHELL")


class WindowsDevice:
    """The real Windows desktop as a Device: capture always, driving behind an environment gate."""

    caps = WINDOWS_CAPS

    def __init__(self, window=None, raise_window=True, input=None, hwnd=None):
        """`window` is a title substring; None means the whole virtual desktop.

        `hwnd` is the SAFE way to name a driving target: a handle the caller obtained from a
        process it started (`top_window_of_pid`). A title substring cannot tell two editors
        apart, so it is for capture only when `hwnd` is absent.

        `raise_window` brings the matched window to the foreground before a grab, because a
        screen grab returns whatever is RENDERED in that rect: a browser on top would be baked
        into the lesson as if it were the editor.

        `input` is the HostInput seam. Leave it None and the real one is created on first use,
        so a capture-only caller never imports pyautogui.
        """
        self._window = window
        self._hwnd = int(hwnd) if hwnd else None
        self._raise = raise_window
        self._input = input

    # ---- capability gates --------------------------------------------------------------
    def _require_host(self):
        if not host_allowed():
            raise RuntimeError(
                "WindowsDevice refuses to act on the real desktop: set BRYES_ALLOW_HOST=1. "
                "Screenshots are not gated; only driving and shell are.")

    def _require_host_shell(self):
        self._require_host()
        if not host_shell_allowed():
            raise RuntimeError(
                "WindowsDevice.shell() is gated separately: set BRYES_ALLOW_HOST_SHELL=1. "
                "A click can be undone by noticing it; a recursive delete cannot.")

    # ---- geometry ----------------------------------------------------------------------
    @property
    def caps(self):
        """What this body can do, sized to the frame it will actually hand back.

        A run names one window (R9), so the frame is that window's monitor and the Brain is told
        the truth about the image it sees. Without a target the virtual desktop is still the
        frame, which is what capture wants. Never raises: if the window vanished, this reports
        the desktop size and `screenshot()` is where the loud failure belongs.
        """
        rect = self._frame_rect_or_none()
        if rect is None:
            return WINDOWS_CAPS
        width, height = rect[2] - rect[0], rect[3] - rect[1]
        if (width, height) == (WINDOWS_CAPS.width, WINDOWS_CAPS.height):
            return WINDOWS_CAPS
        return replace(WINDOWS_CAPS, width=width, height=height)

    def _origin_xy(self):
        """The live virtual-desktop origin. Never cached: a display can change mid-run."""
        if not _IS_WINDOWS:
            return (0, 0)
        user32 = ctypes.windll.user32
        return (user32.GetSystemMetrics(76), user32.GetSystemMetrics(77))

    def _desktop_rect(self):
        """The whole virtual desktop in screen coordinates, origin included (read live)."""
        origin_x, origin_y = self._origin_xy()
        width, height = _virtual_screen()
        return (origin_x, origin_y, origin_x + width, origin_y + height)

    def _frame_rect_or_none(self):
        """The rect `screenshot()` grabs: the target's monitor, or the desktop when none is named.

        Returns None only when a window WAS named and can no longer be found, so callers that
        must not raise (the caps property) can fall back.
        """
        if not self._window and not self._hwnd:
            return self._desktop_rect()
        hwnd = self._target_hwnd()
        if hwnd is None:
            return None
        return monitor_rect(hwnd)

    def _frame_rect(self):
        """The rect `screenshot()` grabs, raising rather than silently changing shape.

        A frame that quietly switches from a monitor to the desktop keeps every coordinate valid
        in the wrong space, which is a click 1000 px away with no error anywhere.
        """
        rect = self._frame_rect_or_none()
        if rect is None:
            raise RuntimeError(
                f"no visible window matching {self._window!r} any more, so the frame is unknown")
        return rect

    def screen_xy(self, x, y):
        """Image-space pixel (what the Eyes saw) -> absolute screen pixel (what the OS uses)."""
        left, top, _right, _bottom = self._frame_rect()
        return (int(x) + left, int(y) + top)

    def _get_input(self):
        if self._input is None:
            from .host_input import HostInput   # lazy: capture-only use never imports pyautogui
            self._input = HostInput()
        return self._input

    def _target_rect(self):
        """(left, top, right, bottom) of the handle, or None when no handle is set."""
        if not self._hwnd or not _IS_WINDOWS:
            return None
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
        return (rect.left, rect.top, rect.right, rect.bottom)

    def _require_inside_target(self, x, y):
        """A point outside the target handle is refused, not clicked.

        The foreground guard proves the right window is in front; it does not stop a coordinate
        that lands on something else entirely. This does, and it is the difference between a
        failed step and a click into whatever happens to sit beside the target.
        """
        rect = self._target_rect()
        if rect is None:
            return
        left, top, right, bottom = rect
        if not (left <= x < right and top <= y < bottom):
            raise RuntimeError(
                f"refusing to act at ({x},{y}): outside the target window "
                f"({left},{top})-({right},{bottom})")

    # ---- focus -------------------------------------------------------------------------
    def _target_hwnd(self):
        """The handle to keep in front: the one given, or the largest window matching a title.

        A handle is stable; a title is a guess. Callers that STARTED their target should pass
        `hwnd=` and never rely on this fallback.
        """
        if self._hwnd:
            return self._hwnd
        if not self._window:
            return None
        found = find_window(self._window)
        return found[0] if found else None

    def _ensure_foreground(self, attempts=3):
        """Keep the target window in front before acting.

        With no window named there is nothing to guard: the caller asked for the whole desktop,
        which means clicking whatever the coordinates point at is the intent.
        """
        if (not self._window and not self._hwnd) or not _IS_WINDOWS:
            return
        user32 = ctypes.windll.user32

        def owner_of(handle):
            return user32.GetWindow(wintypes.HWND(handle), 4)   # GW_OWNER

        for _ in range(attempts):
            hwnd = self._target_hwnd()
            if hwnd is None:
                raise RuntimeError(
                    f"no visible window matching {self._window!r} any more")
            if foreground_is_target(user32.GetForegroundWindow(), hwnd, owner_of):
                return
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.15)
        raise RuntimeError(
            f"could not bring the target window to the foreground after {attempts} attempts; "
            "refusing to act on whatever holds focus instead")

    # ---- capture -----------------------------------------------------------------------
    def grab_window(self):
        """The named window's rect only. For CAPTURE (lessons), never for driving.

        A window crop's (0,0) is the window's corner, so any coordinate read off it is not a
        screen coordinate. Driving therefore always uses `screenshot()` (the full desktop),
        and this method exists for the lesson pipeline, which wants the editor and nothing else.
        """
        if self._hwnd:
            rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(self._hwnd, ctypes.byref(rect))
            hwnd, rect = self._hwnd, (rect.left, rect.top, rect.right, rect.bottom)
        else:
            if not self._window:
                raise RuntimeError("grab_window() needs a window title or an hwnd")
            found = find_window(self._window)
            if found is None:
                raise RuntimeError(
                    f"no visible window matching {self._window!r} "
                    f"(run: python capture.py --list-windows)")
            hwnd, _name, rect = found
        if self._raise and _IS_WINDOWS:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            time.sleep(0.25)                 # let the repaint land before grabbing
        buf = io.BytesIO()
        ImageGrab.grab(bbox=rect, all_screens=True).save(buf, "PNG")
        return buf.getvalue()

    def screenshot(self):
        """The frame the Eyes read: the target's monitor, or the whole desktop with no target.

        The frame and the coordinate space are the same rect, so a pixel the Eyes return maps
        back through `screen_xy` by the frame origin (R10). `grab_window()` stays the tighter
        window-rect grab, and only capture uses it.
        """
        img = ImageGrab.grab(bbox=self._frame_rect(), all_screens=True)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()

    # ---- driving -----------------------------------------------------------------------
    def act(self, action):
        """One pointer/keyboard action, with image coordinates translated to screen ones."""
        self._require_host()
        verb = action.get("type")
        inp = self._get_input()
        self._ensure_foreground()

        if verb == "hover":
            x, y = self.screen_xy(action["x"], action["y"])
            self._require_inside_target(x, y)
            inp.hover(x, y)
        elif verb in ("click", "double_click", "right_click"):
            x, y = self.screen_xy(action["x"], action["y"])
            self._require_inside_target(x, y)
            {"click": inp.click,
             "double_click": inp.double_click,
             "right_click": inp.right_click}[verb](x, y)
        elif verb == "scroll":
            x, y = self.screen_xy(action["x"], action["y"])
            self._require_inside_target(x, y)
            # The Brain sends a direction, not an amount; three notches is the container's
            # implicit amount too, so a scroll means the same thing on both bodies.
            up = str(action.get("direction", "down")).lower() == "up"
            inp.scroll(x, y, 3 if up else -3)
        elif verb == "drag":
            x1, y1 = self.screen_xy(action["x"], action["y"])
            x2, y2 = self.screen_xy(action["x2"], action["y2"])
            self._require_inside_target(x1, y1)
            self._require_inside_target(x2, y2)
            inp.drag(x1, y1, x2, y2)
        elif verb == "type":
            inp.type_text(action.get("text", ""))
        elif verb == "key":
            inp.press(action.get("key", ""))
        elif verb == "key_hold":
            # A held key is continuous movement where a tap is one step. The span is
            # clamped here as well as in the loop: this path is also reachable directly.
            inp.hold(action.get("key", ""), clamp_hold(action.get("seconds")))
        else:
            raise ValueError(f"WindowsDevice cannot perform {verb!r}")

        if runlog:
            runlog.record("action", action, "executed")

    def clear_field(self):
        """Clear the focused field the Windows way: select all, then delete."""
        self._require_host()
        self._ensure_foreground()
        inp = self._get_input()
        inp.press("ctrl+a")
        inp.press("delete")

    def type_into(self, text, *, click_xy=None, clear_first=False, press_enter=False):
        self._require_host()          # fail before the first click, not halfway through
        default_type_into(self, text, click_xy=click_xy, clear_first=clear_first,
                          press_enter=press_enter)

    def shell(self, command, timeout=None, stdin=None):
        """Run a NON-interactive PowerShell command; same result shape as the other bodies."""
        self._require_host_shell()
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
