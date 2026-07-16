"""BRYES — framediff: a deterministic whole-frame change magnitude (screen-wide).

    frame_diff(png_a, png_b) -> float          # mean absolute difference; 0.0 = identical
    changed(png_a, png_b, threshold) -> bool    # did it change by more than `threshold`?

Mechanism: downscale both PNGs to 64x64 grayscale and take the mean of the absolute
per-pixel differences. Answers "did a LOT of the screen change?" cheaply, with no VLM.

NOT wired into the loop's change-feedback. It was built for Phase-5 Layer 1 (a per-action
"did my click do anything?" detector) but measurement killed that use: a whole-frame mean
drowns small localised changes (a single typed digit scores ~0.05, BELOW the ~0.25 idle
noise floor) AND cannot be regionally cropped (UI-TARS only points, never boxes). "Did my
action work?" is a regional, semantic question — so the loop answers it with the VLM
(`expect` verified in describe(), Layer 2), not a pixel metric.

Parked here, intact, for its RIGHT consumer — the incremental/change-driven `describe`
speed thread, where "did a LOT change -> re-describe?" IS a screen-wide question. See
docs/backlog.md.
"""
import io

from PIL import Image

# Mean-abs-diff (0-255 scale, after the 64x64 gray downscale) at or below which two
# frames are treated as the SAME screen. Calibrated on real no-op vs real-change runs;
# ~2.0 separates cursor/clock noise from a genuine UI change. Override per call if needed.
DEFAULT_THRESHOLD = 2.0

_SIZE = (64, 64)


def _thumb(png_bytes):
    """A PNG's pixels as a flat tuple of 64*64 grayscale ints (0-255)."""
    img = Image.open(io.BytesIO(png_bytes)).convert("L").resize(_SIZE)
    return img.getdata()


def frame_diff(png_a, png_b):
    """Mean absolute per-pixel difference of two PNGs after a 64x64 grayscale downscale.
    0.0 = pixel-identical thumbnails; larger = more of the screen changed."""
    a = _thumb(png_a)
    b = _thumb(png_b)
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def changed(png_a, png_b, threshold=DEFAULT_THRESHOLD):
    """True if the two frames differ by more than `threshold` (a real change)."""
    return frame_diff(png_a, png_b) > threshold
