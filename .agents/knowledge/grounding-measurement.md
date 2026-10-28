# Grounding on the Unreal Editor — measured, and how to measure it again

Measured 2026-10-28 with `grounding.py` on a live capture of `BP_CombatBody_Party`. Two frames,
the same three nodes on both, so the shared probes repeat.

## What the numbers were

| Kind | Hits | Median error |
|---|---|---|
| node_header | 2/3 | 6 px on the miss |
| pin | 1/5 | 10.6 px |
| asset_tile | 6/6 | 0 px |
| empty_canvas | 0/6 | 254 px |

Model: `bytedance/ui-tars-1.5-7b`, recorded in every report so a swap invalidates the number
rather than silently inheriting it.

## How to read it

- **Headers and asset tiles are usable by eye.** Both are large and carry readable text.
- **Pins are not.** 1 in 5, with a 10 px error on a 14 px target, so the drag starts on the node
  body instead of the pin and nothing in the transcript says so.
- **Empty canvas is not a pointing question.** Asking a grounding model for "an empty spot"
  returns an object every time. A drop onto canvas must be a computed offset, which is why the drag
  action carries `destination_offset`.

## How to measure again

1. Capture the monitor that holds the editor, not the whole desk (`MonitorFromWindow`).
2. Look at the capture before marking anything.
3. Write `labels-*.json`: `kind`, `instruction`, `box` in pixels.
4. `python grounding.py --frame <png> --labels <json> --check-labels` and **look at the overlay**.
5. `python grounding.py --frame <png> --labels <json>` to score it.

A hit is a point inside the box, edge inclusive; the report carries the per-kind rate, the median
error and the model.

## The trap that cost the first pass

Pins marked by eye from a full-frame view were 5 to 10 px off, which moved one frame's pin rate
from 1/5 to 2/5. Small targets must be marked on a 4x crop and divided back, and the overlay must
be looked at before a single model call is spent. The overlay exists to catch the author, and it
did.
