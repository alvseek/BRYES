"""BRYES ADR-007 — model-free loop test: the CONFIRMED FINDINGS ledger (append-only) +
channel-aware CURRENT CONDITION + note-in-history + the Phase-3 Eyes-skip on non-visual actions.
Stubs describe/decide + a fake device, so it runs with NO model and NO container (mirrors
test_run_selection's injection style)."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import loop as L  # noqa: E402

_CAPS = SimpleNamespace(name="fake", width=1280, height=800, has_shell=True,
                        shell_flavor="bash", keys={"Return", "ctrl+a"},
                        verbs=frozenset({"click", "type", "key"}))


class _FakeDevice:
    def __init__(self):
        self.caps = _CAPS

    def screenshot(self):
        return b"fakepng"

    def act(self, a):
        pass

    def shell(self, cmd, timeout=None, stdin=None):
        return {"ok": True, "exit_code": 0, "stdout": "MX3 avg = 1726270",
                "stderr": "", "timed_out": False}

    def type_into(self, text, click_xy=None, clear_first=False, press_enter=False):
        pass


def _run(script, describe_text="canned screen"):
    """Drive the loop with a scripted Brain. Returns (decide_call_kwargs_per_step,
    describe_call_count, result). `findings` is snapshotted (the loop mutates it in place)."""
    calls = []
    describe_count = [0]

    def fake_decide(goal, observation=None, history=None, **kw):
        snap = dict(kw)
        snap["findings"] = list(kw.get("findings") or [])
        calls.append(snap)
        return dict(script[len(calls) - 1])

    def fake_describe(shot, visual_focus=None, visual_expectation=None, careful=False, context=None):
        describe_count[0] += 1
        return describe_text

    L.decide = fake_decide
    L.describe = fake_describe
    res = L.run("goal", device=_FakeDevice(), verbose=False, tag="test-adr007", settle=0)
    return calls, describe_count[0], res


def main():
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS: " if cond else "FAIL: ") + label)
        ok = ok and bool(cond)
        return cond

    # Run A: a visual action that banks a fact, a shell action that banks another, then done.
    calls, describes, res = _run([
        {"thought": "t", "action": "type_into", "text": "hello",
         "note": "typing hello", "findings": "fact A read"},
        {"thought": "t", "action": "shell", "command": "echo hi",
         "note": "computing", "findings": "fact B computed"},
        {"thought": "t", "action": "done", "note": "all set"},
    ])
    check("run reached done", res.get("status") == "done")
    # 1. append-only ledger threads forward
    check("decide#2 ledger carries the step-1 finding",
          any("fact A read" in f for f in calls[1]["findings"]))
    check("decide#3 ledger carries BOTH banked findings",
          any("fact A" in f for f in calls[2]["findings"])
          and any("fact B" in f for f in calls[2]["findings"]))
    check("step-1 decide saw an EMPTY ledger", calls[0]["findings"] == [])
    # 2. note reaches history (did - note)
    check("history carries the note", any("typing hello" in h for h in res["history"]))
    # 3. channel-aware CURRENT CONDITION
    check("decide#2 visual_unchanged=False after a visual action",
          calls[1]["visual_unchanged"] is False)
    check("decide#2 last_result points at the screen",
          "Current screen" in (calls[1]["last_result"] or ""))
    check("decide#3 visual_unchanged=True after a shell action",
          calls[2]["visual_unchanged"] is True)
    check("decide#3 last_action shows the shell command",
          "shell" in (calls[2]["last_action"] or ""))
    # L1: the shell exec OUTPUT is carried on the 'What resulted' line (not just the action line)
    check("decide#3 last_result carries the shell exec output (L1)",
          "MX3 avg" in (calls[2]["last_result"] or ""))
    # 4. Phase-3 Eyes-skip: describe runs at step 1 (init) + step 2 (after visual), NOT step 3
    #    (after shell) -> 2 describes for a 3-step run.
    check("Eyes skipped after the shell step (2 describes for 3 steps)", describes == 2)

    # Run B: shell then done -> describe only at step 1 (step 2 skips after shell).
    _, describes_b, _ = _run([
        {"thought": "t", "action": "shell", "command": "echo hi"},
        {"thought": "t", "action": "done"},
    ])
    check("shell->done: 1 describe (step-2 skipped)", describes_b == 1)

    # Run C: wait then done -> `wait` CHANGES the screen, so it does NOT skip (2 describes).
    _, describes_c, _ = _run([
        {"thought": "t", "action": "wait", "seconds": 0.5},
        {"thought": "t", "action": "done"},
    ])
    check("wait->done: 2 describes (wait is screen-changing, not skipped)", describes_c == 2)

    # Run D (L2): a describe carrying a "VERIFICATION:" prefix; after visual->shell the REUSED
    # observation must have the stale prefix stripped (only the description remains).
    calls_d, _, _ = _run(
        [{"thought": "t", "action": "type_into", "text": "x"},
         {"thought": "t", "action": "shell", "command": "echo hi"},
         {"thought": "t", "action": "done"}],
        describe_text="VERIFICATION: the box shows X\n\nA text field is focused.")
    check("decide#2 (fresh) keeps the VERIFICATION prefix",
          (calls_d[1]["current_visual"] or "").startswith("VERIFICATION:"))
    check("decide#3 (reused after shell) has VERIFICATION stripped (L2)",
          not (calls_d[2]["current_visual"] or "").startswith("VERIFICATION:")
          and "A text field is focused." in (calls_d[2]["current_visual"] or ""))

    print("\n" + ("ALL PASS" if ok else "SOME FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
