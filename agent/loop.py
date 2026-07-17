"""BRYES Phase 4 — Close the Loop (+ first Phase-5 cut).

Chains the four pieces into one autonomous cycle:

    screenshot -> Eyes.describe(visual_focus) -> Brain.decide -> Eyes.locate -> Hands act -> repeat
                                                        until "done"/"fail"/step-limit

Phase-5 change-feedback in the loop:
  - The Brain predicts a checkable `visual_expectation` with each action; the loop rides it into the
    next describe(), where the Eyes REPORT the actual state of that thing ("VERIFICATION:
    ...") — grounded perception, NOT a verdict; the Brain compares it to what it expected
    (Layer 2, the primary change-feedback: Eyes perceive, Brain judges). A screen-wide pixel
    diff can't answer this — it drowns small changes (a typed digit) in whole-frame noise and
    can't be regionally cropped (UI-TARS only points) — so this is the VLM's job, not a pixel
    metric. (The VLM is asked to REPORT, not judge, because its binary verdicts were noisy —
    whitespace nitpicks, self-contradictions — while its descriptions are accurate.)
  - The Brain steers the Eyes via a `visual_focus` region, carried into the next describe().
  - When stuck, the Brain can request an EXPENSIVE 2-image diff (request_diff) of the
    before/after frames for a precise account of what changed (Layer 3).
  - Recovery lives in the Brain (it rethinks off the accurate VERIFICATION report). The loop
    keeps only a dumb, ADVISORY guard: if the SAME action repeats many times it nudges (and,
    one step later, suggests the 2-image diff). Different actions never trip it, so
    exploration is safe; it never picks the action itself.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runlog  # noqa: E402
from brain.client import build_system_prompt, decide  # noqa: E402
from devices import ALL_VERBS, ContainerDevice  # noqa: E402
from eyes.client import DESCRIBE_PROMPT, GROUND_PROMPT, describe, locate  # noqa: E402
from eyes.client import diff as vlm_diff

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

# Recovery backstop (Phase 5): the Brain now judges progress itself, by comparing the Eyes'
# VERIFICATION report to what it expected. The loop keeps only a dumb, ADVISORY guard against
# a runaway — the SAME action repeated many times in a row (different actions never trip it,
# so exploration is safe; a legitimately-repeating action like scrolling just gets a nudge it
# can ignore). Real recovery lives in the Brain, off the accurate report.
_REPEAT_LIMIT = 2   # consecutive identical actions before an advisory "you're repeating" nudge
_FAILURE_LIMIT = 3  # consecutive action-execution FAILURES before a "reconsider or fail" nudge


def run(goal, max_steps=12, settle=0.6, verbose=True, tag="run", brain_model=None,
        device=None):
    """Drive the loop until the Brain says done/fail or steps run out.

    Every step's prompts and raw replies (describe / decide / locate / action) plus the
    screenshot are preserved to a transcript under artifacts/runs/ (see runlog); `tag`
    names that run folder.
    """
    device = device if device is not None else ContainerDevice()

    # VLM describe/decide text can contain non-ASCII (UI glyphs like the dropdown triangle,
    # em-dashes, etc.) that crash the default Windows console (cp1252). Make console output
    # lossy-but-safe so a stray glyph never kills a run. (The transcript file is UTF-8 already.)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

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
    visual_focus = None
    visual_expectation = None    # the Brain's prediction for THIS step (set last step)
    want_diff = False            # did the last action ask for an expensive 2-image diff?
    want_recheck = False         # did the last action ask for a careful 72B re-read? (recheck rung)
    captures = 0
    prev_shot = None             # last step's frame — kept for the Layer-3 2-image diff
    last_sig = None              # signature of the previous action
    repeat_streak = 0            # consecutive identical actions (advisory runaway guard)
    action_failures = 0          # consecutive action-execution failures (non-fatal-action guard)
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

            if want_recheck:
                log("         [recheck] re-reading the visual_focus region on the 72B (careful)")
            t = time.perf_counter()
            # Eyes: what's on screen. describe() picks its mode (ADR-004): no visual_focus -> a
            # downscaled OVERVIEW gist; visual_focus set -> TRIM (72B box -> crop -> fast describe).
            # It also REPORTs the actual state of what the Brain set in `visual_expectation`
            # ("VERIFICATION: ...") for the Brain to compare — the Eyes perceive; the Brain judges.
            # careful=want_recheck routes the crop describe to the 72B (the recheck rung of the ladder).
            observation = describe(shot, visual_focus=visual_focus,
                                   visual_expectation=visual_expectation, careful=want_recheck)
            t_describe = time.perf_counter() - t

            # Layer 3 (Phase 5): if the LAST action requested it, run the EXPENSIVE 2-image
            # diff (prev vs current = the effect of that action) and append a precise
            # "what changed" account to the observation the Brain is about to read. Gated
            # by the Brain (request_diff) — never automatic.
            if want_diff and prev_shot is not None:
                changes = vlm_diff(prev_shot, shot, visual_focus=visual_focus)
                observation += "\n\nCHANGES SINCE YOUR LAST ACTION:\n" + changes
                log(f"         [diff] {changes[:100].strip()}...")

            # Recovery backstop (Phase 5): dumb, ADVISORY runaway guard — if the SAME action
            # has repeated many times, nudge the Brain (graduated: at limit+1 also push the
            # 2-image diff). The Brain does the real recovery from the VERIFICATION report;
            # this only catches a stubborn loop, and never picks the action itself.
            escalation = None
            if repeat_streak >= _REPEAT_LIMIT and last_sig:
                a, tgt = last_sig
                what = f"the same '{a}'" + (f" on '{tgt}'" if tgt else "") + " action"
                base = (f"SYSTEM ALERT: you have repeated {what} {repeat_streak + 1} times in "
                        "a row with no apparent progress.")
                if repeat_streak >= _REPEAT_LIMIT + 1:
                    escalation = (base + " STOP repeating it. Set \"request_diff\": true to "
                                  "get a precise account of what is actually on screen, then "
                                  "choose a genuinely DIFFERENT action — or use 'fail' if the "
                                  "goal cannot be reached.")
                else:
                    escalation = (base + " Reconsider — try a genuinely DIFFERENT action, or "
                                  "use 'fail' if the goal cannot be reached.")
                log(f"         [escalation] same action x{repeat_streak + 1} -> nudging Brain"
                    + (" (suggest diff)" if repeat_streak >= _REPEAT_LIMIT + 1 else ""))

            # Failure-storm guard: unlike the repeat-guard (same action), this catches a run
            # where DIFFERENT actions keep failing to EXECUTE (bad targets, a sick body). After
            # _FAILURE_LIMIT consecutive failures, nudge the Brain to change tack or give up.
            if action_failures >= _FAILURE_LIMIT:
                storm = (f"SYSTEM ALERT: {action_failures} actions in a row FAILED to execute "
                         "(see the FAILED notes in your history). Your current approach is not "
                         "working — choose a genuinely DIFFERENT action, or use 'fail' if the "
                         "goal cannot be reached.")
                escalation = (escalation + " " + storm) if escalation else storm
                log(f"         [escalation] {action_failures} consecutive failures -> nudging Brain")

            t = time.perf_counter()
            action = decide(goal, observation, history, caps=device.caps,
                            model=brain_model, escalation=escalation)  # device-aware decide
            t_decide = time.perf_counter() - t
            totals["screen"] += t_screen
            totals["describe"] += t_describe
            totals["decide"] += t_decide
            action.pop("_usage", None)
            act = action.get("action")
            thought = action.get("thought", "")
            visual_focus = action.get("visual_focus")   # per-step, NOT sticky: set -> TRIM there, omit -> OVERVIEW
            visual_expectation = action.get("visual_expectation")   # verified next step (not sticky)
            want_diff = bool(action.get("request_diff"))   # 2-image diff next step (not sticky)
            want_recheck = bool(action.get("recheck"))     # careful 72B re-read next step (not sticky)
            # Track repeated identical actions for the advisory runaway guard above.
            sig = (act, action.get("target") or action.get("text")
                   or action.get("key") or "")
            repeat_streak = repeat_streak + 1 if sig == last_sig else 0
            last_sig = sig

            log(f"[step {step}] eyes: {observation[:100].strip()}...")
            detail = (action.get("target") or action.get("text") or action.get("key")
                      or action.get("command") or "")
            log(f"         brain: {thought}")
            log(f"         -> {act} {detail}".rstrip())
            if visual_focus:
                log(f"         visual_focus: {visual_focus}")

            if act == "done":
                log("\n[OK] Brain reports the goal is complete.")
                return {"status": "done", "steps": step, "history": history}
            if act == "fail":
                log(f"\n[FAIL] Brain gave up: {thought}")
                return {"status": "fail", "steps": step, "history": history}

            _loc["s"] = 0.0
            t = time.perf_counter()
            try:
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
                action_failures = 0    # the action executed cleanly — reset the failure streak
            except Exception as e:
                # A Hands/Eyes/shell call FAILED (bad key, unlocatable target, a container or
                # network hiccup). Do NOT crash the run — turn the failure into a Brain-visible
                # history note so it adapts next step (Phase-5: problems become observations the
                # Brain judges). The step still advances; _FAILURE_LIMIT guards a failure storm.
                action_failures += 1
                detail = (action.get("target") or action.get("text") or action.get("key")
                          or action.get("command") or "")
                code = getattr(e, "code", None)      # HTTPError carries the status code
                cause = f"HTTP {code}" if code else f"{type(e).__name__}: {str(e)[:80]}"
                did = (f"action '{act}'" + (f" '{detail}'" if detail else "")
                       + f" FAILED ({cause}); the screen is unchanged — try a genuinely "
                       "DIFFERENT action, or use 'fail' if you cannot proceed")
                log(f"         [action-error] {did}")
                if runlog:
                    runlog.record("action-error", {"action": action}, cause)

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

            # Carry this step's frame forward for the Layer-3 2-image diff: next step's
            # request_diff compares prev_shot (before the action) vs the fresh frame (after).
            prev_shot = shot

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
