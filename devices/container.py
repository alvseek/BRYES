"""BRYES — ContainerDevice: the original Screen+Hands+shell as a Device (ADR-002).

This is today's HTTP-backed body, unchanged in behavior: it drives the disposable
Ubuntu container (Xvfb + fluxbox + xdotool + scrot, Flask API on :8000) the loop has
always used. The transport (urllib over localhost:8000) and its cold-connection retry
are exactly as they were in agent/loop.py's screenshot()/hands()/exec_cmd() — only
relocated behind the Device Protocol so the loop can address it (and the phone, and a
future Windows desktop) uniformly.
"""
import json
import time
import urllib.error
import urllib.request

from .base import ALL_VERBS, Capabilities, default_type_into

try:                       # optional transcript logger (no-op when a run isn't logging)
    import runlog
except ImportError:
    runlog = None

SCREEN = "http://localhost:8000"

# The Brain names keys naturally; xdotool wants X keysyms. Most already match (Return, Escape,
# Tab, ctrl+a, single letters, modifiers), but models reach for synonyms — map those so a
# natural "Enter"/"Esc" doesn't 400. Device-specific translation (ADR-002): the phone body
# maps to Android keyevents instead. Unknown tokens (real keysyms, letters, modifiers) pass through.
_KEY_ALIASES = {
    "enter": "Return", "esc": "Escape", "del": "Delete", "ins": "Insert",
    "pgup": "Prior", "pageup": "Prior", "pgdn": "Next", "pagedown": "Next",
    "bksp": "BackSpace", "backspace": "BackSpace", "spacebar": "space",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
}


def _normalize_key(key):
    """Map a semantic key/chord to xdotool keysyms: 'Enter' -> 'Return',
    'ctrl+Enter' -> 'ctrl+Return'. Each '+'-separated token is mapped independently;
    tokens not in the alias table (letters, modifiers, real keysyms) pass through unchanged."""
    return "+".join(_KEY_ALIASES.get(p.strip().lower(), p.strip())
                    for p in str(key).split("+"))

# The container's Xvfb desktop is SCREEN_RESOLUTION=1280x800x24 (screen/scripts/entrypoint.sh).
# A full desktop body: every pointer verb, a bash shell, X keysyms/chords via xdotool
# (Return, Escape, ctrl+a). The Brain names keys semantically, so common natural synonyms are
# normalized to the keysym before sending (see _KEY_ALIASES) — else a plain "Enter" 400s.
DESKTOP_CAPS = Capabilities(
    name="docker-desktop",
    width=1280,
    height=800,
    verbs=ALL_VERBS,
    has_shell=True,
    shell_flavor="bash",
    keys={},
)


class ContainerDevice:
    """The Dockerized desktop as a Device. Behavior is byte-identical to the loop's
    former screenshot()/hands()/exec_cmd() helpers — same endpoints, same payloads,
    same 4-retry cold-connection handling, same transcript records."""

    caps = DESKTOP_CAPS

    def __init__(self, base_url=SCREEN):
        self._base = base_url

    def _open(self, req, retries=4):
        """urlopen with a few retries — the Screen's dev server can drop a cold connection."""
        for attempt in range(retries):
            try:
                return urllib.request.urlopen(req, timeout=15).read()
            except (urllib.error.URLError, ConnectionError):
                if attempt == retries - 1:
                    raise
                time.sleep(0.5 * (attempt + 1))

    def screenshot(self):
        return self._open(self._base + "/screenshot")

    def act(self, action):
        if action.get("type") == "key" and action.get("key"):
            action = {**action, "key": _normalize_key(action["key"])}
        req = urllib.request.Request(
            self._base + "/action", data=json.dumps(action).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        self._open(req)
        if runlog:
            runlog.record("action", action, "executed")

    def clear_field(self):
        """Clear the focused text field the X-desktop way: select-all, then delete."""
        self.act({"type": "key", "key": "ctrl+a"})
        self.act({"type": "key", "key": "Delete"})

    def type_into(self, text, *, click_xy=None, clear_first=False, press_enter=False):
        """One-gesture text entry (click? -> clear? -> type -> Enter?) via the shared
        composition; the desktop specifics (ctrl+a clear, Enter->Return) live in
        clear_field() and act()'s key normalization."""
        default_type_into(self, text, click_xy=click_xy, clear_first=clear_first,
                          press_enter=press_enter)

    def shell(self, command, timeout=None, stdin=None):
        payload = {"command": command}
        if timeout is not None:
            payload["timeout"] = timeout
        if stdin is not None:
            payload["stdin"] = stdin
        req = urllib.request.Request(
            self._base + "/exec", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        res = json.loads(self._open(req))
        if runlog:
            runlog.record("exec", payload, res)
        return res

    def pointer(self):
        data = json.loads(self._open(self._base + "/pointer"))
        return (data["x"], data["y"])
