"""Deterministic regression tests for the two-mode describe() + box() (ADR-004).

Model-free: mocks eyes.client._ask and .box so it runs with NO network. The live behaviour
(real boxing, real crop-describe faithfulness/latency) is covered by the bake-off + the
loop smoke run; this file guards the pure wiring — helpers and mode selection.

Run: python eyes/test_describe.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image  # noqa: E402

import eyes.client as ec  # noqa: E402


def _png(w, h):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


def test_downscale():
    frame = _png(1280, 800)
    assert Image.open(io.BytesIO(ec._downscale(frame, 0.5))).size == (640, 400)
    assert ec._downscale(frame, 1.0) is frame            # >=1.0 returns it unchanged
    print("PASS: _downscale scales 0.5 -> 640x400, no-op at >=1.0")


def test_crop():
    frame = _png(1000, 1000)
    # box 100x100 at (400,400); pad 0.15 -> +15px each side -> (385,385,515,515) = 130x130
    assert Image.open(io.BytesIO(ec._crop(frame, (400, 400, 500, 500), 0.15))).size == (130, 130)
    # pad clamps at the frame edge (left/top can't go below 0)
    assert Image.open(io.BytesIO(ec._crop(frame, (0, 0, 100, 100), 0.5))).size == (150, 150)
    print("PASS: _crop pads +15% and clamps to the frame")


def test_box_parsing():
    frame = _png(200, 200)
    ec._ask = lambda *a, **k: "50,60,150,160"
    assert ec.box(frame, "x") == (50, 60, 150, 160)
    ec._ask = lambda *a, **k: "no numbers here"
    assert ec.box(frame, "x") is None                    # unparseable
    ec._ask = lambda *a, **k: "only two 12 34"
    assert ec.box(frame, "x") is None                    # <4 ints
    ec._ask = lambda *a, **k: "5,5,5,5"
    assert ec.box(frame, "x") is None                    # zero-area = not a valid rect
    print("PASS: box() -> coords on valid reply, None on garbage/partial/degenerate")


def test_describe_modes():
    frame = _png(1280, 800)
    seen = {}

    def fake_ask(prompt, images, *, model, max_tokens, timeout, reasoning=None):
        img = images if isinstance(images, (bytes, bytearray)) else images[0]
        seen.update(prompt=prompt, size=Image.open(io.BytesIO(img)).size,
                    model=model, reasoning=reasoning)
        return "FAKE"
    ec._ask = fake_ask

    ec.describe(frame)                                   # OVERVIEW (no visual_focus/visual_expectation)
    assert seen["size"] == (640, 400) and seen["prompt"] == ec.OVERVIEW_PROMPT
    assert seen["model"] == ec.DESCRIBE_MODEL and seen["reasoning"] == ec.NO_THINK

    ec.box = lambda img, tgt, *, timeout=60: (100, 100, 300, 200)
    ec.describe(frame, visual_focus="the field")         # TRIM -> crop
    assert seen["size"] != (1280, 800) and "cropped region" in seen["prompt"]

    ec.box = lambda img, tgt, *, timeout=60: None
    out = ec.describe(frame, visual_focus="ghost")       # box miss -> VISUAL_FOCUS FAILED + overview
    assert seen["size"] == (640, 400) and seen["prompt"] == ec.OVERVIEW_PROMPT
    assert "VISUAL_FOCUS FAILED" in out

    ec.describe(frame, visual_expectation="the app is open")   # w/o visual_focus -> full + verify
    assert seen["size"] == (1280, 800) and "VERIFICATION" in seen["prompt"]

    ec.box = lambda img, tgt, *, timeout=60: (100, 100, 300, 200)
    ec.describe(frame, visual_focus="f", visual_expectation="e", careful=True)   # careful -> 72B
    assert seen["model"] == ec.CAREFUL_MODEL and "VERIFICATION" in seen["prompt"]
    print("PASS: describe() routes overview / trim / box-miss / expect-no-focus / careful")


if __name__ == "__main__":
    test_downscale()
    test_crop()
    test_box_parsing()
    test_describe_modes()
    print("\nAll describe/box regression tests passed.")
