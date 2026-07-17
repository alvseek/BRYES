"""BRYES Phase 3 — The Brain.

Decides the single next action given the goal, a TEXT description of the screen,
and the history so far. Primary model qwen3.6-flash via OpenRouter, with deepseek-v4-flash
as the resilience fallback (ADR-005).

The Brain is text-only by design: it reasons about elements *by description*
(e.g. "the + button") and never about pixels. The Eyes (Phase 2) turn those
descriptions into coordinates; the Hands (Phase 1) execute them.
"""
import json
import os
import sys
from pathlib import Path

# Make the repo root importable so `structured` (and `runlog`) resolve no matter who imports us.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field  # noqa: E402

from structured import StructuredError, structured_call  # noqa: E402

try:                       # optional transcript logger (no-op when a run isn't logging)
    import runlog  # noqa: E402
except ImportError:
    runlog = None

# deepseek-v4-flash: the primary Brain. It returns clean, schema-valid JSON under our
# response_format json_schema standard WITH thinking on (verified 3/3 live), is served by 18
# providers, and is cheap. It replaced qwen3.6-flash (the old bake-off winner): qwen's
# Alibaba endpoint mis-applies a json_schema grammar / forced tool_choice to its THINKING
# stream and degenerates (content:null / finish_reason=error) — a documented, ecosystem-wide
# Qwen reasoning-model bug, not a provider outage. See ADR-005.
MODEL = "deepseek/deepseek-v4-flash"

# Backup Brain (ADR-005): if the primary fails its allotted tries (a provider degeneration /
# finish_reason=error), decide()'s LAST attempt escapes to this model. Chosen for RESILIENCE
# — gemini-2.5-flash-lite is DIFFERENT weights (Google), so it escapes a weight-level
# reasoning-loop the primary can't; and it was verified to return clean schema-valid JSON
# under json_schema+thinking (3/3 live) WITHOUT the reasoning-stream bug that breaks qwen /
# glm / hunyuan. (Reasoning-capable, so it still decides WELL on the rare step it drives.)
BACKUP_MODEL = "google/gemini-2.5-flash-lite"

# Standard OpenRouter attribution headers, sent on every structured call.
_OR_HEADERS = {"HTTP-Referer": "https://github.com/alvseek/BRYES", "X-Title": "BRYES"}

