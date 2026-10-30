"""Model-free tests for the Bridge client (api/bridge_client.py). No server, no screen.

    python api/test_bridge_client.py

Tests cover image mappings, generic action JSON, target forwarding, HTTP requests and CLI errors.
Server contract checks use Flask's test client with fake dependencies, never a real desktop.
"""
import sys
import json
import io
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

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


def test_build_payload():
    selector = {"window": "0x1"}
    m = {"scale": 2.0, "origin": [100, 200]}
    drag = {"type": "drag", "x": 40, "y": 60, "x2": 80, "y2": 100}
    converted = {"type": "drag", "x": 120, "y": 230, "x2": 140, "y2": 250}
    assert bc.build_payload(selector, drag, m) == {**selector, **converted}
    assert drag["x"] == 40  # caller-owned JSON is not mutated
    delay = {"type": "delay", "miliseconds": 1000}
    future = {"type": "future-server-verb", "new_field": {"keep": True}}
    batch = {"actions": [drag, delay, future]}
    assert bc.build_payload(selector, batch, m) == {
        **selector, "actions": [converted, delay, future]}
    assert batch["actions"][0] == drag
    assert bc.build_payload({"title": "App"}, future) == {"title": "App", **future}
    # The server, not the CLI, validates verbs, required fields and batch semantics.
    for action in ({"type": "key"}, {"actions": []}, future):
        assert bc.build_payload(selector, action) == {**selector, **action}
    for bad in (lambda: bc.build_payload(selector, []),
                lambda: bc.build_payload(selector, {"window": "0x2"}),
                lambda: bc.build_payload(selector, {"title": "Other"}),
                lambda: bc.build_payload(selector, {"actions": None}, m),
                lambda: bc.build_payload(selector, {"actions": [None]}, m),
                lambda: bc.build_payload(selector, {"x": 1}, m),
                lambda: bc.build_payload(selector, {"x": True, "y": 1}, m),
                lambda: bc.build_payload(selector, {"x": "1", "y": 1}, m),
                lambda: bc.build_payload(selector, {"x": float("inf"), "y": 1}, m)):
        try:
            bad()
        except ValueError:
            continue
        raise AssertionError("an invalid local payload or mapping was accepted")
    print("PASS: generic payloads preserve server fields and map single or batch coordinates")


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

    original_client = bc.BridgeClient
    try:
        bc.BridgeClient = FakeClient
        assert bc.main(["--window", "0x1", "locate", "the Submit button"]) == 0
        assert bc.main(["profiles", "windows/unreal-editor"]) == 0
        with patch("time.sleep", side_effect=AssertionError("no automatic client wait")):
            assert bc.main(["--window", "0x1", "act", "--json",
                            '{"type":"key_hold","key":"w","seconds":1.5}']) == 0
    finally:
        bc.BridgeClient = original_client
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

    original, old_env = bc.BridgeClient, bc.os.environ.pop("BRIDGE_WINDOW", None)
    try:
        bc.BridgeClient = FakeClient
        assert bc.main(["--title", "Example App", "shot", "one", "--raise"]) == 0
        assert bc.main(["--title", "Example App", "crop", "two", "1", "2", "3", "4", "--raise"]) == 0
        assert bc.main(["--title", "Example App", "locate", "button"]) == 0
        assert bc.main(["--title", "Example App", "act", "--json",
                        '{"type":"key","key":"a"}']) == 0
        assert calls[0] == ("/downscaleshot", {"title": "Example App", "scale": "0.5", "raise": True})
        assert calls[1][1] == {"title": "Example App", "x1": 1, "y1": 2, "x2": 3, "y2": 4, "scale": "2", "raise": True}
        assert calls[2] == ("locate", {"title": "Example App"}, "button")
        assert calls[3] == ("act", {"title": "Example App", "type": "key", "key": "a"})
        bc.os.environ["BRIDGE_WINDOW"] = "0x1"
        assert bc.main(["--title", "ignored", "shot", "three", "--raise"]) == 0
        assert calls[-1][1]["window"] == "0x1" and "title" not in calls[-1][1]
    finally:
        bc.BridgeClient = original
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


