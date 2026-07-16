"""BRYES — framediff regression test (deterministic, $0, no models, no network).

Model-free assertions on the Layer-1 pixel no-op detector:
  - identical frames        -> score 0.0, not changed
  - a filled rectangle      -> score well above threshold, changed
  - a single toggled pixel  -> below threshold, not changed (noise-immune)
  - symmetry                 -> frame_diff(a,b) == frame_diff(b,a)

Synthetic PNGs are built in-memory with PIL, so this needs no container and no key.

Usage:  python test_framediff.py
"""
import io
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framediff import DEFAULT_THRESHOLD, changed, frame_diff  # noqa: E402

_SIZE = (320, 240)


def _png(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _solid(color):
    return _png(Image.new("RGB", _SIZE, color))


# --- checks: each returns (name, passed, note) -------------------------------

def t_identical():
    a = _solid((30, 30, 30))
    score = frame_diff(a, a)
    ok = score == 0.0 and not changed(a, a)
    return ("identical frames -> 0.0, not changed", ok, f"score={score}")


def t_big_change():
    base = Image.new("RGB", _SIZE, (30, 30, 30))
    a = _png(base)
    b_img = base.copy()
    for x in range(80, 240):              # a ~25%-of-screen white rectangle
        for y in range(60, 180):
            b_img.putpixel((x, y), (255, 255, 255))
    b = _png(b_img)
    score = frame_diff(a, b)
    ok = changed(a, b) and score > DEFAULT_THRESHOLD * 5
    return ("filled rectangle -> changed", ok, f"score={score:.2f}")


def t_tiny_change():
    base = Image.new("RGB", _SIZE, (30, 30, 30))
    a = _png(base)
    b_img = base.copy()
    b_img.putpixel((10, 10), (255, 255, 255))    # a single toggled pixel = noise
    b = _png(b_img)
    score = frame_diff(a, b)
    ok = not changed(a, b)
    return ("single toggled pixel -> below threshold, not changed", ok, f"score={score:.4f}")


def t_symmetry():
    a = _solid((0, 0, 0))
    b = _solid((128, 128, 128))
    ok = abs(frame_diff(a, b) - frame_diff(b, a)) < 1e-9
    return ("frame_diff is symmetric", ok, f"diff={frame_diff(a, b):.2f}")


TESTS = [t_identical, t_big_change, t_tiny_change, t_symmetry]


def main():
    failed = 0
    for t in TESTS:
        try:
            name, passed, note = t()
        except Exception as e:
            name, passed, note = (t.__name__, False, repr(e))
        print(("PASS:" if passed else "FAIL:") + f" {name}" + (f"  ({note})" if note else ""))
        failed += not passed

    print()
    if failed:
        print(f"FAIL: {failed}/{len(TESTS)} framediff checks failed.")
        return 1
    print(f"PASS: all {len(TESTS)} framediff checks passed. (DEFAULT_THRESHOLD={DEFAULT_THRESHOLD})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
