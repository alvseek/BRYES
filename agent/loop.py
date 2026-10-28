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
from brain.client import answer, build_system_prompt, decide, select_embodiment  # noqa: E402
from devices import ALL_VERBS, ContainerDevice, PhoneDevice, WindowsDevice, clamp_hold  # noqa: E402
from devices.windows import host_allowed  # noqa: E402
from eyes.client import DESCRIBE_PROMPT, GROUND_PROMPT, describe, locate  # noqa: E402
from eyes.client import diff as vlm_diff
from profiles import load_profiles, profile_exists, read_catalog  # noqa: E402

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

# Coordinate verbs: the Brain names a pixel instead of a description, so the Eyes are skipped.
# Each rides on a pointer the body already advertises, which is why they are DERIVED in
# _actions_for rather than added to a body's verb set.
_COORD_VERB = {
    "move_to": "hover",     # a pure move: every desk body's hover is a moveTo
    "click_at": "click",
}

# Which actions leave the SCREEN unchanged (ADR-007): shell + screenshot never touch it, and a
# FAILED action leaves it as-is. Everything else — INCLUDING `wait`, whose whole purpose is to
# let content load — may change the screen. Drives the channel-aware CURRENT CONDITION and
# (Phase 3) lets the loop skip a redundant describe().
_SCREEN_UNCHANGED_ACTS = frozenset({"shell", "screenshot"})


def _changes_screen(act, failed):
    """True if this action may have changed the screen (so the next observation is worth reading)."""
    return not failed and act not in _SCREEN_UNCHANGED_ACTS


def wants_diff(action, after_drag):
    """Whether the next observation carries a before/after diff.

    The Brain may ask for one itself; a completed drag asks automatically (R6), because a drag
    that released somewhere else still changed the screen and nothing else would say so.
    """
    return bool(action.get("request_diff")) or bool(after_drag)