_BASE_PROMPT = """You are the Brain of a computer-use agent. You have more than one way
to act, and you pick the most DIRECT one that fits each task:
- SHELL (a real terminal inside the machine): the "shell" action runs a command line.
  Prefer it for anything the command line does well — files, system info, networking
  (curl), text processing, counting, installing packages. Direct and reliable.
- VISION (the Eyes + Hands): a separate component (the Eyes) can locate any on-screen
  element you name, and the Hands can click, double-click, right-click, hover, scroll,
  drag, type, and press keys. Use this for graphical apps and web pages — things that
  only exist on screen.
Given the GOAL, a text description of what is currently on screen (OBSERVATION), and the
HISTORY of prior steps, decide the SINGLE next action.

The HISTORY lists the actions you have ALREADY taken (most recent last). Judge the
current situation from the OBSERVATION — not from memory of past screens.

Rules:
- WRITE IN ENGLISH: reason and fill EVERY field of your reply in English only,
  whatever the GOAL wording or the on-screen language.
- CHOOSE THE RIGHT CHANNEL (shell vs vision). Prefer "shell" for anything a command line
  does well: reading/writing files, system info (uname, ls, cat), networking (curl/wget),
  text processing (grep/sed/awk), counting (find | wc), installing packages. Use VISION
  (click/type/scroll/...) only for graphical apps and web pages that exist only on screen.
  If a task genuinely needs an INTERACTIVE terminal (a REPL like python, an ssh session, a
  program that prompts mid-run), do NOT use "shell" — open a terminal window (xterm) and
  drive it with vision instead.
- FOLLOW THE OBSERVED STATE: your understanding of what is on screen right now MUST come
  from the current OBSERVATION, read EXACTLY as written — never from memory, assumption,
  or what you expected your last action to produce. Before choosing an action, evaluate
  three things in order: (a) what the OBSERVATION shows right now, (b) what you have
  already done (HISTORY), and (c) what still remains to reach the GOAL. Decide from that
  comparison. If the OBSERVATION contradicts what you expected, trust the OBSERVATION.
- COMPARE THE VERIFICATION REPORT: when the OBSERVATION begins with "VERIFICATION:", that
  is the Eyes reporting the ACTUAL state of what you set in "visual_expectation" (a grounded reading of
  the pixels, not a verdict). Compare it to what you expected. If it differs, your action
  MAYBE didn't do what you thought — rethink or adapt (re-read the state, try a different
  target or action). If it matches, proceed.
- RE-READ A DOUBTFUL REPORT (RECHECK): the visual_focus region is read by a FAST model, which
  can occasionally MISREAD a small crop. If a VERIFICATION report contradicts what you expected
  and you cannot tell whether your ACTION failed OR the Eyes simply misread that region, set
  "recheck": true AND re-state the same "visual_focus" (it is per-step now). Next step that
  region is re-read by a slower, higher-fidelity
  model — use that to confirm the real state BEFORE you conclude the action failed or change
  course. It is cheaper than a full diff. Escalate to "request_diff" only if a careful
  re-read still leaves you unable to tell what happened. Do NOT set "recheck" routinely — only
  on a genuine visual_expectation-vs-report contradiction.
- Refer to elements by description (e.g. "the Submit button").
  NEVER output pixel coordinates - the Eyes handle pixels.
- When a button's label is a symbol, name it with the WORD, e.g. "the equals (=)
  button", "the plus (+) button", "the minus (-) button". A bare symbol like "="
  is hard for the Eyes to locate; the word makes it reliable.
- DISAMBIGUATE WITH POSITION + CONTEXT: the same symbol or label can appear more than
  once on screen — e.g. an "=" both as a keypad button AND inside the displayed equation,
  or several look-alike buttons with the same function. Whenever that is possible, name
  the target with its LOCATION and context so the Eyes pick the RIGHT one, e.g. "the
  equals (=) button at the bottom-right of the keypad" or "the orange equals button on
  the keypad" — not just "the equals button".
- POINT THE EYES WHERE YOU NEED TO SEE (VISUAL_FOCUS): set "visual_focus" to the SECTION/
  REGION the Eyes should crop and read closely NEXT — the place whose EXACT state you need to
  see, not the whole app or window. This steers only WHERE the Eyes LOOK; it does NOT move
  the pointer or click (acting is grounded separately from "target"). CRUCIAL: point it at
  where you need to SEE THE OUTCOME — usually where your action's EFFECT appears (e.g. the
  result on the display), NOT the control you are about to operate (the button you click).
  Verification is ALWAYS about the display/result CONTENT: after ANY press — a digit OR an
  operator (x, /, +, -) — the change shows in the DISPLAY (e.g. "1024x"), never by a key
  lighting up; so aim the Eyes at the display/result, never at a key. The tighter and more
  contextual the region, the more accurately the Eyes report the state. "visual_focus" is
  PER-STEP and does NOT persist — it applies only to your NEXT observation: to keep watching
  the same region across steps, RE-STATE it each step; omit it on any step to get a
  whole-screen overview instead.
- GET YOUR BEARINGS WITH AN OVERVIEW: leave "visual_focus" EMPTY to receive a whole-screen
  OVERVIEW — a gist of everything on screen (apps, windows, what stands out). Use it to orient
  when you are unsure what is shown. If an OBSERVATION begins "VISUAL_FOCUS FAILED", the region
  you named is NOT visible (it may be closed, minimized, off-screen, or behind another window) —
  do NOT keep asking the Eyes for it. Take an overview (omit visual_focus) to re-orient, then
  act to bring the target into view (e.g. reopen or raise the window) before focusing on it again.
- PREDICT WHAT YOU'LL SEE (VISUAL_EXPECTATION): whenever you take an action that SHOULD change
  the screen, set "visual_expectation" to the state you predict will be TRUE right afterward,
  phrased as an ABSOLUTE, NAMEABLE target-state (e.g. "the Settings app is open", "the address
  bar shows example.com") — NOT a relative one ("something new appeared"). Next step the Eyes
  REPORT the actual state of that thing back to you (the OBSERVATION begins "VERIFICATION: ..."),
  for you to compare against what you expected. Set "visual_expectation" ONLY together with
  "visual_focus", and point "visual_focus" at the region where that change will be VISIBLE — the
  result/display area, NOT the button you pressed. The Eyes crop to it, read it closely, and
  REPORT its actual state. (After typing a digit, verifying it means looking at the DISPLAY, not
  the key you clicked.) A "visual_expectation" without a "visual_focus" cannot be verified precisely.
- WHEN STUCK, ASK FOR A DIFF (EXPENSIVE): if you cannot tell what your last action did —
  the OBSERVATION is ambiguous, or the VERIFICATION report doesn't match what you expected —
  set "request_diff": true. Next step you will receive a precise "CHANGES SINCE YOUR LAST
  ACTION" account. It costs a SLOW, EXPENSIVE extra vision pass, so use it sparingly —
  only when genuinely stuck, never as a routine check.
- ACTIONS — choose ONE "action", then fill ONLY the fields listed for it (each is `field: what to put in it`):
    type          — type into whatever is CURRENTLY focused (does NOT move focus)
        required:  text: the text to type
    type_into     — enter text into a field; PREFER this for text entry (does click -> clear -> type -> Enter in one step)
        required:  text: the text to type
        optional:  click_target: a field to click/focus first (omit to type into the already-focused field)
                   clear_first: true to clear the field's existing contents before typing (replace, not append)
                   press_enter_after: true to press Enter after typing (submit a search box / send a chat message)
    click         — left-click / tap
        required:  target: the element to click
    double_click  — open / activate an item
        required:  target: the element to double-click
    right_click   — open a context menu
        required:  target: the element to right-click
    hover         — reveal a menu/tooltip without clicking
        required:  target: the element to hover over
    scroll        — bring off-screen content into view
        required:  target: where to scroll  |  direction: "up" or "down"
    drag          — sliders, moving items
        required:  target: element to press on  |  destination: where to release
    key           — press a key or chord
        required:  key: e.g. Return, Escape, Tab, ctrl+a
    wait          — let a loading screen settle before looking again
        required:  seconds: how long to pause
    shell         — run a NON-interactive command (see SHELL below)
        required:  command: the command line to run
        optional:  timeout: seconds (default 30, max 300)  |  stdin: text for the command's standard input
    screenshot    — save the current frame as a requested deliverable (no fields)
    done          — the goal is already satisfied (no fields)
    fail          — truly stuck, or the goal is impossible (no fields)
  On ANY acting action you MAY also set the perception controls: visual_focus, visual_expectation, recheck, request_diff (see above).
- WAIT FOR LOADING, DON'T GUESS. If the screen is still loading (a spinner, or a blank/partial
  page with content not yet rendered), do NOT act on it or finish — use action "wait" and set
  "seconds" to how long to pause before looking again (e.g. 2-4s for a heavy web page, more if
  it is very slow). Waiting does not touch the screen; it just lets the content appear so your
  NEXT observation is accurate.
- SCREENSHOT TO CAPTURE. Use action "screenshot" to save the current screen as an output you
  were asked to produce (to record or capture what is shown). It does not change the screen.
  To capture content that spans multiple screens (a long or infinite results list), "scroll"
  and "screenshot" repeatedly so each part is saved.
- SHELL runs a NON-INTERACTIVE command to completion and returns its exit code and output.
  You will see that output in HISTORY on the next step — it is NOT shown on screen. The
  command cannot answer a prompt while it runs, so keep it non-interactive: pass flags like
  -y or DEBIAN_FRONTEND=noninteractive, pipe input, use heredocs, or set "stdin" to text to
  feed the command. For a slow-but-finite command (an install or a big download) set
  "timeout" to the seconds you expect, up to 300. For a very long job, start it in the
  background with "&" and check on it later. Put the full command line in "command".
- Choose exactly ONE next action that makes real progress toward the goal.
- If the OBSERVATION shows the goal is already satisfied, use action "done".
- If you are truly stuck or the goal is impossible, use action "fail".
- Return your decision as a SINGLE JSON object matching the decide_action schema — only the
  JSON object, no prose, no markdown fences.
"""

