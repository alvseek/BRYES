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
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runlog  # noqa: E402
from devices import ContainerDevice, ALL_VERBS  # noqa: E402
from eyes.client import describe, locate, DESCRIBE_PROMPT, GROUND_PROMPT  # noqa: E402
from brain.client import decide, build_system_prompt  # noqa: E402

# The Screen+Hands+shell transport now lives behind the Device abstraction (ADR-002):
# ContainerDevice is the default body; PhoneDevice / a future WindowsDevice slot in the
# same way. The loop calls device.screenshot()/act()/shell() and never a transport.

# Point-and-do actions handled identically: locate the named target, act at that pixel.
# (scroll and drag are handled separately — they need a direction / a second point.)
_POINT_VERB = {
    "click": "clicked",
    "double_click": "double-clicked",
    "right_click": "right-clicked",
    "hover": "hovered",
}


def run(goal, max_steps=12, settle=0.6, verbose=True, tag="run", brain_model=None,
        device=None):
    """Drive the loop until the Brain says done/fail or steps run out.

    Every step's prompts and raw replies (describe / decide / locate / action) plus the
    screenshot are preserved to a transcript under artifacts/runs/ (see runlog); `tag`
    names that run folder.
    """
    device = device if device is not None else ContainerDevice()

    def log(*a):
        if verbose:
            print(*a)

    log(f"GOAL: {goal}\n")
    static = {"eyes.DESCRIBE_PROMPT": DESCRIBE_PROMPT,
              "eyes.GROUND_PROMPT": GROUND_PROMPT,
              "brain.SYSTEM_PROMPT": build_system_prompt(device.caps)}
    rundir = runlog.start(goal, static=static, tag=tag)
    log(f"(transcript -> {rundir})\n")
    history = []
    focus = None
    captures = 0
    totals = {"screen": 0.0, "describe": 0.0, "decide": 0.0, "locate": 0.0, "act": 0.0}
    _loc = {"s": 0.0}      # per-step locate accumulator; timed_locate() adds into it

    def timed_locate(shot, instr):
        t = time.perf_counter()
        r = locate(shot, instr)
        _loc["s"] += time.perf_counter() - t
        return r

    try:
        for step in range(1, max_steps + 1):
            runlog.set_step(step)
            t = time.perf_counter()
            shot = device.screenshot()
            t_screen = time.perf_counter() - t
            runlog.save_image(f"step-{step:02d}.png", shot)
            t = time.perf_counter()
            observation = describe(shot, focus=focus)     # Eyes: what's on screen (focused)
            t_describe = time.perf_counter() - t
            t = time.perf_counter()
            action = decide(goal, observation, history,
                            caps=device.caps, model=brain_model)  # Brain decides (device-aware)
            t_decide = time.perf_counter() - t
            totals["screen"] += t_screen
            totals["describe"] += t_describe
            totals["decide"] += t_decide
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

            _loc["s"] = 0.0
            t = time.perf_counter()
            if act in ALL_VERBS and act not in device.caps.verbs:
                # Defensive: the Brain's vocab is built from caps (Phase 2), so this
                # shouldn't happen — but if a verb this body can't do slips through, skip
                # it rather than error.
                did = f"skipped '{act}': not supported by {device.caps.name}"
            elif act == "shell" and not device.caps.has_shell:
                did = f"skipped 'shell': {device.caps.name} has no shell channel"
            elif act in _POINT_VERB:
                # point-and-do: the Eyes locate the named target, the Hands act at that pixel
                target = action.get("target", "")
                loc = timed_locate(shot, target)                       # Eyes: where
                device.act({"type": act, "x": loc["x"], "y": loc["y"]})  # Hands: do
                did = f"{_POINT_VERB[act]} '{target}' at ({loc['x']},{loc['y']})"
            elif act == "scroll":
                target = action.get("target", "")
                direction = (action.get("direction") or "down").lower()
                loc = timed_locate(shot, target)
                device.act({"type": "scroll", "x": loc["x"], "y": loc["y"], "direction": direction})
                did = f"scrolled {direction} at '{target}' ({loc['x']},{loc['y']})"
            elif act == "drag":
                target = action.get("target", "")
                dest = action.get("destination", "")
                a = timed_locate(shot, target)                         # Eyes: start point
                b = timed_locate(shot, dest)                      # Eyes: drop point
                device.act({"type": "drag", "x": a["x"], "y": a["y"], "x2": b["x"], "y2": b["y"]})
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
                res = device.shell(cmd, timeout=action.get("timeout"),
                                   stdin=action.get("stdin"))
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
                device.act({"type": "type", "text": text})
                did = f"typed '{text}'"
            elif act == "key":
                k = action.get("key", "")
                device.act({"type": "key", "key": k})
                did = f"pressed key '{k}'"
            else:
                did = f"unknown action skipped: {action}"

            t_locate = _loc["s"]
            t_act = (time.perf_counter() - t) - t_locate
            totals["locate"] += t_locate
            totals["act"] += t_act
            tline = (f"timing: screen {t_screen:.1f}s | describe {t_describe:.1f}s | "
                     f"decide {t_decide:.1f}s | locate {t_locate:.1f}s | act {t_act:.1f}s")
            log(f"         {tline}")
            runlog.note(f"step {step} — {tline}")

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
        tt = totals
        log(f"\n[timing totals] screen {tt['screen']:.1f}s | describe {tt['describe']:.1f}s | "
            f"decide {tt['decide']:.1f}s | locate {tt['locate']:.1f}s | act {tt['act']:.1f}s")
        runlog.note(f"totals — screen {tt['screen']:.1f}s | describe {tt['describe']:.1f}s | "
                    f"decide {tt['decide']:.1f}s | locate {tt['locate']:.1f}s | act {tt['act']:.1f}s")
        runlog.stop()
