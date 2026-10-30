"""Model-free tests for the Bridge client (api/bridge_client.py). No server, no screen.

    python api/test_bridge_client.py

What is tested is the arithmetic and the payload shapes the client owns: the frame mapping read
from the image headers, the crop-to-frame conversion, the /act payload per verb, window picking
and the raise point. The HTTP calls themselves are thin and are exercised against a live Bridge.
"""
import sys
import json
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bridge_client as bc  # noqa: E402


def test_mapping_from_headers():
    m = bc.mapping_from_headers({"X-Bryes-Scale": "2", "X-Bryes-Origin": "1500,700", "X-Bryes-Frame": "3440,1440"})
    assert m == {"scale": 2.0, "origin": [1500, 700], "frame": [3440, 1440]}
    # a plain 1:1 screenshot carries no mapping headers
    assert bc.mapping_from_headers({}) == {"scale": 1.0, "origin": [0, 0], "frame": [None, None]}
    print("PASS: mapping is read from the X-Bryes headers, 1:1 when absent")


def test_to_frame():
    # the README's own example: crop at (100,200) enlarged by 2, pixel (40,60) -> frame (120,230)
    assert bc.to_frame({"scale": 2.0, "origin": [100, 200]}, 40, 60) == (120, 230)
    # a downscaled overview at 0.5 doubles back
    assert bc.to_frame({"scale": 0.5, "origin": [0, 0]}, 850, 450) == (1700, 900)
    # fractional results round to whole pixels
    assert bc.to_frame({"scale": 3.0, "origin": [780, 380]}, 388, 160) == (909, 433)
    print("PASS: crop pixels map to frame pixels as origin + px / scale")


def test_build_action():
    assert bc.build_action("0x1", "click", (10, 20)) == {"window": "0x1", "type": "click", "x": 10, "y": 20}
    m = {"scale": 2.0, "origin": [100, 200]}
    assert bc.build_action("0x1", "drag", (40, 60, 80, 100), mapping=m) == {
        "window": "0x1", "type": "drag", "x": 120, "y": 230, "x2": 140, "y2": 250}
    assert bc.build_action("0x1", "scroll", (5, 5), direction="up")["direction"] == "up"
    assert bc.build_action("0x1", "scroll", (5, 5))["direction"] == "down"
    assert bc.build_action("0x1", "key", key="ctrl+a") == {"window": "0x1", "type": "key", "key": "ctrl+a"}
    assert bc.build_action("0x1", "key_hold", key="w", seconds=1.5) == {
        "window": "0x1", "type": "key_hold", "key": "w", "seconds": 1.5}
    assert "seconds" not in bc.build_action("0x1", "key_hold", key="w")
    assert bc.build_action("0x1", "type", text="Event BeginPlay")["text"] == "Event BeginPlay"
    for bad in (lambda: bc.build_action("0x1", "click", (1,)),
                lambda: bc.build_action("0x1", "drag", (1, 2)),
                lambda: bc.build_action("0x1", "key"),
                lambda: bc.build_action("0x1", "key", key="w", seconds=1),
                lambda: bc.build_action("0x1", "type")):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("a malformed action was accepted")
    print("PASS: /act payloads per verb, converted through a mapping, malformed ones refused")


def test_client_commands():
    calls = []

    class FakeClient:
        def __init__(self, out=None):
            pass

        def locate(self, window, instruction):
            calls.append(("locate", window, instruction))
            return {"x": 10, "y": 20}

        def profiles(self, path):
            calls.append(("profiles", path))
            return {"visual": "example", "operating": "example"}

        def act(self, payload):
            calls.append(("act", payload))
            return {"ok": True}

    original_client, original_sleep = bc.BridgeClient, bc.time.sleep
    try:
        bc.BridgeClient, bc.time.sleep = FakeClient, lambda _: None
        assert bc.main(["--window", "0x1", "locate", "the Submit button"]) == 0
        assert bc.main(["profiles", "windows/unreal-editor"]) == 0
        assert bc.main(["--window", "0x1", "act", "key_hold", "--key", "w", "--seconds", "1.5"]) == 0
    finally:
        bc.BridgeClient, bc.time.sleep = original_client, original_sleep
    assert calls == [("locate", "0x1", "the Submit button"),
                     ("profiles", "windows/unreal-editor"),
                     ("act", {"window": "0x1", "type": "key_hold", "key": "w", "seconds": 1.5})]

    class Response(io.BytesIO):
        pass

    client = bc.BridgeClient(base="http://example.test")
    requests = []

    def fake_open(req):
        requests.append(req)
        return Response(b'{"ok": true}')

    client._open = fake_open
    assert client.locate("0x1", "a button") == {"ok": True}
    assert json.loads(requests[0].data) == {"window": "0x1", "instruction": "a button"}
    assert requests[0].full_url == "http://example.test/locate"
    assert client.profiles("windows/a b") == {"ok": True}
    assert requests[1] == "http://example.test/profiles?path=windows%2Fa+b"
    print("PASS: locate, profiles, and key_hold duration CLI and HTTP requests")


def test_pick_window():
    wins = [{"id": "0x1", "title": "LSGI - Unreal Editor"}, {"id": "0x2", "title": "Notepad"},
            {"id": "0x3", "title": "BPA_Test - Unreal Editor"}]
    assert bc.pick_window(wins, "notepad") == "0x2"
    for title in ("Unreal Editor", "nothing"):
        try:
            bc.pick_window(wins, title)
        except bc.BridgeError:
            continue
        raise AssertionError(f"'{title}' should not resolve to one window")
    print("PASS: --title resolves exactly one window and refuses none or several")


def test_raise_point():
    entry = {"image_rect": [0, 0, 3440, 1400]}
    # pointer already inside: hover where it is, so nothing moves
    assert bc.raise_point(entry, {"inside_window": True, "image_x": 50, "image_y": 60}) == (50, 60)
    # pointer elsewhere: the window's centre
    assert bc.raise_point(entry, {"inside_window": False, "image_x": -900, "image_y": -900}) == (1720, 700)
    print("PASS: raising hovers in place when the pointer is inside, else at the window centre")


def test_mapping_sidecar_round_trip(tmp=Path(__file__).resolve().parent.parent / "artifacts" / "bridge-client-test"):
    client = bc.BridgeClient(out=tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "k1.json").write_text('{"scale": 3.0, "origin": [780, 380], "frame": [3440, 1440]}', encoding="utf-8")
    assert bc.to_frame(client.load_mapping("k1"), 388, 160) == (909, 433)
    try:
        client.load_mapping("missing")
    except bc.BridgeError:
        print("PASS: --from reads a saved shot's mapping and names a missing one")
        return
    raise AssertionError("a missing mapping was not reported")


if __name__ == "__main__":
    test_mapping_from_headers()
    test_to_frame()
    test_build_action()
    test_client_commands()
    test_pick_window()
    test_raise_point()
    test_mapping_sidecar_round_trip()
    print("PASS: all bridge client tests green")
