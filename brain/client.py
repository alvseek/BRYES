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

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# v4-flash: cheap + 1M context, enough for single-step decisions.
# Switch to "deepseek/deepseek-v4-pro" if the Brain makes weak calls.
# (Do NOT use the legacy deepseek-chat / deepseek-reasoner — they retire 2026-07-24.)
MODEL = "deepseek/deepseek-v4-flash"

SYSTEM_PROMPT = """You are the Brain of a vision-based computer-use agent.
A separate component (the Eyes) can locate any on-screen element you name, and the
Hands can click, type, and press keys. Given the GOAL, a text description of what is
currently on screen (OBSERVATION), and the HISTORY of actions already taken, decide
the SINGLE next action.

Rules:
- Refer to elements by description (e.g. "the Submit button", "the + button").
  NEVER output pixel coordinates - the Eyes handle pixels.
- Choose exactly ONE next action that makes real progress toward the goal.
- If the OBSERVATION shows the goal is already satisfied, use action "done".
- If you are truly stuck or the goal is impossible, use action "fail".
- Respond with ONLY a JSON object, no prose, no markdown fences.

JSON schema:
{
  "thought": "<one sentence of reasoning>",
  "action": "click" | "type" | "key" | "done" | "fail",
  "target": "<element description; required for click, optional for type>",
  "text": "<text to type; required when action is type>",
  "key": "<key name like Return, Escape, Tab; required when action is key>"
}"""

VALID_ACTIONS = {"click", "type", "key", "done", "fail"}


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


def decide(goal, observation, history=None, *, model=MODEL, timeout=60):
    """Return the next action as a dict: {thought, action, target?, text?, key?}."""
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")

    hist_txt = "\n".join(f"- {h}" for h in (history or [])) or "(none yet)"
    user = (f"GOAL:\n{goal}\n\n"
            f"OBSERVATION (what is on screen now):\n{observation}\n\n"
            f"HISTORY (actions already taken):\n{hist_txt}\n\n"
            f"Decide the single next action as JSON.")

    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": 300,
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

    content = data["choices"][0]["message"]["content"]
    action = _extract_json(content)
    if action.get("action") not in VALID_ACTIONS:
        raise RuntimeError(f"Brain returned invalid action: {content!r}")
    action["_usage"] = data.get("usage")
    return action
