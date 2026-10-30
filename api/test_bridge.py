"""Model-free tests for the visual bridge (api/bridge-windows.py). No screen, no model, no desktop.

    python api/test_bridge.py

The point of the injections: the surface's job is to pass the caller's words through to a body
and a locator, so a fake body and a fake locator are enough to prove it. What is NOT tested
here is the Windows enumeration (real windows) and the Eyes (a live call); both are exercised
once by hand when the bridge is pointed at the editor.
"""
import importlib.util
import io
import json
import sys
import threading
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_spec = importlib.util.spec_from_file_location(
    "bridge_windows", Path(__file__).with_name("bridge-windows.py"))
_bridge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bridge)
make_app = _bridge.make_app


def _png(width=100, height=100):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (10, 20, 30)).save(buf, "PNG")
    return buf.getvalue()


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
        self.pos = (960, 540)
        self.png = _png(100, 100)

    def screenshot(self):
        return self.png

    def act(self, action):
        if action.get("x") == -1:
            raise RuntimeError("refusing to act at (-1,0): outside the target window")
        self.actions.append(action)

    def pointer(self):
        return self.pos


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
                   window_lister=lambda: WINDOWS,
                   frame_provider=lambda hwnd: (-100, -50, 1820, 1030))
    return app, device


def test_target_resolver():
    app, _ = build()
    calls = []

    def lister():
        calls.append(True)
        return WINDOWS

    with app.test_request_context():
        assert _bridge._resolve_target({"title": "  UNREAL editor "}, lister)[0] == 0x2b
        assert _bridge._resolve_target({"window": "001A"}, lister)[0] == 0x1a
        assert _bridge._resolve_target({}, lister, required=False) == (None, None)
        for args, expected in [({"window": "0x0"}, 400), ({"window": "-1"}, 400),
                               ({"window": None}, 400), ({"window": 26}, 400),
                               ({"title": " "}, 400), ({"title": None}, 400),
                               ({"title": []}, 400), ({}, 400),
                               ({"title": "x", "window": "0x1a"}, 400),
                               ({"title": "missing"}, 404), ({"window": "0xff"}, 404),
                               ({"title": "o"}, 409)]:
            try:
                _bridge._resolve_target(args, lister)
                raise AssertionError(args)
            except _bridge.HTTPException as exc:
                status = exc.response.status_code if exc.response else exc.code
                assert status == expected, (args, status)
                if status == 409:
                    assert len(exc.response.get_json()["matches"]) == 2
    assert len(calls) == 5
    print("PASS: target resolver validates selectors and refuses ambiguous or missing windows")


def test_target_routes():
    calls, handles, inputs, models = [], [], [], []
    device = FakeDevice(None)
    device.act = lambda action: inputs.append(action)
    app = make_app(device_factory=lambda hwnd: (handles.append(hwnd), device)[1],
                   locator=lambda *_: (models.append(True), {"x": 1, "y": 2})[1],
                   window_lister=lambda: (calls.append(True), WINDOWS)[1],
                   frame_provider=lambda _: (0, 0, 100, 100))
    c = app.test_client()
    for selector in ("window=0x1a", "title=party"):
        for path in ("pointer", "screenshot", "downscaleshot",
                     "upscaleshot?x1=0&y1=0&x2=10&y2=10"):
            join = "&" if "?" in path else "?"
            assert c.get(f"/{path}{join}{selector}").status_code == 200
    for selector in ({"window": "0x1a"}, {"title": "party"}):
        assert c.post("/locate", json={**selector, "instruction": "x"}).status_code == 200
        calls.clear()
        actions = [{"type": "type", "text": "a"}, {"type": "key", "key": "enter"}]
        assert c.post("/act", json={**selector, "actions": actions}).status_code == 200
        assert len(calls) == 1 and handles[-1] == 0x1a and inputs[-2:] == actions
    before = (len(handles), len(inputs), len(models))
    for path in ("pointer", "screenshot", "downscaleshot", "upscaleshot"):
        assert c.get(f"/{path}?title=missing").status_code == 404
    assert c.post("/locate", json={"title": "missing", "instruction": "x"}).status_code == 404
    assert c.post("/act", json={"window": "0xff", "type": "key", "key": "a"}).status_code == 404
    assert (len(handles), len(inputs), len(models)) == before
    assert c.post("/act", json={"window": "0x1a", "actions": [
        {"type": "key", "key": "x", "title": "party"}]}).status_code == 400
    print("PASS: target routes resolve once and refuse missing targets before device or model access")


