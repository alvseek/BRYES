"""BRYES Phase 4 — Close the Loop.

Chains the four pieces into one autonomous cycle:

    screenshot -> Eyes.describe -> Brain.decide -> Eyes.locate -> Hands act -> repeat
                                                        until "done"/"fail"/step-limit

No verify-and-recover yet — that's Phase 5. The goal here is one clean success on the
ONE task; note *how* it fails on retries, that's the input to Phase 5.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from eyes.client import describe, locate  # noqa: E402
from brain.client import decide  # noqa: E402

SCREEN = "http://localhost:8000"


def _open(req, retries=4):
    """urlopen with a few retries — the Screen's dev server can drop a cold connection."""
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(req, timeout=15).read()
        except (urllib.error.URLError, ConnectionError) as e:
            if attempt == retries - 1:
                raise
            time.sleep(0.5 * (attempt + 1))


def screenshot():
    return _open(SCREEN + "/screenshot")


def hands(payload):
    req = urllib.request.Request(
        SCREEN + "/action", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    return _open(req)


def run(goal, max_steps=12, settle=0.6, verbose=True):
    """Drive the loop until the Brain says done/fail or steps run out."""
    def log(*a):
        if verbose:
            print(*a)

    log(f"GOAL: {goal}\n")
    history = []
    for step in range(1, max_steps + 1):
        shot = screenshot()
        observation = describe(shot)              # Eyes: what's available
        action = decide(goal, observation, history)  # Brain: decide from it
        action.pop("_usage", None)
        act = action.get("action")
        thought = action.get("thought", "")

        log(f"[step {step}] eyes: {observation[:100].strip()}...")
        detail = action.get("target") or action.get("text") or action.get("key") or ""
        log(f"         brain: {thought}")
        log(f"         -> {act} {detail}".rstrip())

        if act == "done":
            log("\n[OK] Brain reports the goal is complete.")
            return {"status": "done", "steps": step, "history": history}
        if act == "fail":
            log(f"\n[FAIL] Brain gave up: {thought}")
            return {"status": "fail", "steps": step, "history": history}

        if act == "click":
            target = action.get("target", "")
            loc = locate(shot, target)                       # Eyes: where
            hands({"type": "click", "x": loc["x"], "y": loc["y"]})  # Hands: do
            history.append(f"clicked '{target}' at ({loc['x']},{loc['y']})")
        elif act == "type":
            target = action.get("target")
            if target:
                loc = locate(shot, target)
                hands({"type": "click", "x": loc["x"], "y": loc["y"]})
            text = action.get("text", "")
            hands({"type": "type", "text": text})
            history.append(f"typed '{text}'" + (f" into '{target}'" if target else ""))
        elif act == "key":
            k = action.get("key", "")
            hands({"type": "key", "key": k})
            history.append(f"pressed key '{k}'")
        else:
            history.append(f"unknown action skipped: {action}")

        log("")
        time.sleep(settle)

    log("\n[STOP] step limit reached without a done/fail.")
    return {"status": "step_limit", "steps": max_steps, "history": history}
