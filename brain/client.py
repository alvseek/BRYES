"""BRYES Phase 3 — The Brain.

Decides the single next action given the goal, a TEXT description of the screen,
and the history so far. Uses DeepSeek V4 via OpenRouter.

The Brain is text-only by design: it reasons about elements *by description*
(e.g. "the + button") and never about pixels. The Eyes (Phase 2) turn those
descriptions into coordinates; the Hands (Phase 1) execute them.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

try:                       # optional transcript logger (no-op when a run isn't logging)
    import runlog
except ImportError:
    runlog = None

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# qwen3.6-flash: best value in the 5-model browser-search bake-off (4 steps, clean done,
# ~$0.19/$1.13 per M, 1M context). Beat v4-pro AND minimax-m3 on both cost and capability
# once the harness was fixed (VLM describe + type-just-types + actions-only history).
# Fallbacks if it underperforms elsewhere: tencent/hy3 (256k ctx) or deepseek-v4-flash
# (cheapest). (Do NOT use legacy deepseek-chat / deepseek-reasoner — retire 2026-07-24.)
MODEL = "qwen/qwen3.6-flash"

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
- WRITE IN ENGLISH: reason and fill EVERY field of your JSON reply in English only,
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
  is the Eyes reporting the ACTUAL state of what you set in "expect" (a grounded reading of
  the pixels, not a verdict). Compare it to what you expected. If it differs, your action
  MAYBE didn't do what you thought — rethink or adapt (re-read the state, try a different
  target or action). If it matches, proceed.
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
- FOCUS THE EYES ON A REGION (WHERE): set "focus" to the SECTION/REGION of the screen
  whose EXACT current state you need next — e.g. the current input/entry field, a specific
  control, or a panel — not the whole app or window. "focus" only steers WHERE the Eyes
  look; it is NOT a claim to check (that is "expect"). The more specific and contextual the
  region, the more accurately the Eyes report the state you must act on. Keep the focus on
  the relevant area across steps, moving it only when the task moves to a new area.
- PREDICT THE RESULT (EXPECT): whenever you take an action that SHOULD change the screen,
  set "expect" to the state you predict will be TRUE right afterward, phrased as an
  ABSOLUTE, NAMEABLE target-state (e.g. "the Settings app is open", "the address bar shows
  example.com") — NOT a relative one ("something new appeared"). Next step the Eyes REPORT
  the actual state of that thing back to you (the OBSERVATION begins "VERIFICATION: ..."),
  for you to compare against what you expected.
- WHEN STUCK, ASK FOR A DIFF (EXPENSIVE): if you cannot tell what your last action did —
  the OBSERVATION is ambiguous, or the VERIFICATION report doesn't match what you expected —
  set "request_diff": true. Next step you will receive a precise "CHANGES SINCE YOUR LAST
  ACTION" account. It costs a SLOW, EXPENSIVE extra vision pass, so use it sparingly —
  only when genuinely stuck, never as a routine check.
- TEXT ENTRY: the "type" action sends text to whatever field is currently FOCUSED — it
  does NOT move focus. To enter text: first "click" the field to focus it, then "type".
  To REPLACE a field's existing contents (e.g. an address bar with a URL in it): "click"
  it, then "key" with ctrl+a to select all, then "type" — the typed text replaces the
  selection. To append at the cursor, just "type".
- PICK THE RIGHT ACTION. Point actions name a "target" by description (the Eyes turn it
  into pixels): "click" (left-click), "double_click" (open/activate an item), "right_click"
  (open a context menu), "hover" (move the pointer ONTO a target to reveal a menu/tooltip,
  without clicking), "scroll" (wheel-scroll at a target — set "direction" to "up" or "down",
  e.g. to bring off-screen content into view), "drag" (press on "target" and release on
  "destination" — for sliders, moving items). Plus "type", "key", "wait", "screenshot", "shell", "done", "fail".
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
- Respond with ONLY a JSON object, no prose, no markdown fences.
"""