def test_focused_capture():
    device = FakeDevice(None)
    events = []
    device.pos = (-90, -40)
    device.act = lambda action: events.append(action)
    device.screenshot = lambda: (events.append("shot"), _png())[1]
    windows = [{"id": "0x1a", "title": "target", "rect": [-100, -50, 0, 50]}]
    app = make_app(device_factory=lambda _: device, window_lister=lambda: windows,
                   frame_provider=lambda _: (-100, -50, 0, 50))
    c = app.test_client()
    sleep = _bridge.time.sleep
    _bridge.time.sleep = lambda _: None
    try:
        for path in ("screenshot", "downscaleshot", "upscaleshot"):
            extra = {"x1": 0, "y1": 0, "x2": 10, "y2": 10} if path == "upscaleshot" else {}
            events.clear()
            r = c.post("/" + path, json={"title": "target", "raise": True, **extra})
            assert r.status_code == 200 and events == [{"type": "hover", "x": 10, "y": 10}, "shot"]
        device.pos = (500, 500)
        events.clear()
        assert c.post("/screenshot", json={"window": "0x1a", "raise": True}).status_code == 200
        assert events[0] == {"type": "hover", "x": 50, "y": 50}
        for body in ({"window": "0x1a", "raise": "false"},
                     {"window": "0x1a", "raise": True, "x1": 0, "y1": 0, "x2": 101, "y2": 10},
                     {"window": "0x1a", "raise": True, "scale": True}):
            events.clear()
            assert c.post("/upscaleshot", json=body).status_code == 400
            assert events == []
        events.clear()
        assert c.post("/screenshot", json={"window": "0x1a", "raise": False}).status_code == 200
        assert events == ["shot"]
        assert c.get("/screenshot?window=0x1a&raise=true").status_code == 400
        assert c.post("/screenshot", data="x").status_code == 415
        device.act = lambda _: (_ for _ in ()).throw(RuntimeError("gate"))
        assert c.post("/screenshot", json={"window": "0x1a", "raise": True}).status_code == 409
    finally:
        _bridge.time.sleep = sleep
    print("PASS: focused captures validate before input and preserve frame coordinates")


def test_focus_capture_lock():
    entered, release, attempted, done = (threading.Event() for _ in range(4))
    events = []
    device = FakeDevice(None)
    device.pos = (10, 10)

    def act(action):
        events.append(action["type"])
        if action["type"] == "hover":
            entered.set()
            assert release.wait(5)

    device.act = act
    device.screenshot = lambda: (events.append("shot"), _png())[1]
    app = make_app(device_factory=lambda _: device, window_lister=lambda: WINDOWS,
                   frame_provider=lambda _: (0, 0, 100, 100))
    sleep = _bridge.time.sleep
    _bridge.time.sleep = lambda _: None

    def capture_thread():
        with app.test_client() as c:
            assert c.post("/screenshot", json={"window": "0x1a", "raise": True}).status_code == 200

    def action_thread():
        attempted.set()
        with app.test_client() as c:
            assert c.post("/act", json={"window": "0x1a", "type": "key", "key": "x"}).status_code == 200
        done.set()

    try:
        a = threading.Thread(target=capture_thread)
        b = threading.Thread(target=action_thread)
        a.start()
        assert entered.wait(5)
        b.start()
        assert attempted.wait(5) and not done.is_set()
        release.set()
        a.join(5)
        b.join(5)
        assert done.is_set() and events == ["hover", "shot", "key"]
    finally:
        release.set()
        _bridge.time.sleep = sleep
    print("PASS: another input cannot interleave between focus and capture")


