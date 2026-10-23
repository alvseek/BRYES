"""BRYES — model-free payload tests for the container server's /action endpoint.

Proving that a held key STAYS held needs a live X display, which is screen/test_hands.py
and needs Docker. This file proves the half that needs neither: a bad `key_hold` payload is
refused, and a good one builds exactly one down/wait/up xdotool chain. The subprocess is
replaced, so nothing is executed and no display is needed.

Run:  python screen/test_action_payloads.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

_spec = importlib.util.spec_from_file_location(
    "screen_app", os.path.join(HERE, "server", "app.py"))
app_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(app_mod)


class _FakeRun:
    """Stands in for subprocess.run: records each command, reports success."""

    def __init__(self):
        self.cmds = []

    def __call__(self, cmd, *args, **kwargs):
        self.cmds.append(list(cmd))

        class _Done:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Done()


def main():
    ok = True

    def check(label, cond, note=""):
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + label + (f"  ({note})" if not cond else ""))
        ok = ok and bool(cond)
        return cond

    client = app_mod.app.test_client()

    # 1. A payload that cannot be honoured is refused loudly, not silently clamped.
    for payload, why in (
        ({"type": "key_hold"}, "no key"),
        ({"type": "key_hold", "key": "w", "seconds": 99}, "span above the ceiling"),
        ({"type": "key_hold", "key": "w", "seconds": 0}, "span below the floor"),
        ({"type": "key_hold", "key": "w", "seconds": "abc"}, "span not a number"),
    ):
        res = client.post("/action", json=payload)
        check(f"refused: {why}", res.status_code == 400, f"got {res.status_code}")

    # 2. A good hold builds ONE chain: down, wait the span, up. The tap stays a tap.
    fake = _FakeRun()
    real = app_mod._run
    app_mod._run = fake
    try:
        res = client.post("/action", json={"type": "key_hold", "key": "w", "seconds": 0.6})
        check("a hold returns ok", res.status_code == 200, f"got {res.status_code}")
        check("the hold is one down/sleep/up chain",
              fake.cmds == [["xdotool", "keydown", "w", "sleep", "0.60", "keyup", "w"]],
              str(fake.cmds))

        client.post("/action", json={"type": "key_hold", "key": "Up"})
        check("an absent span defaults to 1.00 s",
              fake.cmds[-1] == ["xdotool", "keydown", "Up", "sleep", "1.00", "keyup", "Up"],
              str(fake.cmds[-1]))

        client.post("/action", json={"type": "key", "key": "Return"})
        check("a plain key is still one tap",
              fake.cmds[-1] == ["xdotool", "key", "Return"], str(fake.cmds[-1]))
    finally:
        app_mod._run = real

    # 3. The container CLIENT sends what the server documents: a bounded span, and a key
    #    rewritten to the keysym the server expects. The transport is replaced, so this
    #    needs no display and no Docker.
    from devices import ContainerDevice

    device = ContainerDevice(base_url="http://fake")
    sent = []

    def _fake_open(req, retries=4):
        sent.append(json.loads(req.data.decode()))
        return b"{}"

    device._open = _fake_open
    device.act({"type": "key_hold", "key": "Enter", "seconds": 99})
    check("the client clamps an over-long span to 5.0 s",
          bool(sent) and sent[-1].get("seconds") == 5.0, str(sent[-1:]))
    check("the client rewrites the key to the server's keysym",
          bool(sent) and sent[-1].get("key") == "Return", str(sent[-1:]))

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
