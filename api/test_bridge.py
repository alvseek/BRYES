"""Model-free tests for the visual bridge (api/bridge.py). No screen, no model, no desktop.

    python api/test_bridge.py

The point of the injections: the surface's job is to pass the caller's words through to a body
and a locator, so a fake body and a fake locator are enough to prove it. What is NOT tested
here is the Windows enumeration (real windows) and the Eyes (a live call); both are exercised
once by hand when the bridge is pointed at the editor.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.bridge import make_app  # noqa: E402


class Caps:
    name = "fake-desktop"
    width = 100
    height = 100
    verbs = frozenset({"click", "double_click", "right_click", "hover", "drag", "type", "key"})
    has_shell = False
    shell_flavor = ""
    keys = {}


class FakeDevice:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.caps = Caps()
        self.actions = []

    def screenshot(self):
        return b"\x89PNG\r\n\x1a\nfake-frame"

    def act(self, action):
        if action.get("x") == -1:
            raise RuntimeError("refusing to act at (-1,0): outside the target window")
        self.actions.append(action)


WINDOWS = [
    {"id": "0x1a", "title": "BP_CombatBody_Party", "rect": [0, 0, 1920, 1040],
     "foreground": True},
    {"id": "0x2b", "title": "LSGI - Unreal Editor", "rect": [0, 0, 1920, 1040],
     "foreground": False},
]


def build():
    device = FakeDevice(None)
    app = make_app(device_factory=lambda hwnd: device,
                   locator=lambda _frame, instruction: {"x": 918, "y": 585},
                   window_lister=lambda: WINDOWS)
    return app, device


def test_health_and_windows():
    app, _ = build()
    c = app.test_client()
    r = c.get("/health")
    assert r.status_code == 200 and r.get_json() == {"ok": True}
    r = c.get("/windows")
    got = r.get_json()
    assert r.status_code == 200 and len(got) == 2
    assert got[0]["id"] == "0x1a" and got[0]["foreground"] is True
    assert got[1]["foreground"] is False
    print("PASS: /health and /windows answer from the injected lister")


def test_screenshot():
    app, _ = build()
    c = app.test_client()
    r = c.get("/screenshot?window=0x1a")
    assert r.status_code == 200
    assert r.mimetype == "image/png"
    assert r.data == b"\x89PNG\r\n\x1a\nfake-frame"
    r = c.get("/screenshot")
    assert r.status_code == 400            # no window named
    print("PASS: /screenshot returns the body's bytes, and 400 without a window")


def test_act_forwards_and_refuses():
    app, device = build()
    c = app.test_client()
    # non-JSON is refused: this is what keeps a cross-origin form post out
    assert c.post("/act", data="type=click&x=1&y=2").status_code == 415
    # unknown verb
    assert c.post("/act", json={"window": "0x1a", "type": "explode"}).status_code == 400
    # point verb without coordinates
    assert c.post("/act", json={"window": "0x1a", "type": "click"}).status_code == 400
    # drag missing an endpoint
    assert c.post("/act", json={"window": "0x1a", "type": "drag", "x": 1, "y": 2}).status_code == 400
    # a verb this body does not have
    assert c.post("/act", json={"window": "0x1a", "type": "key_hold",
                                "key": "w", "seconds": 1}).status_code == 400
    # the happy path forwards the caller's numbers untouched
    r = c.post("/act", json={"window": "0x1a", "type": "click", "x": 918, "y": 585})
    assert r.status_code == 200
    assert device.actions[-1] == {"type": "click", "x": 918, "y": 585}
    # a body refusal becomes a 409 with the body's own reason
    r = c.post("/act", json={"window": "0x1a", "type": "click", "x": -1, "y": 0})
    assert r.status_code == 409 and "outside the target window" in r.get_json()["description"]
    print("PASS: /act forwards pixels unchanged and refuses bad shapes, verbs and points")


def test_locate():
    app, _ = build()
    c = app.test_client()
    r = c.post("/locate", json={"window": "0x1a", "instruction": "the output pin"})
    assert r.status_code == 200
    assert r.get_json() == {"x": 918, "y": 585, "instruction": "the output pin"}
    assert c.post("/locate", json={"window": "0x1a"}).status_code == 400
    assert c.post("/locate", data="instruction=x").status_code == 415
    print("PASS: /locate returns the Eyes' pixel for the caller's words")


def test_profiles():
    app, _ = build()
    c = app.test_client()
    r = c.get("/profiles?path=windows/unreal-editor")
    assert r.status_code == 200
    body = r.get_json()
    assert body["path"] == "windows/unreal-editor"
    assert "UNREAL EDITOR" in body["visual"].upper()
    assert body["operating"].strip()
    assert c.get("/profiles?path=windows/nope").status_code == 404
    assert c.get("/profiles").status_code == 404
    print("PASS: /profiles serves the merged vocabulary, and 404s an unknown path")


if __name__ == "__main__":
    test_health_and_windows()
    test_screenshot()
    test_act_forwards_and_refuses()
    test_locate()
    test_profiles()
    print("PASS: all bridge tests green")
