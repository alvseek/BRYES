"""BRYES Phase 4 — Close the Loop (+ first Phase-5 cut).

Chains the four pieces into one autonomous cycle:

    screenshot -> Eyes.describe(focus) -> Brain.decide -> Eyes.locate -> Hands act -> repeat
                                                        until "done"/"fail"/step-limit

Phase-5 seeds now in the loop:
  - HISTORY carries BOTH what the Eyes saw and the action taken each step, so the Brain
    can detect "my last action changed nothing" and stop repeating it (no-progress).
  - The Brain steers the Eyes via a `focus` field, carried into the next describe() so
    the description stays on the task-relevant area.
Still missing (later Phase-5 work): an explicit post-action re-check/recover step.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runlog  # noqa: E402
from eyes.client import describe, locate, DESCRIBE_PROMPT, GROUND_PROMPT  # noqa: E402
from brain.client import decide, SYSTEM_PROMPT  # noqa: E402

SCREEN = "http://localhost:8000"

# Point-and-do actions handled identically: locate the named target, act at that pixel.
# (scroll and drag are handled separately — they need a direction / a second point.)
_POINT_VERB = {
    "click": "clicked",
    "double_click": "double-clicked",
    "right_click": "right-clicked",
    "hover": "hovered",
}


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
    res = _open(req)
    runlog.record("action", payload, "executed")
    return res


def exec_cmd(payload):
    """POST a shell command to /exec (Tier-2 effector); return the parsed result
    {ok, exit_code, stdout, stderr, timed_out?}."""
    req = urllib.request.Request(
        SCREEN + "/exec", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    res = json.loads(_open(req))
    runlog.record("exec", payload, res)
    return res


def run(goal, max_steps=12, settle=0.6, verbose=True, tag="run", brain_model=None):
    """Drive the loop until the Brain says done/fail or steps run out.

    Every step's prompts and raw replies (describe / decide / locate / action) plus the
    screenshot are preserved to a transcript under artifacts/runs/ (see runlog); `tag`
    names that run folder.
    """
    def log(*a):
        if verbose:
            print(*a)

    log(f"GOAL: {goal}\n")
    static = {"eyes.DESCRIBE_PROMPT": DESCRIBE_PROMPT,
              "eyes.GROUND_PROMPT": GROUND_PROMPT,
              "brain.SYSTEM_PROMPT": SYSTEM_PROMPT}
    rundir = runlog.start(goal, static=static, tag=tag)
    log(f"(transcript -> {rundir})\n")
    history = []
    focus = None
    captures = 0
    try:
        for step in range(1, max_steps + 1):
            runlog.set_step(step)
            shot = screenshot()
            runlog.save_image(f"step-{step:02d}.png", shot)
            observation = describe(shot, focus=focus)     # Eyes: what's on screen (focused)
            action = decide(goal, observation, history, model=brain_model)  # Brain decides
            action.pop("_usage", None)
            act = action.get("action")
            thought = action.get("thought", "")
            focus = action.get("focus") or focus          # Brain steers the Eyes next step

            log(f"[step {step}] eyes: {observation[:100].strip()}...")
            detail = (action.get("target") or action.get("text") or action.get("key")
                      or action.get("command") or "")
            log(f"         brain: {thought}")
            log(f"         -> {act} {detail}".rstrip())
            if focus:
                log(f"         focus: {focus}")

            if act == "done":
                log("\n[OK] Brain reports the goal is complete.")
                return {"status": "done", "steps": step, "history": history}
            if act == "fail":
                log(f"\n[FAIL] Brain gave up: {thought}")
                return {"status": "fail", "steps": step, "history": history}

            if act in _POINT_VERB:
                # point-and-do: the Eyes locate the named target, the Hands act at that pixel
                target = action.get("target", "")
                loc = locate(shot, target)                       # Eyes: where
                hands({"type": act, "x": loc["x"], "y": loc["y"]})  # Hands: do
                did = f"{_POINT_VERB[act]} '{target}' at ({loc['x']},{loc['y']})"
            elif act == "scroll":
                target = action.get("target", "")
                direction = (action.get("direction") or "down").lower()
                loc = locate(shot, target)
                hands({"type": "scroll", "x": loc["x"], "y": loc["y"], "direction": direction})
                did = f"scrolled {direction} at '{target}' ({loc['x']},{loc['y']})"
            elif act == "drag":
                target = action.get("target", "")
                dest = action.get("destination", "")
                a = locate(shot, target)                         # Eyes: start point
                b = locate(shot, dest)                           # Eyes: drop point
                hands({"type": "drag", "x": a["x"], "y": a["y"], "x2": b["x"], "y2": b["y"]})
                did = f"dragged '{target}' ({a['x']},{a['y']}) -> '{dest}' ({b['x']},{b['y']})"
            elif act == "wait":
                # Let a loading screen settle. No UI interaction — just pause and re-observe.
                # The Brain chooses the duration; clamp to a sane range.
                try:
                    secs = float(action.get("seconds", 2))
                except (TypeError, ValueError):
                    secs = 2.0
                secs = max(0.5, min(secs, 30.0))    # 30s ceiling ~ standard API timeout
                time.sleep(secs)
                did = f"waited {secs:g}s for the screen to settle"
            elif act == "screenshot":
                # Capture the current screen as a deliverable (distinct from the per-step
                # diagnostic frames). Reuses this step's frame — exactly what the Brain saw.
                captures += 1
                runlog.save_image(f"capture-{captures:02d}.png", shot)
                did = f"captured screenshot #{captures} (capture-{captures:02d}.png)"
            elif act == "shell":
                # Tier-2 effector: run a command directly instead of driving the GUI. The
                # result is invisible on screen, so thread exit + output into HISTORY —
                # that's how the Brain sees what happened (vision uses the next screenshot).
                cmd = action.get("command", "")
                payload = {"command": cmd}
                if action.get("timeout") is not None:
                    payload["timeout"] = action["timeout"]
                if action.get("stdin") is not None:
                    payload["stdin"] = action["stdin"]
                res = exec_cmd(payload)
                out = (res.get("stdout") or "").strip()
                did = f"ran shell '{cmd}' -> exit {res.get('exit_code')}; out: {out or '(empty)'}"
                err = (res.get("stderr") or "").strip()
                if not res.get("ok") and err:
                    did += f"; err: {err}"
                if res.get("timed_out"):
                    did += " [TIMED OUT]"
            elif act == "type":
                # type sends text to whatever is FOCUSED — it must NOT click first, or it
                # would drop the cursor/selection the Brain just set up (e.g. a Ctrl+A
                # select-all before a replace). The Brain focuses fields with explicit
                # click actions; type just types.
                text = action.get("text", "")
                hands({"type": "type", "text": text})
                did = f"typed '{text}'"
            elif act == "key":
                k = action.get("key", "")
                hands({"type": "key", "key": k})
                did = f"pressed key '{k}'"
            else:
                did = f"unknown action skipped: {action}"

            # History holds ONLY the actions taken. The Brain judges the current state
            # from the CURRENT OBSERVATION (an accurate VLM describe), not from a pile of
            # stale past descriptions — accumulating those blurs the signal, especially
            # now that describe is verbose.
            history.append(did)

            log("")
            time.sleep(settle)

        log("\n[STOP] step limit reached without a done/fail.")
        return {"status": "step_limit", "steps": max_steps, "history": history}
    finally:
        runlog.stop()