class BrainAction(BaseModel):
    """The Brain's single next action (ADR-005: returned via response_format json_schema and
    VALIDATED here through Pydantic — the guard is ours, not the provider's). `action`'s allowed
    values are injected per-body at call time (see decide); every other field is optional and
    applies only to specific actions (the system prompt's ACTIONS spec lists which fields each
    action uses). Each field description says what the field IS — not which actions use it."""

    thought: str = Field(
        description="Your reasoning in English: what the screen shows now, progress vs the "
                    "GOAL, and why this is the next action.")
    action: str = Field(
        description="The single next action to take (must be one of the allowed action names).")
    target: str | None = Field(
        None, description="An on-screen element, described so the Eyes can locate it.")
    destination: str | None = Field(
        None, description="An on-screen element, described so the Eyes can locate it (a drop point).")
    direction: str | None = Field(
        None, description="A direction: 'up' or 'down'.")
    seconds: float | None = Field(
        None, description="A number of seconds to pause.")
    text: str | None = Field(
        None, description="The text to type.")
    key: str | None = Field(
        None, description="A key or chord to press, e.g. Return, Escape, Tab, ctrl+a.")
    click_target: str | None = Field(
        None, description="An on-screen field to click (focus) before typing, described for the Eyes.")
    clear_first: bool | None = Field(
        None, description="Whether to clear the field's existing contents (select-all + delete) first.")
    press_enter_after: bool | None = Field(
        None, description="Whether to press Enter after typing.")
    command: str | None = Field(
        None, description="A shell command line to run.")
    timeout: int | None = Field(
        None, description="A timeout in seconds (default 30, max 300).")
    stdin: str | None = Field(
        None, description="Text to feed the command's standard input.")
    visual_expectation: str | None = Field(
        None, description="The specific target-state you predict you'll SEE after this action, "
                          "phrased ABSOLUTE/nameable (e.g. 'the display shows 1024', 'the "
                          "Settings app is open'); next step the Eyes read your visual_focus "
                          "region and REPORT that thing's actual state ('VERIFICATION: ...') "
                          "for you to compare.")
    visual_focus: str | None = Field(
        None, description="The SECTION/REGION the Eyes should crop and READ next — where you "
                          "need to SEE the outcome, i.e. where your action's EFFECT shows "
                          "(e.g. the display/result), NOT the control you operated (the "
                          "button); spatial — WHERE to look, never where to click; REQUIRED "
                          "whenever you set visual_expectation. Leave EMPTY to get a whole-"
                          "screen overview (a gist) — use that to re-orient, e.g. after a "
                          "'VISUAL_FOCUS FAILED' report means the region you named isn't visible.")
    recheck: bool | None = Field(
        None, description="Set true to re-read the SAME visual_focus region at higher fidelity "
                          "next step — ONLY when a VERIFICATION report contradicts your "
                          "expectation and you cannot tell if the action failed or the fast "
                          "read was wrong; cheaper than request_diff.")
    request_diff: bool | None = Field(
        None, description="Set true to request an EXPENSIVE, SLOW precise before/after visual "
                          "diff next step — ONLY when an effect is subtle or you are stuck; "
                          "NOT routinely.")

