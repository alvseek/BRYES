"""BRYES Phase 2 — The Eyes (UI-TARS-1.5-7B via OpenRouter).

Two capabilities, both from screenshots:
  describe(image)              -> text report of what's on screen (for the Brain)
  locate(image, instruction)   -> pixel (x, y) of one described element (for the Hands)

Coordinate convention: UI-TARS-1.5 is Qwen2.5-VL based. It sees the image after a
`smart_resize` (sides rounded to multiples of 28, area clamped) and returns coords in
that space. We convert back with: actual = model_coord * original_dim / resized_dim.
"""
import base64
import io
import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

try:                       # optional transcript logger (no-op when a run isn't logging)
    import runlog
except ImportError:
    runlog = None

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "bytedance/ui-tars-1.5-7b"

IMAGE_FACTOR = 28
MIN_PIXELS = 3136
MAX_PIXELS = 2_116_800

GROUND_PROMPT = (
    "You are a precise GUI grounding model. Look at the screenshot and locate the "
    "single UI element described below. Respond with ONLY the click action in "
    "exactly this format and nothing else:\n"
    "click(start_box='(x,y)')\n\n"
    "Element to locate: {instruction}"
)

DESCRIBE_PROMPT = (
    "You are the eyes of a computer-use agent, reporting to a decision-maker who "
    "cannot see the screen. Describe the current screen concisely and factually:\n"
    "- the main window(s) and which app they are\n"
    "- the interactive elements available to act on (buttons, input fields, menus) "
    "- list them by their visible labels\n"
    "- the current state: window titles, and what any display or text field shows "
    "right now\n\n"
    "CRITICAL — report ONLY what is literally visible as pixels on the screen. Do NOT "
    "infer, compute, calculate, complete, or guess anything. Transcribe visible numbers "
    "and text EXACTLY as shown, character for character. If a display shows an "
    "expression or partial input with no result (e.g. a calculation that has not been "
    "evaluated yet), report it exactly and state plainly that no result is shown — NEVER "
    "fill in a value that is not on the screen.\n\n"
    "Do NOT suggest actions and do NOT give coordinates. Only report what is there."
)


def _load_key():
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def smart_resize(height, width, factor=IMAGE_FACTOR,
                 min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS):
    """Return (resized_height, resized_width) the model actually sees."""
    h_bar = max(factor, round(height / factor) * factor)
    w_bar = max(factor, round(width / factor) * factor)
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = math.floor(height / beta / factor) * factor
        w_bar = math.floor(width / beta / factor) * factor
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = math.ceil(height * beta / factor) * factor
        w_bar = math.ceil(width * beta / factor) * factor
    return h_bar, w_bar


def _ask(prompt, image_bytes, *, max_tokens, timeout):
    """Send one image+text chat turn to UI-TARS, return the text reply."""
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")
    b64 = base64.b64encode(image_bytes).decode()
    body = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
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
    return data["choices"][0]["message"]["content"].strip()


def describe(image_bytes, focus=None, *, timeout=60):
    """Return a text report of what is on screen, for the Brain to reason over.

    If `focus` is given (the Brain telling the Eyes what matters this step), the
    description concentrates on that area — detailed there, one line for everything
    else. Called with focus=None (e.g. the first step) it reports the whole screen.
    """
    prompt = DESCRIBE_PROMPT
    if focus:
        prompt += (
            f"\n\nFOCUS: concentrate on {focus}. Describe it in full detail — its "
            "current state, every visible label, and any values or text it shows right "
            "now (distinguish a live entry/input from a log of past results). Mention "
            "anything else on screen in at most one line."
        )
    result = _ask(prompt, image_bytes, max_tokens=512, timeout=timeout)
    if runlog:
        runlog.record("describe", f"focus: {focus or '(none)'}", result)
    return result


def locate(image_bytes, instruction, *, timeout=60):
    """Locate a UI element. Returns dict with pixel x/y plus diagnostics."""
    width, height = Image.open(io.BytesIO(image_bytes)).size
    rh, rw = smart_resize(height, width)
    content = _ask(GROUND_PROMPT.format(instruction=instruction),
                   image_bytes, max_tokens=128, timeout=timeout)

    nums = [int(n) for n in re.findall(r"-?\d+", content)]
    if len(nums) < 2:
        raise RuntimeError(f"could not parse a coordinate from: {content!r}")
    if len(nums) >= 4:                       # bbox -> center
        mx, my = (nums[0] + nums[2]) / 2, (nums[1] + nums[3]) / 2
    else:
        mx, my = nums[0], nums[1]

    ax = max(0, min(width - 1, round(mx * width / rw)))
    ay = max(0, min(height - 1, round(my * height / rh)))
    result = {
        "x": ax, "y": ay,
        "raw_model_coord": [mx, my],
        "resized_dims_wh": [rw, rh],
        "original_dims_wh": [width, height],
        "content": content,
    }
    if runlog:
        runlog.record("locate", f"instruction: {instruction}", content,
                      x=ax, y=ay, raw_model_coord=[mx, my])
    return result
