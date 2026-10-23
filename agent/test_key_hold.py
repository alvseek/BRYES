"""BRYES — model-free loop test for the held-key action (`key_hold`).

Stubs describe/decide and uses a fake device, so it runs with NO model and NO container
(same injection style as test_condition_ledger.py). What it proves is the loop's half of
the feature: the span is clamped before it reaches a body, the hold reaches the body as
one action, and a body that cannot hold gets a skip instead of a failed call.

Run:  python agent/test_key_hold.py
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import loop as L  # noqa: E402


def _caps(name, verbs):
    return SimpleNamespace(name=name, width=1280, height=800, has_shell=True,
                           shell_flavor="bash", keys={"Return", "ctrl+a"},
                           verbs=frozenset(verbs))


class _FakeDevice:
    """Records every action the loop sends. `verbs` decides whether it can hold."""

    def __init__(self, verbs=("click", "type", "key", "key_hold")):
        self.caps = _caps("fake", verbs)
        self.actions = []

    def screenshot(self):
        return b"fakepng"

    def act(self, action):
        self.actions.append(dict(action))

    def shell(self, cmd, timeout=None, stdin=None):
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": "", "timed_out": False}

    def type_into(self, text, click_xy=None, clear_first=False, press_enter=False):
        pass


def _run(script, device=None):
    """Drive the loop with a scripted Brain. Returns (sent actions, history, result)."""
    device = device or _FakeDevice()
    calls = []

    def fake_decide(goal, observation=None, history=None, **kw):
        calls.append(goal)
        return dict(script[len(calls) - 1])

    def fake_describe(shot, visual_focus=None, visual_expectation=None, careful=False,
                      context=None):
        return "canned screen"

    real_decide, real_describe = L.decide, L.describe
    L.decide, L.describe = fake_decide, fake_describe
    try:
        res = L.run("goal", device=device, verbose=False, tag="test-keyhold", settle=0)
    finally:
        L.decide, L.describe = real_decide, real_describe
    return device.actions, res.get("history", []), res


def main():
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and bool(cond)
        return cond

    # 1. A plain hold reaches the body as ONE action carrying its span.
    actions, history, res = _run([
        {"thought": "t", "action": "key_hold", "key": "w", "seconds": 2.0},
        {"thought": "t", "action": "done"},
    ])
    holds = [a for a in actions if a.get("type") == "key_hold"]
    check("run reached done", res.get("status") == "done")
    check("the hold reached the body once",
          len(holds) == 1 and holds[0] == {"type": "key_hold", "key": "w", "seconds": 2.0})
    check("history names the key and the span",
          any("held key 'w' for 2s" in h for h in history))

    # 2. The span is clamped before it leaves the loop.
    actions, _, _ = _run([
        {"thought": "t", "action": "key_hold", "key": "w", "seconds": 99},
        {"thought": "t", "action": "done"},
    ])
    clamped = [a for a in actions if a.get("type") == "key_hold"]
    check("an over-long span clamps to 5.0 s",
          clamped and clamped[0]["seconds"] == 5.0)

    # 3. An absent span takes the default rather than reaching a body as None.
    actions, history, _ = _run([
        {"thought": "t", "action": "key_hold", "key": "w"},
        {"thought": "t", "action": "done"},
    ])
    defaulted = [a for a in actions if a.get("type") == "key_hold"]
    check("an absent span defaults to 1.0 s",
          defaulted and defaulted[0]["seconds"] == 1.0)
    check("the default is stated in history",
          any("held key 'w' for 1s" in h for h in history))

    # 4. A body without the verb is skipped, not sent, and the run continues.
    phone = _FakeDevice(verbs=("click", "type", "key"))
    actions, history, res = _run([
        {"thought": "t", "action": "key_hold", "key": "w", "seconds": 1.0},
        {"thought": "t", "action": "done"},
    ], device=phone)
    check("a body without key_hold receives no hold",
          not [a for a in actions if a.get("type") == "key_hold"])
    check("the skip is recorded in history and the run still finishes",
          any("skipped 'key_hold'" in h for h in history) and res.get("status") == "done")

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