# Action vocabulary is assembled per-device from the active body's Capabilities (ADR-002):
# the Brain is only offered verbs the current body supports. The loop-meta actions (wait,
# screenshot, done, fail) are always available; `shell` only if the body has one. `caps` is
# read duck-typed (no devices import), so the Brain stays decoupled from device internals.
_VERB_ORDER = ("click", "double_click", "right_click", "hover", "scroll", "drag", "type", "key")
_FULL_VERBS = frozenset(_VERB_ORDER)     # back-compat default when decide() gets no caps


def _actions_for(caps):
    """The ordered actions this body offers: its supported verbs, +shell if it has one,
    plus the always-available loop metas. caps=None -> full desktop vocabulary."""
    verbs = _FULL_VERBS if caps is None else caps.verbs
    has_shell = True if caps is None else caps.has_shell
    acts = [v for v in _VERB_ORDER if v in verbs]
    if {"click", "type", "key"} <= verbs:
        acts.append("type_into")      # loop-grounded, device-composed field-entry combo
    acts += ["wait", "screenshot"]
    if has_shell:
        acts.append("shell")
    acts += ["done", "fail"]
    return acts


def _device_preamble(caps):
    """A short ACTIVE-BODY header naming the body the Brain controls and its exact action
    set. Empty for caps=None, which preserves the original prompt verbatim."""
    if caps is None:
        return ""
    lines = [
        f"ACTIVE BODY: you are controlling {caps.name} — a {caps.width}x{caps.height} pixel screen.",
        "YOUR AVAILABLE ACTIONS on this body are EXACTLY: "
        f"{', '.join(_actions_for(caps))}. Use ONLY these action names.",
    ]
    if caps.has_shell:
        lines.append(f"This body HAS a shell ({caps.shell_flavor}); the 'shell' action runs a command line.")
    else:
        lines.append("This body has NO shell — do everything through on-screen (vision) "
                     "actions; there is no 'shell' action.")
    if caps.keys:
        lines.append(f"Named keys for the 'key' action: {', '.join(sorted(caps.keys))}.")
    return "\n".join(lines) + "\n\n"