def test_error_contract():
    app, device = build()
    c = app.test_client()
    app.logger.disabled = True
    for path, status in (("/missing", 404), ("/act", 405), ("/profiles?path=missing", 404)):
        r = c.get(path)
        assert r.status_code == status and r.is_json and {"error", "description"} <= r.get_json().keys()
    for data in ("null", "[]", '"x"', "{"):
        r = c.post("/locate", data=data, content_type="application/json")
        assert r.status_code == 400 and r.is_json
    device.pointer = lambda: (_ for _ in ()).throw(RuntimeError("pointer refused"))
    assert c.get("/pointer").status_code == 409
    device.screenshot = lambda: (_ for _ in ()).throw(ValueError("capture refused"))
    assert c.get("/screenshot?window=0x1a").status_code == 409
    device.screenshot = lambda: (_ for _ in ()).throw(OSError("secret detail"))
    r = c.get("/screenshot?window=0x1a")
    assert r.status_code == 500 and "secret detail" not in r.get_data(as_text=True)
    device.screenshot = lambda: _png()
    assert c.get("/screenshot?window=0x1a").status_code == 200
    for error, status in ((RuntimeError("model failed"), 502), (OSError("secret model"), 500)):
        model_app = make_app(device_factory=lambda _: device, window_lister=lambda: WINDOWS,
                             locator=lambda *_: (_ for _ in ()).throw(error))
        model_app.logger.disabled = True
        r = model_app.test_client().post("/locate", json={"window": "0x1a", "instruction": "x"})
        assert r.status_code == status and r.is_json and {"error", "description"} <= r.get_json().keys()
        if status == 500:
            assert "secret model" not in r.get_data(as_text=True)
    print("PASS: errors remain JSON, classify failures, and hide unexpected exception details")


def test_health_and_windows():
    app, _ = build()
    c = app.test_client()
    r = c.get("/health")
    assert r.status_code == 200 and r.get_json() == {"ok": True}
    r = c.get("/windows")
    got = r.get_json()["windows"]
    assert r.status_code == 200 and len(got) == 2
    assert got[0]["id"] == "0x1a" and got[0]["foreground"] is True
    assert got[1]["foreground"] is False
    # screen rect minus the frame origin: this is the space a click is measured in
    assert got[0]["image_rect"] == [100, 50, 2020, 1090], got[0]["image_rect"]
    assert got[0]["frame"] == {"origin": [-100, -50], "size": [1920, 1080]}
    print("PASS: /health and /windows answer from the injected lister, with frame-space rects")


def test_screenshot():
    app, device = build()
    c = app.test_client()
    r = c.get("/screenshot?window=0x1a")
    assert r.status_code == 200
    assert r.mimetype == "image/png"
    assert r.data == device.png
    r = c.get("/screenshot")
    assert r.status_code == 400            # no window named
    print("PASS: /screenshot returns the body's bytes, and 400 without a window")


def test_downscaleshot():
    app, _ = build()
    c = app.test_client()
    r = c.get("/downscaleshot?window=0x1a&scale=0.5")
    assert r.status_code == 200
    assert Image.open(io.BytesIO(r.data)).size == (50, 50)
    assert r.headers["X-Bryes-Scale"] == "0.5"
    assert r.headers["X-Bryes-Origin"] == "0,0"
    assert r.headers["X-Bryes-Frame"] == "100,100"
    # the default is the factor the Eyes themselves use for an overview
    assert Image.open(io.BytesIO(c.get("/downscaleshot?window=0x1a").data)).size == (50, 50)
    assert c.get("/downscaleshot?window=0x1a&scale=5").status_code == 400
    assert c.get("/downscaleshot?window=0x1a&scale=wide").status_code == 400
    print("PASS: /downscaleshot halves by default and reports how to map back")


def test_upscaleshot():
    app, _ = build()
    c = app.test_client()
    r = c.get("/upscaleshot?window=0x1a&x1=10&y1=20&x2=40&y2=60&scale=2")
    assert r.status_code == 200
    assert Image.open(io.BytesIO(r.data)).size == (60, 80)      # 30x40 crop, doubled
    assert r.headers["X-Bryes-Scale"] == "2"
    assert r.headers["X-Bryes-Origin"] == "10,20"               # crop offset travels with it
    assert c.get("/upscaleshot?window=0x1a&x1=10&y1=20").status_code == 400
    assert c.get("/upscaleshot?window=0x1a&x1=10&y1=20&x2=200&y2=60").status_code == 400
    print("PASS: /upscaleshot crops, enlarges, and carries the crop origin")


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


def test_act_batch():
    app, device = build()
    actions = [{"type": "click", "x": 20, "y": 10},
               {"type": "type", "text": "abc"}, {"type": "key", "key": "enter"}]
    r = app.test_client().post("/act", json={"window": "0x1a", "actions": actions})
    assert r.status_code == 200 and r.get_json() == {"ok": True, "actions": actions}
    assert device.actions == actions
    print("PASS: batch actions run in order with the documented text and key fields")


