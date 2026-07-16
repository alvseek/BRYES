"""BRYES Phase 2 — The Eyes.

Two capabilities from screenshots, each on the model that does its job best:
  describe(image)            -> text report of the screen, via a general VLM
                                (Qwen2.5-VL-72B) that reads structure faithfully
  locate(image, instruction) -> pixel (x, y) of one element, via UI-TARS-1.5-7B, a
                                Qwen2.5-VL grounding fine-tune

Why two models: UI-TARS is Qwen2.5-VL specialized for grounding — great at locate, but
the fine-tune degraded free-form description (it confabulates results and flattens a
history/log into the current state). A general VLM describes faithfully.

Coordinate convention (locate only): UI-TARS-1.5 is Qwen2.5-VL based. It sees the image
after a `smart_resize` (sides rounded to multiples of 28, area clamped) and returns
coords in that space. We convert back: actual = model_coord * original_dim / resized_dim.
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
# locate() — GUI grounding (screenshot -> coordinates). UI-TARS = Qwen2.5-VL-7B tuned
# for grounding; excellent at pointing, weak at describing.
GROUND_MODEL = "bytedance/ui-tars-1.5-7b"
# describe() — faithful reading of the screen for the Brain. A general VLM (the larger,
# un-specialized sibling of UI-TARS' own backbone) that keeps its description ability.
DESCRIBE_MODEL = "qwen/qwen2.5-vl-72b-instruct"

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
    "- the interactive elements available to act on (buttons, input fields, menus), "
    "listed by their visible labels\n"
    "- the CURRENT state — the important part: clearly SEPARATE the active input/entry "
    "(what is being edited right now, INCLUDING when it is empty) from any HISTORY or "
    "log of PAST results/entries shown above or around it. State explicitly which text "
    "is the live entry and which is history.\n\n"
    "CRITICAL — report ONLY what is literally visible as pixels. Do NOT infer, compute, "
    "calculate, complete, or guess. Transcribe visible numbers and text EXACTLY as "
    "shown. If the active entry is empty or shows an un-evaluated expression, say so "
    "plainly. NEVER fill in a value that is not on screen, and NEVER present a past/"
    "history result as if it were the current entry.\n\n"
    "Do NOT suggest actions and do NOT give coordinates. Only report what is there."
)

DIFF_PROMPT = (
    "You are comparing two screenshots of the SAME user interface: the FIRST image is "
    "BEFORE an action, the SECOND is AFTER it. Describe ONLY what CHANGED from BEFORE to "
    "AFTER — specifically: elements that appeared/disappeared, moved, or changed their "
    "text/value/state; a dialog or menu opening or closing; a selection or focus change. "
    "If nothing meaningful changed, say exactly 'No significant change.' Report only what "
    "is literally different in the pixels — do NOT infer intent or describe unchanged parts."
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


def _ask(prompt, images, *, model, max_tokens, timeout):
    """Send one text+image(s) chat turn to `model` on OpenRouter, return the text reply.

    `images` is a single PNG (bytes) or several (list[bytes], sent in order) — the
    multi-image form powers diff() (BEFORE + AFTER frames in one call).
    """
    key = _load_key()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not found (check BRYES/.env)")
    if isinstance(images, (bytes, bytearray)):
        images = [images]
    content = [{"type": "text", "text": prompt}]
    for img in images:
        b64 = base64.b64encode(img).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}})
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": content}],
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


def describe(image_bytes, focus=None, expect=None, *, timeout=60):
    """Return a text report of what is on screen, for the Brain to reason over.

    Two optional prospective modifiers the Brain sets on its last action:
      - `focus`  — a SECTION/REGION of the screen (spatial: WHERE to look). The report
        concentrates there — detailed in that region, one line for everything else.
      - `expect` — the thing the Brain wants checked AFTER its last action (WHAT to look
        at). The report opens with `VERIFICATION: <the actual state of that thing>` — a
        grounded description, NOT a verdict; the Brain compares it to what it expected.
    Called with both None (e.g. the first step) it reports the whole screen.
    """
    prompt = DESCRIBE_PROMPT
    if focus:
        prompt += (
            f"\n\nFOCUS: a SECTION/REGION of the screen to concentrate on: {focus}. "
            "Describe that region in full detail — its current state, every visible "
            "label, and any values or text it shows right now (distinguish a live "
            "entry/input from a log of past results). Mention anything else on screen in "
            "at most one line. (FOCUS is only WHERE to look — it is NOT a claim to check.)"
        )
    if expect:
        prompt += (
            "\n\nThe decision-maker (who cannot see the screen) is checking on this after "
            "their last action: \"" + expect + "\". Report the ACTUAL current state of that "
            "specific thing, exactly as you see it in the pixels. Begin your reply with "
            "'VERIFICATION: <precisely what is shown regarding it right now>'. Do NOT judge "
            "whether it matches, and do NOT say verified/failed — just report what IS there "
            "(the decision-maker will compare). Then continue with the normal description."
        )
    # 1024 (not 512): headroom for the VERIFY verdict + a busy-screen description without
    # truncating. NOT 8192 like decide() — describe is a VLM emitting visible text (no hidden
    # reasoning tokens to budget), and the prompt keeps it concise; a big ceiling would only
    # invite the verbose describe that blurred the Brain's context (the 2026-07-13 regression).
    result = _ask(prompt, image_bytes, model=DESCRIBE_MODEL, max_tokens=1024,
                  timeout=timeout)
    if runlog:
        runlog.record("describe",
                      f"focus: {focus or '(none)'} | expect: {expect or '(none)'}", result)
    return result


def diff(prev_bytes, cur_bytes, focus=None, *, timeout=60):
    """One VLM call over BOTH frames -> a text account of what changed (Phase 5, Layer 3).

    EXPENSIVE: two images in a single call, heavier than a describe. The loop runs it only
    when the Brain sets request_diff (it is stuck / an effect is subtle). `focus` (optional)
    narrows the comparison to a region.
    """
    prompt = DIFF_PROMPT
    if focus:
        prompt += f"\n\nConcentrate the comparison on this region: {focus}."
    result = _ask(prompt, [prev_bytes, cur_bytes], model=DESCRIBE_MODEL, max_tokens=1024,
                  timeout=timeout)
    if runlog:
        runlog.record("diff", f"focus: {focus or '(none)'}", result)
    return result


def locate(image_bytes, instruction, *, timeout=60):
    """Locate a UI element. Returns dict with pixel x/y plus diagnostics."""
    width, height = Image.open(io.BytesIO(image_bytes)).size
    rh, rw = smart_resize(height, width)
    content = _ask(GROUND_PROMPT.format(instruction=instruction),
                   image_bytes, model=GROUND_MODEL, max_tokens=128, timeout=timeout)

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