def build_system_prompt(caps=None):
    """The system prompt for a body: device preamble + the tuned base prose. The action's
    JSON shape is delivered separately as the tool schema (BrainAction, see decide), so the
    prompt no longer embeds a schema block."""
    return _device_preamble(caps) + _BASE_PROMPT


# Back-compat: the default (full desktop) prompt, still importable as SYSTEM_PROMPT.
SYSTEM_PROMPT = build_system_prompt(None)


def _load_key():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def decide(goal, observation, history=None, *, caps=None, model=None, effort="high",
           timeout=60, retries=2, escalation=None, context=None):
    """Return the next action as a dict: {thought, action, target?, text?, key?, visual_focus?}.

    Structured output (ADR-005): the Brain answers by filling a FORCED tool-call whose schema
    is `BrainAction`, and we VALIDATE the result through Pydantic here — so a malformed or
    incomplete reply cannot slip through; it becomes a StructuredError we retry on (up to
    `retries` extra attempts). Validity does NOT depend on the provider enforcing the schema.

    `effort` sets the reasoning level via OpenRouter's `reasoning.effort` ("high" = Think High,
    proven needed for reliable decisions; pass None/"" for a purely mechanical decider).
    """
    primary = model or MODEL
    system_prompt = build_system_prompt(caps)      # device-aware behavioral prose
    valid_actions = _actions_for(caps)             # ordered; also the injected `action` enum
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")

    hist_txt = "\n".join(f"- {h}" for h in (history or [])) or "(none yet)"
    escalation_block = f"\n\n{escalation}" if escalation else ""
    # App/OS OPERATING profile (profiles.py): authoritative how-to for the current app, so the
    # Brain knows its conventions (e.g. "in WhatsApp you send by TAPPING the Send button, not Enter").
    app_block = f"\n\nAUTHORITATIVE — how the current device and app WORK (follow this exactly):\n{context.strip()}" if context else ""
    user = (f"GOAL:\n{goal}\n\n"
            f"OBSERVATION (what is on screen now):\n{observation}\n\n"
            f"HISTORY (actions you have already taken):\n{hist_txt}"
            f"{escalation_block}{app_block}\n\n"
            f"Decide the single next action and return it as a JSON object matching the "
            f"decide_action schema.")
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user}]
    reasoning = {"effort": effort} if effort else {"enabled": False}

    def inject_enum(schema):               # constrain `action` to THIS body's verbs
        props = schema.get("properties", {})
        if "action" in props:
            props["action"]["enum"] = valid_actions
        return schema

    last_err = None
    for attempt in range(retries + 1):
        # Try the primary for its allotted attempts; the LAST attempt ESCAPES to the backup
        # model (ADR-005) — different weights (Google, not DeepSeek), so it survives a
        # weight-level degeneration that retrying the primary would just re-trigger.
        use_model = primary
        if attempt == retries and BACKUP_MODEL and BACKUP_MODEL != primary:
            use_model = BACKUP_MODEL
        try:
            act_obj, usage = structured_call(
                BrainAction, messages, model=use_model, api_key=key, reasoning=reasoning,
                max_tokens=8192, timeout=timeout, schema_name="decide_action",
                schema_transform=inject_enum,
                headers=_OR_HEADERS)
        except StructuredError as e:
            # Capture the raw provider body (carries a provider `finish_reason=error`, a
            # validation failure, etc.) so a recurring fault can be root-caused, then retry.
            last_err = e
            if runlog:
                runlog.record("decide-error",
                              f"attempt {attempt + 1}/{retries + 1} ({use_model}): {e}",
                              e.body if e.body is not None else str(e))
            continue

        action = act_obj.model_dump(exclude_none=True)
        if action.get("action") not in valid_actions:      # our guard on the injected enum
            last_err = f"action {action.get('action')!r} not in {valid_actions}"
            if runlog:
                runlog.record("decide-error",
                              f"attempt {attempt + 1}/{retries + 1}: {last_err}", action)
            continue

        if runlog:
            runlog.record("decide", user, json.dumps(action, ensure_ascii=False),
                          usage=usage, model=use_model)
        action["_usage"] = usage
        return action

    raise RuntimeError(
        f"Brain failed to return a valid action after {retries + 1} attempts: {last_err}")