def drag_endpoint(action, start):
    """Where a drag releases: `start` plus `destination_offset`, or None to locate `destination`.

    A canvas has no element at the drop point, so describing it asks the Eyes a question they
    cannot answer (measured: 0 of 6 on empty-canvas requests). An offset is what a coordinate
    space actually offers. A malformed offset raises rather than silently falling back to a
    description nobody supplied.
    """
    offset = action.get("destination_offset")
    if not offset:
        return None
    try:
        dx, dy = int(offset["dx"]), int(offset["dy"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"destination_offset needs integer dx and dy, got {offset!r}") from e
    return (int(start["x"]) + dx, int(start["y"]) + dy)

# Recovery backstop (Phase 5): the Brain now judges progress itself, by comparing the Eyes'
# VERIFICATION report to what it expected. The loop keeps only a dumb, ADVISORY guard against
# a runaway — the SAME action repeated many times in a row (different actions never trip it,
# so exploration is safe; a legitimately-repeating action like scrolling just gets a nudge it
# can ignore). Real recovery lives in the Brain, off the accurate report.
_REPEAT_LIMIT = 2   # consecutive identical actions before an advisory "you're repeating" nudge
_FAILURE_LIMIT = 3  # consecutive action-execution FAILURES before a "reconsider or fail" nudge


# Embodiment selection (ADR-006): a profile path's top-level (OS) segment names the BODY it
# belongs to, so the Brain's pick of a profile path also picks the device. One body per run.
# `windows` is the REAL desktop: registered so an explicit `device="windows"` resolves, and
# deliberately absent from the profile catalog so the auto-picker can never choose it.
_ROOT_DEVICE = {"android": PhoneDevice, "linux": ContainerDevice, "windows": WindowsDevice}


def _make_device(root, **kw):
    """Instantiate the body for an OS root, failing CLEARLY if it can't be reached (e.g. the
    phone is unplugged/locked) — we never silently substitute a different body (ADR-006).

    The host body also fails EARLY here when `BRYES_ALLOW_HOST` is unset, so a run says why
    in one line instead of dying at the first click.
    """
    if root == "windows" and not host_allowed():
        raise RuntimeError(
            "device 'windows' drives the REAL desktop; set BRYES_ALLOW_HOST=1 to allow it "
            "(the container body needs no such switch)")
    if root == "windows" and not kw.get("window"):
        # R9: the host guards are no-ops without a target. `_ensure_foreground` returns early and
        # `_require_inside_target` cannot even compute a rect, so a host run with no window clicks
        # the whole desktop unchecked. Refuse here, where every run-built body passes.
        raise RuntimeError(
            "refusing to drive the real desktop without a target window: name it with "
            "window='<title substring>' so the frame, the foreground guard and the rect guard "
            "all have something to hold on to")
    # Drop None so a body with no such parameter is not handed one: `window=None` used to
    # reach ContainerDevice and break every non-host run.
    kw = {name: value for name, value in kw.items() if value is not None}
    try:
        return _ROOT_DEVICE[root](**kw)
    except Exception as e:
        raise RuntimeError(f"chose body {root!r} but it's unavailable: {e}") from e


def _first_seg(path):
    """The top-level (OS/body) segment of a profile path, or "" if the path is empty."""
    stripped = str(path).strip("/")
    return stripped.split("/")[0] if stripped else ""


def _root_of(paths):
    """The shared top-level (OS) segment of profile paths — the one body they all belong to.
    Raises if the list is empty or the paths span more than one body (that would be two bodies)."""
    roots = {seg for p in paths if (seg := _first_seg(p))}
    if not roots:
        raise RuntimeError("no profile paths to derive a body from")
    if len(roots) > 1:
        raise RuntimeError(f"profiles span multiple bodies {sorted(roots)} — one body per run")
    return roots.pop()


def _validate_under(root, paths):
    """Every path must sit under `root` (same first segment) AND resolve to a real profile.md.
    Raises RuntimeError on the first offender (the ef253360 one-body-per-run constraint)."""
    for p in paths:
        if _first_seg(p) != root:
            raise RuntimeError(f"profile {p!r} is not under body {root!r}")
        if not profile_exists(p):
            raise RuntimeError(f"profile {p!r} has no profiles/{p}/profile.md")


def resolve_embodiment(goal, *, picker, catalog_reader):
    """PURE embodiment decision — no device instantiation, no loop. Ask the injected `picker`
    for an Embodiment, then classify it. Returns one of:
      {"mode": "answer", "reason": str}                                   -> no body; answer the goal
      {"mode": "loop", "root": str, "profiles": list[str], "reason": str} -> inhabit `root`, load profiles
    Raises RuntimeError on an unknown body or an incoherent (mixed/invalid) profile set.
    Injecting `picker`/`catalog_reader` keeps this unit-testable without a live model."""
    emb = picker(goal, catalog_reader())
    if emb.device is None:
        return {"mode": "answer", "reason": emb.reason}
    root = emb.device
    if root not in _ROOT_DEVICE:
        raise RuntimeError(f"picked unknown body {root!r}; known: {sorted(_ROOT_DEVICE)}")
    _validate_under(root, emb.profiles)
    return {"mode": "loop", "root": root, "profiles": list(emb.profiles), "reason": emb.reason}


def run(goal, max_steps=12, settle=0.6, verbose=True, tag="run", brain_model=None,
        device=None, profile=None, window=None):
    """Drive the loop until the Brain says done/fail or steps run out.

    Every step's prompts and raw replies (describe / decide / locate / action) plus the
    screenshot are preserved to a transcript under artifacts/runs/ (see runlog); `tag`
    names that run folder.

    `window` names a surface on the host body (`device="windows"`): a title substring the
    body keeps in front and captures. It never reaches the Brain or the Eyes, and it is
    useless on any other body, so combining it with one is an error rather than a no-op.
    """
    # VLM describe/decide text (and an answer-only reply) can contain non-ASCII that crashes the
    # default Windows console (cp1252). Make console output lossy-but-safe FIRST so a stray glyph
    # never kills a run. (The transcript file is UTF-8 already.)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    # A body NAME (e.g. "windows") is materialised here so `window` can reach it; an already
    # built Device instance passes through untouched, and keeps the loop transport-blind.
    # A named window SELECTS the host body (R9): a caller who knows which window to drive should
    # not also have to name the device. A built Device instance is still an override, and a forced
    # profile still derives the body from its own root.
    if window is not None and device is not None and not isinstance(device, str):
        # A body you built yourself already carries its target (or does not). Accepting `window`
        # here would drop it on the floor, and a silently ignored target is how a run drives the
        # wrong thing.
        raise ValueError(
            "window cannot be applied to a Device you built: give that body its target "
            "(WindowsDevice(hwnd=...)), or pass device='windows' with window=... instead")
    if window is not None and device is None and profile is None:
        device = "windows"
    if isinstance(device, str):
        device = _make_device(device, window=window)

    # Embodiment selection (ADR-006): if the caller forced NEITHER a device NOR a profile, the
    # Brain picks the body + profiles for this goal — or picks NO body and we answer directly.
    # An explicit `device`/`profile` is an override (testing / direct control): no pick then.
    profile_paths = []
    if device is None and profile is None:
        plan = resolve_embodiment(goal, picker=select_embodiment, catalog_reader=read_catalog)
        if plan["mode"] == "answer":
            ans = answer(goal)
            if verbose:
                print(f"GOAL: {goal}\n\n[ANSWER-ONLY] {plan['reason']}\n{ans}\n")
            return {"status": "answered", "answer": ans, "reason": plan["reason"]}
        device = _make_device(plan["root"])            # instantiate the chosen body (fail clearly)
        profile_paths = plan["profiles"]
        embodiment_note = f"picked body={plan['root']} profiles={profile_paths} - {plan['reason']}"
    elif profile is not None:
        # Forced profile(s): accept a str or a list; derive + validate the body from the root.
        profile_paths = [profile] if isinstance(profile, str) else list(profile)
        root = _root_of(profile_paths)
        _validate_under(root, profile_paths)
        device = device or _make_device(root, window=window)
        embodiment_note = f"forced profiles={profile_paths} on body={root}"
    else:
        # Forced device instance, no profile.
        embodiment_note = f"forced device={device.caps.name}"
    if window:
        embodiment_note += f" window={window!r}"

    # App/OS profile (profiles.py): the VISUAL half primes the Eyes, the OPERATING half the Brain,
    # so both know the current app's UI + conventions. Merges multiple profiles (ADR-006).
    prof = load_profiles(profile_paths)
    prof_visual = prof["visual"] or None
    prof_operating = prof["operating"] or None

    def log(*a):
        if verbose:
            print(*a)

    log(f"GOAL: {goal}\n")
    static = {"eyes.DESCRIBE_PROMPT": DESCRIBE_PROMPT,
              "eyes.GROUND_PROMPT": GROUND_PROMPT,
              "brain.SYSTEM_PROMPT": build_system_prompt(device.caps),
              # The injected app/OS profile context — logged so a run's transcript SHOWS exactly
              # what visual/operating help the Eyes and Brain were given (else it's invisible).
              "profile.visual (-> Eyes)": prof_visual or "(none)",
              "profile.operating (-> Brain)": prof_operating or "(none)"}
    rundir = runlog.start(goal, static=static, tag=tag)
    runlog.note(f"embodiment - {embodiment_note}")
    log(f"(transcript -> {rundir})\n")
    history = []
    findings = []                # ADR-007: append-only CONFIRMED FINDINGS ledger (loop-owned)
    last_action_desc = None      # CURRENT CONDITION: the previous step's action ...
    last_result = None           # ... and its channel-aware result (screen-pointer / shell outcome)
    visual_unchanged = False     # did the last action leave the current screen unchanged?
    prev_observation = None      # last DESCRIBED observation — reused when the screen didn't change
    visual_focus = None
    visual_expectation = None    # the Brain's prediction for THIS step (set last step)
    want_diff = False            # did the last action ask for an expensive 2-image diff?
    diff_after_drag = False      # R6: a drag's failure still changes the screen, so ask for one
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

            # Phase 3 (ADR-007): if the LAST action left the screen UNCHANGED (shell / screenshot
            # / a failed action) and the Brain asked for no explicit look (focus / recheck / diff),
            # SKIP the describe() model call and reuse the prior observation — the Eyes would only
            # re-read an identical screen. Any explicit perception request is still honored.
            skip_describe = (visual_unchanged and prev_observation is not None
                             and not (visual_focus or want_recheck or want_diff))
            if skip_describe:
                observation = prev_observation
                # The reused screen is NOT a fresh verification — drop a stale "VERIFICATION:"
                # prefix (it referred to an expectation from an earlier step) so it doesn't mislead.
                if observation.startswith("VERIFICATION:") and "\n\n" in observation:
                    observation = observation.split("\n\n", 1)[1]
                t_describe = 0.0
                log("         [eyes skipped] screen unchanged since a non-visual action")
            else:
                if want_recheck:
                    log("         [recheck] re-reading the visual_focus region on the 72B (careful)")
                t = time.perf_counter()
                # Eyes: what's on screen. describe() picks its mode (ADR-004): no visual_focus -> a
                # downscaled OVERVIEW gist; visual_focus set -> TRIM (72B box -> crop -> fast describe).
                # It also REPORTs the actual state of what the Brain set in `visual_expectation`
                # ("VERIFICATION: ...") for the Brain to compare — the Eyes perceive; the Brain judges.
                # careful=want_recheck routes the crop describe to the 72B (the recheck rung).
                observation = describe(shot, visual_focus=visual_focus,
                                       visual_expectation=visual_expectation, careful=want_recheck,
                                       context=prof_visual)
                t_describe = time.perf_counter() - t
            prev_observation = observation

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
            action = decide(goal, history=history, caps=device.caps,
                            model=brain_model, escalation=escalation,
                            context=prof_operating,           # device- + app-aware decide
                            last_action=last_action_desc, last_result=last_result,
                            current_visual=observation, visual_unchanged=visual_unchanged,
                            findings=findings)               # ADR-007: channel-aware condition + ledger
            t_decide = time.perf_counter() - t
            totals["screen"] += t_screen
            totals["describe"] += t_describe
            totals["decide"] += t_decide
            action.pop("_usage", None)
            act = action.get("action")
            thought = action.get("thought", "")
            note = action.get("note")                     # compact "why" -> HISTORY (ADR-007)
            new_findings = action.get("findings")         # facts to BANK -> CONFIRMED FINDINGS
            if new_findings:
                findings.append(f"[step {step}] {new_findings}")
                log(f"         findings+: {new_findings[:80].strip()}")
            visual_focus = action.get("visual_focus")   # per-step, NOT sticky: set -> TRIM there, omit -> OVERVIEW
            visual_expectation = action.get("visual_expectation")   # verified next step (not sticky)
            want_diff = wants_diff(action, diff_after_drag)   # 2-image diff next step
            diff_after_drag = False
            want_recheck = bool(action.get("recheck"))     # careful 72B re-read next step (not sticky)
            # Track repeated identical actions for the advisory runaway guard above.
            sig = (act, action.get("target") or action.get("text")
                   or action.get("click_target") or action.get("key") or "")
            repeat_streak = repeat_streak + 1 if sig == last_sig else 0
            last_sig = sig

            log(f"[step {step}] eyes: {observation[:100].strip()}...")
            detail = (action.get("target") or action.get("text")
                      or action.get("click_target") or action.get("key")
                      or action.get("command") or "")
            log(f"         brain: {thought}")
            log(f"         -> {act} {detail}".rstrip())
            if visual_focus:
                log(f"         visual_focus: {visual_focus}")

            if act == "done":
                log("\n[OK] Brain reports the goal is complete.")
                return {"status": "done", "steps": step, "history": history,
                        "findings": findings}
            if act == "fail":
                log(f"\n[FAIL] Brain gave up: {thought}")
                return {"status": "fail", "steps": step, "history": history,
                        "findings": findings}

            _loc["s"] = 0.0
            step_failed = False
            outcome = None       # non-visual RESULT text for CURRENT CONDITION (shell / failure)
            gesture = None       # short action label for CURRENT CONDITION (else the full `did`)
            t = time.perf_counter()
            try:
                if act in ALL_VERBS and act not in device.caps.verbs:
                    # Defensive: the Brain's vocab is built from caps (Phase 2), so this
                    # shouldn't happen — but if a verb this body can't do slips through, skip
                    # it rather than error.
                    did = f"skipped '{act}': not supported by {device.caps.name}"
                elif act == "shell" and not device.caps.has_shell:
                    did = f"skipped 'shell': {device.caps.name} has no shell channel"
                elif act in _COORD_VERB:
                    # A pixel the Brain already knows: no Eyes call, so no chance of a misread.
                    x, y = action.get("x"), action.get("y")
                    if x is None or y is None:
                        raise ValueError(f"{act} needs x and y in pixels, got x={x!r} y={y!r}")
                    device.act({"type": _COORD_VERB[act], "x": int(x), "y": int(y)})
                    did = f"{act.replace('_', ' ')} at ({int(x)},{int(y)})"
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
                    a = timed_locate(shot, target)                         # Eyes: start point
                    end = drag_endpoint(action, a)
                    if end is None:
                        # A named drop point: the second locate, for a target that exists.
                        dest = action.get("destination", "")
                        b = timed_locate(shot, dest)
                        end = (b["x"], b["y"])
                        where = f"'{dest}' ({end[0]},{end[1]})"
                    else:
                        # A canvas drop: a delta from the start, with nothing to locate.
                        where = f"({end[0]},{end[1]}) via destination_offset"
                    device.act({"type": "drag", "x": a["x"], "y": a["y"],
                                "x2": end[0], "y2": end[1]})
                    did = f"dragged '{target}' ({a['x']},{a['y']}) -> {where}"
                    diff_after_drag = True        # R6: the next step gets a before/after diff
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
                    outcome = f"exit {res.get('exit_code')}; out: {out or '(empty)'}"
                    err = (res.get("stderr") or "").strip()
                    if not res.get("ok") and err:
                        outcome += f"; err: {err}"
                    if res.get("timed_out"):
                        outcome += " [TIMED OUT]"
                    did = f"ran shell '{cmd}' -> {outcome}"   # full form -> HISTORY
                    gesture = f"ran shell: {cmd}"             # short form -> CURRENT CONDITION
                elif act == "type_into":
                    # Field-entry combo. The loop owns PERCEPTION: ground the optional
                    # click_target to a pixel here (the device has no Eyes). Then hand the whole
                    # click? -> clear? -> type -> Enter? gesture to the BODY, which knows how to
                    # perform it (desktop ctrl+a clear + Return; a phone its own idiom). One
                    # Brain decision, one device gesture. A failing sub-step raises and is caught
                    # by the outer handler (non-fatal), aborting the rest of the gesture.
                    text = action.get("text", "")   # same field as `type` — no separate type_text
                    click_target = action.get("click_target")
                    click_xy = None
                    if click_target:
                        loc = timed_locate(shot, click_target)     # Eyes: where the field is
                        click_xy = (loc["x"], loc["y"])
                    device.type_into(text, click_xy=click_xy,
                                     clear_first=bool(action.get("clear_first")),
                                     press_enter=bool(action.get("press_enter_after")))
                    did = ("typed '" + text + "' into "
                           + (f"'{click_target}'" if click_target else "the focused field")
                           + (" (cleared first)" if action.get("clear_first") else "")
                           + (" then pressed Enter" if action.get("press_enter_after") else ""))
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
                elif act == "key_hold":
                    # A held key, for surfaces that watch key STATE rather than key taps
                    # (a game character walks while the key is down). Clamped here so the
                    # Brain cannot ask for a hold longer than the body will honour.
                    k = action.get("key", "")
                    secs = clamp_hold(action.get("seconds"))
                    device.act({"type": "key_hold", "key": k, "seconds": secs})
                    did = f"held key '{k}' for {secs:g}s"
                else:
                    did = f"unknown action skipped: {action}"
                action_failures = 0    # the action executed cleanly — reset the failure streak
            except Exception as e:
                # A Hands/Eyes/shell call FAILED (bad key, unlocatable target, a container or
                # network hiccup). Do NOT crash the run — turn the failure into a Brain-visible
                # history note so it adapts next step (Phase-5: problems become observations the
                # Brain judges). The step still advances; _FAILURE_LIMIT guards a failure storm.
                action_failures += 1
                step_failed = True
                detail = (action.get("target") or action.get("text")
                          or action.get("click_target") or action.get("key")
                          or action.get("command") or "")
                code = getattr(e, "code", None)      # HTTPError carries the status code
                cause = f"HTTP {code}" if code else f"{type(e).__name__}: {str(e)[:80]}"
                did = (f"action '{act}'" + (f" '{detail}'" if detail else "")
                       + f" FAILED ({cause}); the screen is unchanged — try a genuinely "
                       "DIFFERENT action, or use 'fail' if you cannot proceed")
                gesture = f"tried '{act}'" + (f" '{detail}'" if detail else "")
                outcome = f"FAILED ({cause}); the screen is unchanged"
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

            # HISTORY carries the action + a COMPACT note (the Brain's why), so later steps see
            # intent, not just the raw action (ADR-007). Durable FACTS live in CONFIRMED FINDINGS,
            # not here; verbose describe text is still kept OUT of history.
            history.append(did + (f" - {note}" if note else ""))

            # Channel-aware CURRENT CONDITION for the NEXT step (ADR-007): did the action change
            # the screen? If so, the result shows there; if not (shell/screenshot/failed), the
            # outcome is the action line itself and the screen is unchanged.
            changed = _changes_screen(act, step_failed)
            last_action_desc = gesture or did
            if changed:
                last_result = "(the effect shows on the Current screen below)"
            else:
                last_result = outcome if outcome is not None else "(no screen change)"
            visual_unchanged = not changed

            # Carry this step's frame forward for the Layer-3 2-image diff: next step's
            # request_diff compares prev_shot (before the action) vs the fresh frame (after).
            prev_shot = shot

            log("")
            time.sleep(settle)

        log("\n[STOP] step limit reached without a done/fail.")
        return {"status": "step_limit", "steps": max_steps, "history": history,
                "findings": findings}
    finally:
        tt = totals
        log(f"\n[timing totals] screen {tt['screen']:.1f}s | describe {tt['describe']:.1f}s | "
            f"decide {tt['decide']:.1f}s | locate {tt['locate']:.1f}s | act {tt['act']:.1f}s")
        runlog.note(f"totals — screen {tt['screen']:.1f}s | describe {tt['describe']:.1f}s | "
                    f"decide {tt['decide']:.1f}s | locate {tt['locate']:.1f}s | act {tt['act']:.1f}s")
        runlog.stop()