_JSON_SCHEMA = """JSON schema:
{
  "thought": "<reasoning in English, with NO quotation marks inside: what the screen shows now, progress vs the GOAL, and the next action>",
  "action": __ACTION_ENUM__,
  "target": "<element description; required for click/double_click/right_click/hover/scroll, and the START point of a drag>",
  "destination": "<element description; the drop point, required for drag>",
  "direction": "<'up' or 'down'; required for scroll>",
  "seconds": "<number of seconds to pause; required for wait>",
  "text": "<text to type into the CURRENTLY-FOCUSED field; required for type>",
  "key": "<key name like Return, Escape, Tab; required when action is key>",
  "command": "<the full shell command line to run; required for shell>",
  "timeout": "<optional seconds for shell, up to 300; default 30>",
  "stdin": "<optional text to feed the shell command's standard input>",
  "expect": "<optional: the specific target-state you predict after this action, phrased ABSOLUTE/nameable (e.g. 'the Settings app is open'); next step the Eyes REPORT that thing's actual state ('VERIFICATION: ...') for you to compare>",
  "focus": "<optional: a SECTION/REGION of the screen the Eyes should concentrate on next (spatial — WHERE to look)>",
  "request_diff": "<optional true: request an EXPENSIVE, SLOW precise before/after visual diff next step — set ONLY when an effect is subtle or you are stuck; NOT routinely>"
}"""

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
    """Full system prompt for a body: device preamble + the tuned base prose + a JSON
    schema whose `action` enum lists only this body's actions."""
    enum = " | ".join(f'"{a}"' for a in _actions_for(caps))
    return _device_preamble(caps) + _BASE_PROMPT + "\n" + _JSON_SCHEMA.replace("__ACTION_ENUM__", enum)


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


def _extract_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def decide(goal, observation, history=None, *, caps=None, model=None, effort="high",
           timeout=60, retries=2, escalation=None):
    """Return the next action as a dict: {thought, action, target?, text?, key?, focus?}.

    `effort` sets DeepSeek V4's thinking mode via OpenRouter's `reasoning.effort`
    ("high" = Think High, proven needed for reliable decisions). Pass None/"" to
    disable reasoning for a purely mechanical decider.

    Retries on a malformed / empty JSON reply (a reasoning model occasionally emits
    invalid JSON — e.g. an unescaped quote inside a string) instead of crashing the
    whole run; the retry asks explicitly for one strict JSON object.
    """
    model = model or MODEL
    system_prompt = build_system_prompt(caps)      # device-aware: verbs from caps
    valid_actions = set(_actions_for(caps))
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")

    hist_txt = "\n".join(f"- {h}" for h in (history or [])) or "(none yet)"
    escalation_block = f"\n\n{escalation}" if escalation else ""
    user_base = (f"GOAL:\n{goal}\n\n"
                 f"OBSERVATION (what is on screen now):\n{observation}\n\n"
                 f"HISTORY (actions you have already taken):\n{hist_txt}"
                 f"{escalation_block}\n\n"
                 f"Decide the single next action as JSON.")

    last_err = None
    for attempt in range(retries + 1):
        user = user_base
        if attempt:                       # a previous try returned unparseable JSON
            user += ("\n\nYOUR PREVIOUS REPLY WAS NOT VALID JSON. Reply with exactly ONE "
                     "strict JSON object and nothing else. Do NOT put unescaped quotation "
                     "marks inside any string value.")
        body = {
            "model": model,
            "temperature": 0,
            # v4 is a reasoning model. Think High is enabled (effort="high") — proven
            # needed for reliable next-action decisions. Reasoning tokens are hidden but
            # count against max_tokens, so the ceiling is raised to leave room for the
            # trace + the JSON; too low re-introduces the content:null truncation.
            # (Use the single nested `reasoning` form — reasoning_effort AND
            #  reasoning.effort together is an HTTP 400.)
            "reasoning": {"effort": effort} if effort else {"enabled": False},
            "max_tokens": 8192,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
        }
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/alvseek/BRYES",
                "X-Title": "BRYES",
            },
            method="POST",
        )
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"OpenRouter HTTP {e.code}: {e.read().decode()[:400]}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # Network stall / timeout / reset on the Brain call. Unlike ContainerDevice this
            # had NO retry, so a dropped or timed-out connection hung/crashed the whole loop
            # (observed 2026-07-16: a step stalled in decide, after describe completed). Back
            # off and retry via the outer loop instead. (A genuinely slow-but-alive reasoning
            # response is a latency matter, not this error path.)
            last_err = e
            time.sleep(1.0 * (attempt + 1))
            continue

        choice = data["choices"][0]
        content = choice["message"].get("content")
        try:
            if not content:
                raise ValueError(
                    f"empty content (finish_reason={choice.get('finish_reason')})")
            action = _extract_json(content)
            if action.get("action") not in valid_actions:
                raise ValueError(f"invalid action in {content!r}")
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            continue                       # retry with the strict-JSON nudge

        if runlog:
            runlog.record("decide", user, content, usage=data.get("usage"))
        action["_usage"] = data.get("usage")
        return action

    raise RuntimeError(
        f"Brain failed to return valid JSON after {retries + 1} attempts: {last_err}")
