"""Model-free tests for the Bridge client (api/bridge_client.py). No server, no screen.

    python api/test_bridge_client.py

What is tested is the arithmetic and the payload shapes the client owns: the frame mapping read
from the image headers, the crop-to-frame conversion, the /act payload per verb, window picking
and the raise point. The HTTP calls themselves are thin and are exercised against a live Bridge.
"""
import sys
import json
import io
import tempfile
import urllib.error
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
    assert calls == [("locate", {"window": "0x1"}, "the Submit button"),
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


def test_server_owned_targeting():
    calls = []

    class FakeClient:
        def __init__(self, out=None):
            pass

        def save_image(self, path, name, body=None):
            calls.append((path, body))
            return name, {"scale": 1, "origin": [0, 0], "frame": [100, 100]}

        def locate(self, selector, instruction):
            calls.append(("locate", selector, instruction))
            return {}

        def act(self, payload):
            calls.append(("act", payload))
            return {}

    original, sleep, old_env = bc.BridgeClient, bc.time.sleep, bc.os.environ.pop("BRIDGE_WINDOW", None)
    try:
        bc.BridgeClient, bc.time.sleep = FakeClient, lambda _: None
        assert bc.main(["--title", "Example App", "shot", "one", "--raise"]) == 0
        assert bc.main(["--title", "Example App", "crop", "two", "1", "2", "3", "4", "--raise"]) == 0
        assert bc.main(["--title", "Example App", "locate", "button"]) == 0
        assert bc.main(["--title", "Example App", "act", "key", "--key", "a"]) == 0
        assert calls[0] == ("/downscaleshot", {"title": "Example App", "scale": "0.5", "raise": True})
        assert calls[1][1] == {"title": "Example App", "x1": 1, "y1": 2, "x2": 3, "y2": 4, "scale": "2", "raise": True}
        assert calls[2] == ("locate", {"title": "Example App"}, "button")
        assert calls[3] == ("act", {"title": "Example App", "type": "key", "key": "a"})
        bc.os.environ["BRIDGE_WINDOW"] = "0x1"
        assert bc.main(["--title", "ignored", "shot", "three", "--raise"]) == 0
        assert calls[-1][1]["window"] == "0x1" and "title" not in calls[-1][1]
    finally:
        bc.BridgeClient, bc.time.sleep = original, sleep
        if old_env is None:
            bc.os.environ.pop("BRIDGE_WINDOW", None)
        else:
            bc.os.environ["BRIDGE_WINDOW"] = old_env
    print("PASS: CLI sends title and focused capture directly to server")


def test_focused_http_request():
    class Response(io.BytesIO):
        headers = {"X-Bryes-Scale": "0.5", "X-Bryes-Origin": "0,0", "X-Bryes-Frame": "100,100"}

    with tempfile.TemporaryDirectory() as directory:
        client = bc.BridgeClient(base="http://example.test", out=directory)
        requests = []
        client._open = lambda req: (requests.append(req), Response(b"png"))[1]
        png, mapping = client.save_image("/downscaleshot", "shot",
                                         {"title": "app", "raise": True, "scale": "0.5"})
        assert requests[0].get_method() == "POST"
        assert requests[0].full_url == "http://example.test/downscaleshot"
        assert json.loads(requests[0].data) == {"title": "app", "raise": True, "scale": "0.5"}
        assert png.read_bytes() == b"png" and mapping["scale"] == 0.5
        assert json.loads((Path(directory) / "shot.json").read_text()) == mapping
    original = bc.urllib.request.urlopen
    try:
        def fail(*_args, **_kwargs):
            raise urllib.error.HTTPError("http://example.test", 409, "conflict", {}, io.BytesIO(b'failure body'))
        bc.urllib.request.urlopen = fail
        try:
            bc.BridgeClient().get_json("/pointer")
            raise AssertionError("HTTP error not surfaced")
        except bc.BridgeError as exc:
            assert "409" in str(exc) and "failure body" in str(exc)
    finally:
        bc.urllib.request.urlopen = original
    print("PASS: focused capture sends JSON POST and preserves image mapping and HTTP errors")


def test_cli_error_exit():
    class FakeClient:
        def __init__(self, out=None):
            pass

        def locate(self, *_args):
            raise bc.BridgeError("HTTP 409: refusal body")

    original, stderr = bc.BridgeClient, sys.stderr
    try:
        bc.BridgeClient = FakeClient
        sys.stderr = io.StringIO()
        assert bc.main(["--window", "0x1", "locate", "button"]) == 1
        assert "HTTP 409: refusal body" in sys.stderr.getvalue()
    finally:
        bc.BridgeClient, sys.stderr = original, stderr
    print("PASS: CLI prints HTTP error and returns failure")


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
    test_server_owned_targeting()
    test_focused_http_request()
    test_cli_error_exit()
    test_mapping_sidecar_round_trip()
    print("PASS: all bridge client tests green")
