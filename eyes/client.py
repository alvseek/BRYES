"""BRYES — The Eyes.

Screenshot -> text/coords, each capability on the model that does its job best:
  describe(img, focus, expect, careful) -> text report (two-mode foveal, ADR-004):
       OVERVIEW (no focus) = downscaled gist on qwen3-vl-8b; TRIM (focus) = 72B box() ->
       crop -> q3-8b describes the crop. `careful` re-reads a crop on the 72B (recheck rung).
  box(img, target)         -> (x1,y1,x2,y2) bounding box for the TRIM crop, via Qwen2.5-VL-72B
       (the only reliable boxer; absolute coords at any resolution) — or None (-> full frame).
  locate(img, instruction) -> pixel (x, y) of one element, via UI-TARS-1.5-7B (grounding).
  diff(prev, cur)          -> 2-image "what changed" account, via the 72B (request_diff rung).

Why the split: UI-TARS (a grounding fine-tune) is great at locate/pointing but confabulates
and flattens history when asked to describe; a general VLM describes faithfully. The fast
q3-8b is faithful ONLY on trimmed crops (a small clean crop has little to hallucinate), so the
72B stays the authoritative Eyes for boxing + careful re-reads + diffs. Latency is
output-length-bound, so describe says less about less (ADR-004). Thinking off on describe/box.

Coordinate conventions: locate (UI-TARS) returns coords in the `smart_resize` space (sides
rounded to multiples of 28, area clamped) -> converted back: actual = model*orig/resized.
box (Qwen2.5-VL) returns ABSOLUTE pixels at any resolution (validated to 4M px) -> used as-is.
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
# describe() — DEFAULT crop/overview describer: the fast qwen3-vl-8b. The bake-off proved it
# faithful on TRIMMED crops (no confab; read Rp759 vs struck Rp799; hard calc crops clean) at
# ~0.3-1.4s — a small clean crop has little to hallucinate. NOT used on full busy frames
# (where small VLMs flatten/confabulate); the trim is what keeps it honest.
DESCRIBE_MODEL = "qwen/qwen3-vl-8b-instruct"
# box() — bounding box for a named region (powers describe()'s TRIM mode). The 72B was the
# ONLY model that boxed reliably in the bake-off, including small targets; UI-TARS and the
# small VLMs only point / mislocate. Stays on 72B — the authoritative Eyes.
BOX_MODEL = "qwen/qwen2.5-vl-72b-instruct"
# careful describe — the recheck rung (ADR-004): re-read a crop on the 72B when the fast
# q3-8b read is doubted (an expect-mismatch). Same model as BOX_MODEL, distinct role.
CAREFUL_MODEL = "qwen/qwen2.5-vl-72b-instruct"

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

BOX_PROMPT = (
    "The image is {w}x{h} pixels. Return the bounding box of {target}. "
    "Respond with ONLY four integers in absolute pixel coordinates, comma-separated, "
    "as x1,y1,x2,y2 (top-left corner then bottom-right corner). Nothing else."
)

# OVERVIEW mode (describe with NO focus): a downscaled full frame -> a coarse gist. Positive-
# framed (telling a model what NOT to read primes it to read exactly that); the eye-catching
# salience is a FEATURE — it is the cue that tells the Brain where to `focus` next.
OVERVIEW_PROMPT = (
    "You are the eyes of a computer-use agent taking a first quick glance at the screen for a "
    "decision-maker who cannot see it. Give a brief, high-level overview — the way a person "
    "would glancing at a monitor:\n"
    "- What environment you are in (the OS / desktop).\n"
    "- What apps, windows, or components are showing — and anything visually interesting about each.\n"
    "- Anything generally eye-catching that stands out.\n"
    "This is a glance, not a careful read: capture the gist and what stands out; leave exact "
    "values and full text for a later focused look."
)

# TRIM mode (describe WITH focus): the frame is already cropped to the focus region, so the
# model only sees what matters -> read it faithfully. Generic across domains (calc display,
# a web form, a marketplace price). `focus` hint + `expect` VERIFICATION are appended per call.
CROP_PROMPT = (
    "This image is a cropped region of a computer screen (a focused area to look at closely). "
    "Report exactly what is in it, factually:\n"
    "- transcribe all visible text, numbers, labels, and prices EXACTLY as shown\n"
    "- distinguish any active/live/current value from any history/past/secondary value "
    "(e.g. a live entry vs a past result; a current price vs a struck-through original)\n"
    "Do NOT infer, compute, complete, or guess anything not literally visible. Report only what is there."
)

OVERVIEW_SCALE = 0.5   # downscale factor for the OVERVIEW gist (calibrated in Step 2.3)
CROP_PAD = 0.15        # TRIM crop padding: +15% of the box per side (clip-safety)


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


# Force thinking OFF on perception calls: measured 14x latency for zero accuracy gain
# (bake-off). Passed to _ask by describe()/box(); harmless no-op on the non-thinking
# instruct models we use, but future-proofs a swap to a thinking-capable VLM.
NO_THINK = {"enabled": False}


def _ask(prompt, images, *, model, max_tokens, timeout, reasoning=None):
    """Send one text+image(s) chat turn to `model` on OpenRouter, return the text reply.

    `images` is a single PNG (bytes) or several (list[bytes], sent in order) — the
    multi-image form powers diff() (BEFORE + AFTER frames in one call). `reasoning` is an
    optional OpenRouter reasoning-control dict (e.g. NO_THINK to force thinking off) —
    describe/box pass it, since reasoning only adds latency to a perception call.
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
    if reasoning is not None:
        body["reasoning"] = reasoning
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
    # A rate-limit / provider error can come back as HTTP 200 with an {"error": ...} body
    # (no "choices"). Surface it as a RuntimeError instead of a bare KeyError, so callers
    # that degrade on RuntimeError (box() -> full-frame fallback) handle it cleanly.
    if not data.get("choices"):
        raise RuntimeError(f"OpenRouter response had no choices: {str(data)[:400]}")
    return data["choices"][0]["message"]["content"].strip()