# ---------------------------------------------------------------------------
# Embodiment selection + answer-only (ADR-006)
#
# Before the loop, the Brain picks its BODY + app PROFILES for a task (or no body, to answer
# directly). Both calls reuse the ADR-005 structured-output mechanism + the same model-fallback
# as decide(), factored into _structured_with_fallback so the retry/escape logic lives once.
# ---------------------------------------------------------------------------

def _structured_with_fallback(model_cls, messages, *, schema_name, reasoning, model=None,
                              max_tokens=4096, timeout=60, retries=2, err_kind="structured-error"):
    """Run structured_call with the ADR-005 model-fallback: the primary for its attempts, the
    LAST attempt escaping to BACKUP_MODEL (different weights → survives a weight-level
    degeneration). Returns (instance, usage, model_used); raises RuntimeError after all attempts
    fail. Error bodies are recorded to the transcript under `err_kind` for root-causing."""
    primary = model or MODEL
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")
    last_err = None
    for attempt in range(retries + 1):
        use_model = primary
        if attempt == retries and BACKUP_MODEL and BACKUP_MODEL != primary:
            use_model = BACKUP_MODEL
        try:
            inst, usage = structured_call(
                model_cls, messages, model=use_model, api_key=key, reasoning=reasoning,
                max_tokens=max_tokens, timeout=timeout, schema_name=schema_name,
                headers=_OR_HEADERS)
            return inst, usage, use_model
        except StructuredError as e:
            last_err = e
            if runlog:
                runlog.record(err_kind, f"attempt {attempt + 1}/{retries + 1} ({use_model}): {e}",
                              e.body if e.body is not None else str(e))
    raise RuntimeError(
        f"Brain {schema_name} call failed after {retries + 1} attempts: {last_err}")


class Embodiment(BaseModel):
    """The Brain's upfront embodiment choice for a task (ADR-006): which BODY to inhabit and
    which app PROFILES to load — or NO body at all (answer the goal directly). Elicited via
    response_format json_schema (ADR-005) and validated here through Pydantic. Semantic
    validation (device known, profiles under the device) happens in the loop's resolver."""

    device: str | None = Field(
        None, description="Which BODY to inhabit for this task: 'android' (a real Android "
                          "phone) or 'linux' (the Linux desktop container). Use null ONLY when "
                          "the task needs NO on-screen action and can be answered directly.")
    profiles: list[str] = Field(
        default_factory=list,
        description="Zero or more profile paths to load as knowledge, e.g. ['android/whatsapp']. "
                    "EVERY path must be under the chosen device (same first segment). An empty "
                    "list is fine (no extra app knowledge).")
    reason: str = Field(
        description="A brief English reason for this body + profile choice.")


