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

SYSTEM_PROMPT = """You are the Brain of a vision-based computer-use agent.
A separate component (the Eyes) can locate any on-screen element you name, and the
Hands can click, double-click, right-click, hover, scroll, drag, type, and press keys.
Given the GOAL, a text description of what is currently on screen (OBSERVATION), and the
HISTORY of prior steps, decide the SINGLE next action.

The HISTORY lists the actions you have ALREADY taken (most recent last). Judge the
current situation from the OBSERVATION — not from memory of past screens.

Rules:
- WRITE IN ENGLISH: reason and fill EVERY field of your JSON reply in English only,
  whatever the GOAL wording or the on-screen language.
- FOLLOW THE OBSERVED STATE: your understanding of what is on screen right now MUST come
  from the current OBSERVATION, read EXACTLY as written — never from memory, assumption,
  or what you expected your last action to produce. Before choosing an action, evaluate
  three things in order: (a) what the OBSERVATION shows right now, (b) what you have
  already done (HISTORY), and (c) what still remains to reach the GOAL. Decide from that
  comparison. If the OBSERVATION contradicts what you expected, trust the OBSERVATION.
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
- FOCUS THE EYES, SPECIFICALLY: set "focus" to the precise element or region whose EXACT
  current state you need for your next decision and to verify your last action — e.g. the
  current input/entry field and exactly what it contains right now, or the specific
  control you are about to use — not just the whole app or window. The more specific and
  contextual the focus, the more accurately the Eyes report the state you must act on.
  Keep the focus on the relevant area across steps, moving it only when the task moves to
  a new area.
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
  "destination" — for sliders, moving items). Plus "type", "key", "wait", "screenshot", "done", "fail".
- WAIT FOR LOADING, DON'T GUESS. If the screen is still loading (a spinner, or a blank/partial
  page with content not yet rendered), do NOT act on it or finish — use action "wait" and set
  "seconds" to how long to pause before looking again (e.g. 2-4s for a heavy web page, more if
  it is very slow). Waiting does not touch the screen; it just lets the content appear so your
  NEXT observation is accurate.
- SCREENSHOT TO CAPTURE. Use action "screenshot" to save the current screen as an output you
  were asked to produce (to record or capture what is shown). It does not change the screen.
  To capture content that spans multiple screens (a long or infinite results list), "scroll"
  and "screenshot" repeatedly so each part is saved.
- Choose exactly ONE next action that makes real progress toward the goal.
- If the OBSERVATION shows the goal is already satisfied, use action "done".
- If you are truly stuck or the goal is impossible, use action "fail".
- Respond with ONLY a JSON object, no prose, no markdown fences.

JSON schema:
{
  "thought": "<reasoning in English, with NO quotation marks inside: what the screen shows now, progress vs the GOAL, and the next action>",
  "action": "click" | "double_click" | "right_click" | "hover" | "scroll" | "drag" | "type" | "key" | "wait" | "screenshot" | "done" | "fail",
  "target": "<element description; required for click/double_click/right_click/hover/scroll, and the START point of a drag>",
  "destination": "<element description; the drop point, required for drag>",
  "direction": "<'up' or 'down'; required for scroll>",
  "seconds": "<number of seconds to pause; required for wait>",
  "text": "<text to type into the CURRENTLY-FOCUSED field; required for type>",
  "key": "<key name like Return, Escape, Tab; required when action is key>",
  "focus": "<optional: what the Eyes should concentrate on next>"
}"""

VALID_ACTIONS = {"click", "double_click", "right_click", "hover", "scroll", "drag",
                 "type", "key", "wait", "screenshot", "done", "fail"}


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


def decide(goal, observation, history=None, *, model=None, effort="high",
           timeout=60, retries=2):
    """Return the next action as a dict: {thought, action, target?, text?, key?, focus?}.

    `effort` sets DeepSeek V4's thinking mode via OpenRouter's `reasoning.effort`
    ("high" = Think High, proven needed for reliable decisions). Pass None/"" to
    disable reasoning for a purely mechanical decider.

    Retries on a malformed / empty JSON reply (a reasoning model occasionally emits
    invalid JSON — e.g. an unescaped quote inside a string) instead of crashing the
    whole run; the retry asks explicitly for one strict JSON object.
    """
    model = model or MODEL
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")

    hist_txt = "\n".join(f"- {h}" for h in (history or [])) or "(none yet)"
    user_base = (f"GOAL:\n{goal}\n\n"
                 f"OBSERVATION (what is on screen now):\n{observation}\n\n"
                 f"HISTORY (actions you have already taken):\n{hist_txt}\n\n"
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
                {"role": "system", "content": SYSTEM_PROMPT},
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

        choice = data["choices"][0]
        content = choice["message"].get("content")
        try:
            if not content:
                raise ValueError(
                    f"empty content (finish_reason={choice.get('finish_reason')})")
            action = _extract_json(content)
            if action.get("action") not in VALID_ACTIONS:
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