def _downscale(image_bytes, scale):
    """PNG bytes of the frame scaled by `scale` (e.g. 0.5). For the OVERVIEW gist — fewer
    pixels, cheaper prefill; naming windows needs no acuity. scale>=1 returns it unchanged."""
    if scale >= 1.0:
        return image_bytes
    im = Image.open(io.BytesIO(image_bytes))
    w, h = im.size
    im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _crop(image_bytes, box_xyxy, pad):
    """PNG bytes of the frame cropped to box_xyxy, expanded by `pad` (fraction of the box's
    own width/height) on each side and clamped to the frame — clip-safety for a box that
    slightly under-shoots the target. The crop stays FULL-resolution (acuity by trimming,
    not shrinking)."""
    im = Image.open(io.BytesIO(image_bytes))
    w, h = im.size
    x1, y1, x2, y2 = box_xyxy
    dx = (x2 - x1) * pad
    dy = (y2 - y1) * pad
    x1 = max(0, int(x1 - dx)); y1 = max(0, int(y1 - dy))
    x2 = min(w, int(x2 + dx)); y2 = min(h, int(y2 + dy))
    buf = io.BytesIO()
    im.crop((x1, y1, x2, y2)).save(buf, format="PNG")
    return buf.getvalue()


def _expect_block(expect):
    """The VERIFICATION rider (Phase 5 / ADR-003): the Eyes REPORT the actual state of what
    the Brain set in `expect` — a grounded reading, NOT a verdict. The Brain compares."""
    return (
        "\n\nThe decision-maker (who cannot see the screen) is checking on this after their "
        "last action: \"" + expect + "\". Report the ACTUAL current state of that specific "
        "thing, exactly as you see it in the pixels. Begin your reply with 'VERIFICATION: "
        "<precisely what is shown regarding it right now>'. Do NOT judge whether it matches, "
        "and do NOT say verified/failed — just report what IS there (the decision-maker will "
        "compare). Then continue with the normal description."
    )