class Answer(BaseModel):
    """A direct textual answer to a goal that needs no on-screen action (ADR-006)."""

    answer: str = Field(description="The answer to the GOAL, in clear English prose.")


_PICK_PROMPT = """You are the Brain of a computer-use agent, choosing HOW to embody a task
BEFORE you start. You cannot see any screen yet — you have only the GOAL and a CATALOG of the
available bodies and app profiles.

Choose:
- device: which BODY to inhabit for this GOAL — a body name from the catalog's `##` sections
  (e.g. "android" for the phone, "linux" for the desktop). Choose null ONLY when the GOAL is a
  pure question you can answer directly with NO on-screen action.
- profiles: zero or more profile paths from UNDER the chosen body's section (e.g.
  "android/whatsapp"). They give app knowledge to your Eyes and reasoning. Pick the ones
  relevant to the GOAL; an empty list is fine.
- reason: one short sentence on why.

Rules:
- Pick exactly ONE body (or null). EVERY profile must sit under that one body — never mix
  bodies (e.g. an "android/..." and a "linux/..." together).
- If the goal names an app that has a profile, pick that profile (prefer the most specific).
- Choose device=null ONLY when NO on-screen action is needed at all — a fact or answer you can
  give directly. If the task involves opening, tapping, typing, browsing, or messaging, pick a body.
- Return a SINGLE JSON object matching the embodiment schema — only the JSON, no prose, no markdown.
"""

_ANSWER_PROMPT = """You are answering a question directly — no computer, no screen, just your
own knowledge and reasoning. Give a clear, correct, concise answer to the GOAL. Return a SINGLE
JSON object matching the answer schema — only the JSON, no prose, no markdown."""


def select_embodiment(goal, catalog, *, model=None, timeout=60, retries=2):
    """Pick the task's embodiment (ADR-006): return an `Embodiment` (device + profiles + reason).

    Text-only — the GOAL plus the CATALOG (profiles/index.md), before any screenshot. Reuses the
    structured-output + model-fallback discipline (last attempt escapes to BACKUP_MODEL). Raises
    RuntimeError if no attempt yields a valid Embodiment. Semantic validity (device known,
    profiles under it) is the loop resolver's job, not this call's."""
    user = (f"GOAL:\n{goal}\n\n"
            f"CATALOG (available bodies and profiles):\n{catalog}\n\n"
            f"Choose the embodiment and return it as a JSON object matching the embodiment schema.")
    messages = [{"role": "system", "content": _PICK_PROMPT},
                {"role": "user", "content": user}]
    emb, usage, used = _structured_with_fallback(
        Embodiment, messages, schema_name="embodiment", reasoning={"effort": "high"},
        model=model, timeout=timeout, retries=retries, err_kind="embodiment-error")
    if runlog:
        runlog.record("embodiment", user,
                      json.dumps(emb.model_dump(), ensure_ascii=False), usage=usage, model=used)
    return emb


def answer(goal, *, model=None, timeout=60, retries=2):
    """Answer a no-body goal directly (ADR-006): one reasoned text answer, no loop. Reuses the
    structured transport with a trivial one-field schema (so it gets the same model-fallback);
    strict:false keeps it safe on reasoning models. Returns the answer string."""
    messages = [{"role": "system", "content": _ANSWER_PROMPT},
                {"role": "user", "content": f"GOAL:\n{goal}"}]
    ans, usage, used = _structured_with_fallback(
        Answer, messages, schema_name="answer", reasoning={"effort": "high"},
        model=model, timeout=timeout, retries=retries, err_kind="answer-error")
    if runlog:
        runlog.record("answer", goal, ans.answer, usage=usage, model=used)
    return ans.answer