def test_settle_option_removed():
    with patch("sys.stderr", new_callable=io.StringIO) as stderr:
        try:
            bc.main(["--window", "0x1", "act", "--json",
                     '{"type":"key","key":"enter"}', "--settle", "1"])
        except SystemExit as exc:
            assert exc.code == 2
        else:
            raise AssertionError("removed --settle option was accepted")
        assert "unrecognized arguments: --settle" in stderr.getvalue()
    print("PASS: removed --settle option is rejected rather than silently ignored")


def test_json_action_requests():
    from test_bridge import build

    app, device = build()
    requests, waits = [], []
    with tempfile.TemporaryDirectory() as directory:
        client = bc.BridgeClient(base="http://example.test", out=directory)
        (Path(directory) / "pins.json").write_text(
            '{"scale":2,"origin":[100,200]}', encoding="utf-8", newline="\n")

        def open_request(req):
            requests.append(req)
            assert req.get_method() == "POST" and req.full_url == "http://example.test/act"
            assert req.get_header("Content-type") == "application/json"
            r = app.test_client().post("/act", data=req.data, content_type="application/json")
            if r.status_code != 200:
                raise bc.BridgeError(f"HTTP {r.status_code}: {r.get_data(as_text=True)}")
            return io.BytesIO(r.data)

        client._open = open_request
        with patch.object(bc, "BridgeClient", return_value=client), patch("time.sleep", waits.append):
            single = {"type": "key", "key": "enter"}
            assert bc.main(["--window", "0x1a", "act", "--json", json.dumps(single)]) == 0
            assert json.loads(requests[-1].data) == {"window": "0x1a", **single}
            actions = [{"type": "click", "x": 40, "y": 60},
                       {"type": "delay", "miliseconds": 1000},
                       {"type": "drag", "x": 40, "y": 60, "x2": 80, "y2": 100}]
            assert bc.main(["--window", "0x1a", "act", "--from", "pins", "--json",
                            json.dumps({"actions": actions})]) == 0
            expected = [{"type": "click", "x": 120, "y": 230}, actions[1],
                        {"type": "drag", "x": 120, "y": 230, "x2": 140, "y2": 250}]
            assert json.loads(requests[-1].data) == {"window": "0x1a", "actions": expected}
            assert device.actions == [single, expected[0], expected[2]] and waits == [1.0]
            assert bc.main(["--window", "0x1a", "act", "--json",
                            '{"type":"delay","miliseconds":0}']) == 0
            assert waits == [1.0, 0]
            # Semantic errors still reach the server and are printed with a failing exit.
            before = len(device.actions)
            with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                assert bc.main(["--window", "0x1a", "act", "--json",
                                '{"actions":[{"type":"key","key":"a"},{"type":"unknown"}]}']) == 1
                assert "HTTP 400" in stderr.getvalue()
            assert len(device.actions) == before
            before = len(requests)
            for value in ("{", "[]", '{"window":"0x2","type":"key"}'):
                with patch("sys.stderr", new_callable=io.StringIO):
                    assert bc.main(["--window", "0x1a", "act", "--json", value]) == 1
            assert len(requests) == before
            for legacy in (["key", "--key", "enter"], ["--json", "{}", "--seconds", "1"]):
                with patch("sys.stderr", new_callable=io.StringIO):
                    try:
                        bc.main(["--window", "0x1a", "act", *legacy])
                    except SystemExit as exc:
                        assert exc.code == 2
                    else:
                        raise AssertionError("legacy action syntax accepted")
    print("PASS: JSON CLI sends single, delay and mapped batch requests through the server contract")


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
    test_build_payload()
    test_client_commands()
    test_server_owned_targeting()
    test_focused_http_request()
    test_cli_error_exit()
    test_settle_option_removed()
    test_json_action_requests()
    test_mapping_sidecar_round_trip()
    print("PASS: all bridge client tests green")