def describe(image_bytes, focus=None, expect=None, *, careful=False, timeout=60):
    """A text report of what is on screen, for the Brain to reason over. Two modes (ADR-004,
    foveal vision): describe latency is output-length-bound, so we say less about less.

      - OVERVIEW (no `focus`): a DOWNSCALED full frame -> a coarse gist (environment / apps /
        anything eye-catching). Cheap; the salience tells the Brain where to `focus` next.
      - TRIM (`focus` set): 72B box() the named region -> crop (+15% pad) -> describe the CROP
        at full resolution. Fast AND faithful (a small clean crop has little to hallucinate).

    `expect` (which the Brain only sets WITH `focus`) rides the crop as a VERIFICATION report.
    `careful=True` is the recheck rung: do the crop/full describe on the 72B (CAREFUL_MODEL)
    instead of the fast q3-8b — for when a q3-8b read is doubted. Box always uses 72B.

    Robustness: an unparseable box() (None) -> describe the full frame (the only fallback).
    Defensive: `expect` without `focus` violates the Brain contract -> full frame + verify.
    """
    model = CAREFUL_MODEL if careful else DESCRIBE_MODEL

    if not focus and not expect:
        # OVERVIEW — downscaled gist.
        result = _ask(OVERVIEW_PROMPT, _downscale(image_bytes, OVERVIEW_SCALE),
                      model=model, max_tokens=1024, timeout=timeout, reasoning=NO_THINK)
        mode = f"overview x{OVERVIEW_SCALE:g}"
    else:
        # TRIM (focus) or the defensive full-frame path (expect without focus / box miss).
        img = image_bytes
        cropped = False
        if focus:
            b = box(image_bytes, focus, timeout=timeout)
            if b is not None:
                img = _crop(image_bytes, b, CROP_PAD)
                cropped = True
        if cropped:
            prompt = CROP_PROMPT + f"\n\nThis crop is the region: {focus}."
            mode = "trim"
        else:
            # No usable crop: full frame with the classic describe prompt (+ focus hint).
            prompt = DESCRIBE_PROMPT
            if focus:
                prompt += (f"\n\nFOCUS: concentrate on this region: {focus}. Describe it in "
                           "full detail; mention anything else in at most one line.")
            mode = "full(box-miss)" if focus else "full(expect-no-focus)"
        if expect:
            prompt += _expect_block(expect)
        result = _ask(prompt, img, model=model, max_tokens=1024, timeout=timeout,
                      reasoning=NO_THINK)

    if runlog:
        runlog.record("describe",
                      f"mode: {mode}{' careful' if careful else ''} | "
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
    # The 72B (CAREFUL_MODEL), NOT the fast q3-8b: request_diff is the TOP escalation rung
    # (the Brain is stuck), so it runs on the authoritative Eyes. No reasoning param -> the
    # 72B's non-thinking default. Whether a *thinking* VLM reads 2-image changes better HERE
    # (this rung can afford the latency, unlike every-step describe) is untested — see backlog.
    result = _ask(prompt, [prev_bytes, cur_bytes], model=CAREFUL_MODEL, max_tokens=1024,
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


def box(image_bytes, target, *, timeout=60):
    """Return an (x1, y1, x2, y2) absolute-pixel bounding box for a named on-screen
    region, or None if the model didn't return a usable box.

    Powers describe()'s TRIM mode: box a focus region -> crop -> describe the crop. Uses
    the 72B general VLM (BOX_MODEL) — the ONLY model that boxed reliably in the bake-off,
    including small targets (UI-TARS and the small VLMs only point / mislocate).

    Coordinate convention: Qwen2.5-VL emits ABSOLUTE pixel coordinates (unlike UI-TARS'
    resized-space, which is why locate() rescales via smart_resize), so we take them as-is.
    VALIDATED at BOTH 1280x800 and 2560x1600 (4.1M px, above the model's ~2.1M-px clamp):
    raw coords land dead-on at both — the model returns absolute even when it internally
    downscales, so NO smart_resize conversion or pre-scale is needed. (Step 1.2, 2026-07-16.)

    Returns None (not an exception) on an unparseable or non-rectangular reply, so the caller
    (describe's TRIM path) can fall back to describing the full frame. This is the ONLY
    fallback — no geometric "is this box wrong" heuristics (a confidently-wrong box can't be
    caught by geometry; 72B's measured accuracy + the recheck/request_diff ladder cover that).
    """
    width, height = Image.open(io.BytesIO(image_bytes)).size
    try:
        content = _ask(BOX_PROMPT.format(w=width, h=height, target=target),
                       image_bytes, model=BOX_MODEL, max_tokens=128, timeout=timeout,
                       reasoning=NO_THINK)
    except (RuntimeError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
        # A transient boxing failure (rate-limit / network) is a box-miss, not a crash:
        # return None so describe()'s TRIM path degrades to a full-frame describe this step.
        if runlog:
            runlog.record("box", f"target: {target}", f"ERROR: {e}", box=None)
        return None
    nums = [int(n) for n in re.findall(r"-?\d+", content)]
    result = None
    if len(nums) >= 4:
        x1, y1, x2, y2 = nums[:4]
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))
        x1 = max(0, min(width - 1, x1)); x2 = max(1, min(width, x2))
        y1 = max(0, min(height - 1, y1)); y2 = max(1, min(height, y2))
        if x2 > x1 and y2 > y1:            # a valid rectangle (not zero/inverted)
            result = (x1, y1, x2, y2)
    if runlog:
        runlog.record("box", f"target: {target}", content,
                      box=(list(result) if result else None))
    return result
