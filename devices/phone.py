"""BRYES — PhoneDevice: a real Android phone as a Device, over adb/USB (ADR-002).

The second body. Same Device contract as ContainerDevice, different transport: instead
of HTTP to a container, this shells out to `adb` against a physically-connected phone.

  screenshot()  -> adb exec-out screencap -p   (raw PNG bytes, binary-clean via subprocess)
  act()         -> adb shell input tap/swipe/text/keyevent
  shell()       -> adb shell <command>         (Tier-2, on the phone's own shell)

Its Capabilities differ from the desktop's — first-class, not flattened: no right_click
or hover (a touchscreen has neither), scroll/drag become swipes, keys are Android
KEYCODEs (Back/Home/...), coordinates are portrait. The Eyes/Brain/loop don't change.
"""
import subprocess
from dataclasses import replace
from pathlib import Path

from .base import Capabilities

try:                       # optional transcript logger (no-op when a run isn't logging)
    import runlog
except ImportError:
    runlog = None

# adb ships in the gitignored tools/ (installed in Phase 0). Resolved relative to the repo
# root, not the cwd — like eyes/brain resolve .env — so it works whatever the caller's dir.
_DEFAULT_ADB = Path(__file__).resolve().parent.parent / "tools" / "platform-tools" / "adb.exe"

_MAX_OUT = 4096            # cap each shell stream fed back to the Brain (bounds size, not time)

# A touchscreen body: no right_click / hover; scroll+drag are swipes; Android KEYCODEs.
PHONE_VERBS = frozenset({"click", "double_click", "scroll", "drag", "type", "key"})
PHONE_KEYS = {
    "Back": "KEYCODE_BACK", "Home": "KEYCODE_HOME", "Enter": "KEYCODE_ENTER",
    "Menu": "KEYCODE_MENU", "AppSwitch": "KEYCODE_APP_SWITCH", "Tab": "KEYCODE_TAB",
    "Space": "KEYCODE_SPACE", "Delete": "KEYCODE_DEL", "Escape": "KEYCODE_ESCAPE",
    "VolumeUp": "KEYCODE_VOLUME_UP", "VolumeDown": "KEYCODE_VOLUME_DOWN",
}
# width/height are filled from the live device (wm size) at init; these are the fallback.
PHONE_CAPS = Capabilities(
    name="android-phone", width=1080, height=2400,
    verbs=PHONE_VERBS, has_shell=True, shell_flavor="android", keys=PHONE_KEYS,
)


def _clip(s, limit=_MAX_OUT):
    s = s or ""
    if len(s) <= limit:
        return s
    half = limit // 2
    return f"{s[:half]}\n...[{len(s) - limit} chars elided]...\n{s[-half:]}"


