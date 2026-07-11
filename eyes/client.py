"""BRYES Phase 2 — The Eyes.

A grounding client: screenshot + a target description in, pixel coordinate out.
Uses UI-TARS-1.5-7B (a GUI-grounding model) via OpenRouter.

Key detail — the coordinate convention:
  UI-TARS-1.5 is Qwen2.5-VL based. It "sees" the image after a `smart_resize`
  (each side rounded to a multiple of 28, area clamped between MIN/MAX pixels)
  and returns coordinates in THAT resized space. We convert back to real pixels:
      actual = model_coord * original_dim / resized_dim
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

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "bytedance/ui-tars-1.5-7b"

# Qwen2.5-VL smart_resize parameters (UI-TARS defaults).
IMAGE_FACTOR = 28
MIN_PIXELS = 3136          # 56*56
MAX_PIXELS = 2_116_800     # ~1920x1102; our 1280x800 stays untouched (just 28-rounded)

GROUND_PROMPT = (
    "You are a precise GUI grounding model. Look at the screenshot and locate the "
    "single UI element described below. Respond with ONLY the click action in "
    "exactly this format and nothing else:\n"
    "click(start_box='(x,y)')\n\n"
    "Element to locate: {instruction}"
)


def _load_key():
    """Read OPENROUTER_API_KEY from BRYES/.env (never logged)."""
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


def locate(image_bytes, instruction, *, timeout=60):
    """Locate a UI element. Returns dict with pixel x/y plus diagnostics."""
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")

    width, height = Image.open(io.BytesIO(image_bytes)).size
    rh, rw = smart_resize(height, width)
    b64 = base64.b64encode(image_bytes).decode()

    body = {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 128,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": GROUND_PROMPT.format(instruction=instruction)},
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

    content = data["choices"][0]["message"]["content"]
    nums = [int(n) for n in re.findall(r"-?\d+", content)]
    if len(nums) < 2:
        raise RuntimeError(f"could not parse a coordinate from: {content!r}")
    if len(nums) >= 4:                       # bbox -> center
        mx, my = (nums[0] + nums[2]) / 2, (nums[1] + nums[3]) / 2
    else:
        mx, my = nums[0], nums[1]

    ax = max(0, min(width - 1, round(mx * width / rw)))
    ay = max(0, min(height - 1, round(my * height / rh)))
    return {
        "x": ax, "y": ay,
        "raw_model_coord": [mx, my],
        "resized_dims_wh": [rw, rh],
        "original_dims_wh": [width, height],
        "content": content.strip(),
        "usage": data.get("usage"),
    }