def test_act_batch_validates_before_input():
    invalid = [None, [], {}, [None], [{"type": []}],
               [{"type": "click"}], [{"type": "type", "string": "abc"}],
               [{"type": "key", "key": ""}],
               [{"type": "click", "x": "20", "y": 10}],
               [{"type": "drag", "x": 1, "y": 2, "x2": 3}],
               [{"type": "key_hold", "key": "w"}],
               [{"type": "type", "text": "abc", "window": "0x2b"}]]
    for items in invalid:
        app, device = build()
        if isinstance(items, list) and items:
            items = [{"type": "type", "text": "must not run"}] + items
        r = app.test_client().post("/act", json={"window": "0x1a", "actions": items})
        assert r.status_code == 400, (items, r.get_json())
        assert not device.actions
    app, device = build()
    c = app.test_client()
    for body in ([], None, "abc", {"window": "0x1a", "type": "type", "actions": []},
                 {"actions": [{"type": "type", "text": "abc"}]}):
        r = c.post("/act", data=json.dumps(body), content_type="application/json")
        assert r.status_code == 400
    assert not device.actions
    print("PASS: malformed batches and later invalid actions send no input")


def test_act_batch_stops_on_failure():
    for failed_index in (0, 1, 2):
        app, device = build()
        actions = [{"type": "click", "x": 10, "y": 10} for _ in range(3)]
        actions[failed_index] = {"type": "click", "x": -1, "y": 0}
        r = app.test_client().post("/act", json={"window": "0x1a", "actions": actions})
        body = r.get_json()
        assert r.status_code == 409 and body["ok"] is False
        assert body["failed_index"] == failed_index
        assert body["failed_action"] == actions[failed_index]
        assert body["completed"] == device.actions == actions[:failed_index]
    # Even an unexpected device exception must retain progress and stop the batch.
    app, device = build()
    original = device.act

    def fail_on_key(action):
        if action["type"] == "key":
            raise OSError("input backend unavailable")
        original(action)

    device.act = fail_on_key
    actions = [{"type": "type", "text": "abc"}, {"type": "key", "key": "enter"},
               {"type": "type", "text": "must not run"}]
    r = app.test_client().post("/act", json={"window": "0x1a", "actions": actions})
    assert r.status_code == 500 and r.get_json()["completed"] == actions[:1]
    assert device.actions == actions[:1]
    print("PASS: first, middle, last and unexpected failures stop with accurate progress")


def test_act_batch_lock():
    app, device = build()
    original_act = device.act
    original_lock = _bridge._LOCK

    class RecordingLock:
        held = False
        entries = 0

        def __enter__(self):
            assert not self.held
            self.held = True
            self.entries += 1

        def __exit__(self, *_args):
            self.held = False

    lock = RecordingLock()

    def check_lock(action):
        assert lock.held
        original_act(action)

    device.act = check_lock
    _bridge._LOCK = lock
    try:
        r = app.test_client().post("/act", json={"window": "0x1a", "actions": [
            {"type": "type", "text": "a"}, {"type": "type", "text": "b"}]})
        assert r.status_code == 200 and len(device.actions) == 2
        assert lock.entries == 1 and not lock.held
    finally:
        _bridge._LOCK = original_lock
    print("PASS: one lock acquisition covers the whole batch and is released afterwards")


def test_pointer():
    app, device = build()
    c = app.test_client()
    r = c.get("/pointer")
    assert r.status_code == 200 and r.get_json() == {"x": 960, "y": 540}
    assert c.get("/pointer?window=invalid").status_code == 400
    r = c.get("/pointer?window=0x1a")
    body = r.get_json()
    assert r.status_code == 200, body
    # frame origin is (-100,-50) in this fixture, so image space shifts by that
    assert body["x"] == 960 and body["y"] == 540
    assert body["image_x"] == 1060 and body["image_y"] == 590
    assert body["inside_frame"] is True
    assert body["inside_window"] is True
    device.pos = (-900, -900)                    # parked on another display
    assert c.get("/pointer").get_json() == {"x": -900, "y": -900}
    body = c.get("/pointer?window=0x1a").get_json()
    assert body["inside_frame"] is False and body["inside_window"] is False
    device.pos = None
    assert c.get("/pointer").status_code == 503
    print("PASS: /pointer reports global position and optional window-relative details")


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
    test_target_resolver()
    test_target_routes()
    test_focused_capture()
    test_focus_capture_lock()
    test_error_contract()
    test_health_and_windows()
    test_screenshot()
    test_downscaleshot()
    test_upscaleshot()
    test_act_forwards_and_refuses()
    test_act_batch()
    test_act_batch_validates_before_input()
    test_act_batch_stops_on_failure()
    test_act_batch_lock()
    test_locate()
    test_pointer()
    test_profiles()
    print("PASS: all bridge tests green")