class PhoneDevice:
    """A physical Android phone, driven over adb (USB). Satisfies the Device Protocol."""

    def __init__(self, adb_path=None, serial=None):
        self._adb = str(adb_path or _DEFAULT_ADB)
        self._serial = serial or self._only_device()
        self._assert_live()
        w, h = self._screen_size()
        self.caps = replace(PHONE_CAPS, width=w, height=h)
        # Keep the screen awake while tethered so the loop doesn't act on a dark screen.
        self._run("shell", "svc", "power", "stayon", "usb")

    # -- adb plumbing --------------------------------------------------------

    def _run(self, *args, timeout=30, text=True, input=None):
        """Run `adb -s <serial> <args...>` and return the CompletedProcess."""
        cmd = [self._adb]
        if self._serial:
            cmd += ["-s", self._serial]
        cmd += list(args)
        return subprocess.run(cmd, capture_output=True, text=text, input=input,
                              timeout=timeout, errors="replace" if text else None)

    def _only_device(self):
        """Serial of the single attached device, or raise if 0 or >1."""
        out = subprocess.run([self._adb, "devices"], capture_output=True, text=True).stdout
        devs = [ln.split("\t")[0] for ln in out.splitlines()[1:]
                if "\tdevice" in ln]
        if not devs:
            raise RuntimeError("no authorized adb device (check USB + 'Allow debugging')")
        if len(devs) > 1:
            raise RuntimeError(f"multiple adb devices {devs}; pass serial=... to PhoneDevice")
        return devs[0]

    def _assert_live(self):
        out = subprocess.run([self._adb, "devices"], capture_output=True, text=True).stdout
        if f"{self._serial}\tdevice" not in out:
            raise RuntimeError(
                f"adb device {self._serial!r} not ready (unauthorized/offline?):\n{out}")

    def _screen_size(self):
        """(width, height) from `wm size` — override the fallback so any phone works."""
        try:
            out = self._run("shell", "wm", "size").stdout or ""
            # "Physical size: 1080x2400"  (may also show "Override size:")
            line = [l for l in out.splitlines() if "size:" in l][-1]
            w, h = line.split(":")[1].strip().split("x")
            return int(w), int(h)
        except Exception:
            return PHONE_CAPS.width, PHONE_CAPS.height

    # -- Device protocol -----------------------------------------------------

    def screenshot(self):
        # exec-out keeps stdout binary-clean (no CRLF translation); subprocess captures bytes.
        return self._run("exec-out", "screencap", "-p", text=False).stdout

    def act(self, action):
        t = action.get("type")
        if t == "click":
            self._input("tap", action["x"], action["y"])
        elif t == "double_click":
            self._input("tap", action["x"], action["y"])
            self._input("tap", action["x"], action["y"])
        elif t == "scroll":
            self._swipe_scroll(action["x"], action["y"],
                               (action.get("direction") or "down").lower())
        elif t == "drag":
            self._input("swipe", action["x"], action["y"], action["x2"], action["y2"], 500)
        elif t == "type":
            # input text: %s stands for a space; ASCII first-proof only (emoji/special
            # chars deferred — needs ADBKeyboard, out of scope).
            self._input("text", str(action.get("text", "")).replace(" ", "%s"))
        elif t == "key":
            self._input("keyevent", self._keycode(action.get("key", "")))
        else:
            raise ValueError(f"PhoneDevice: unsupported action {t!r}")
        if runlog:
            runlog.record("action", action, "executed")

    def shell(self, command, timeout=None, stdin=None):
        try:
            r = self._run("shell", command, timeout=(timeout or 30), input=stdin)
        except subprocess.TimeoutExpired:
            res = {"ok": False, "exit_code": None, "stdout": "",
                   "stderr": f"timed out after {timeout or 30}s", "timed_out": True}
        else:
            res = {"ok": r.returncode == 0, "exit_code": r.returncode,
                   "stdout": _clip(r.stdout), "stderr": _clip(r.stderr)}
        if runlog:
            runlog.record("exec", {"command": command}, res)
        return res

    def pointer(self):
        return None            # a touchscreen has no queryable pointer

    # -- helpers -------------------------------------------------------------

    def _input(self, *args):
        self._run("shell", "input", *[str(a) for a in args])

    def _swipe_scroll(self, x, y, direction):
        """A wheel-scroll becomes a swipe. 'down' (reveal content below) = finger swipes
        UP; 'up' = finger swipes down. Distance scales with the screen; 300ms = controlled."""
        dist = min(700, self.caps.height // 3)
        half = dist // 2
        top = max(0, y - half)
        bot = min(self.caps.height - 1, y + half)
        if direction == "up":
            y1, y2 = top, bot          # finger down -> content scrolls up
        else:
            y1, y2 = bot, top          # finger up -> content scrolls down
        self._input("swipe", x, y1, x, y2, 300)

    def _keycode(self, key):
        """Map a named key to an Android KEYCODE. Accepts our names (Back/Home/...),
        a raw KEYCODE_*, or a bare letter/number."""
        if key in PHONE_KEYS:
            return PHONE_KEYS[key]
        if key.upper().startswith("KEYCODE_"):
            return key.upper()
        if key in ("Return", "\n"):
            return "KEYCODE_ENTER"
        if len(key) == 1 and key.isalnum():
            return f"KEYCODE_{key.upper()}"
        return key             # best-effort passthrough
