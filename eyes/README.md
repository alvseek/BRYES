# BRYES — Phase 2: The Eyes

Turns a screenshot into element coordinates using **UI-TARS-1.5-7B** (a GUI-grounding
model) via OpenRouter. The Eyes are a *rented API client*, not a container — only the
Screen and Hands run locally (see [roadmap.md](../roadmap.md)).

## The one function

```python
from eyes.client import locate

result = locate(screenshot_png_bytes, "the number 7 button in the calculator")
# -> {'x': 130, 'y': 382, 'raw_model_coord': [131, 388],
#     'resized_dims_wh': [1288, 812], 'original_dims_wh': [1280, 800],
#     'content': "click(start_box='(131,388)')", 'usage': {...}}
```

`x, y` are pixel coordinates on the original screenshot — ready to feed straight into
the Screen's `POST /action`.

## Run the proof

The Screen container must be up (`cd ../screen && docker compose up -d`) and your
OpenRouter key must be in [`../.env`](../.env.example).

```bash
python eyes/test_phase2.py        # from the BRYES root
```

It grabs a screenshot, locates the calculator's "7", then proves it twice:
- **eyes_located.png** — a red crosshair drawn on the predicted point
- **eyes_after_click.png** — clicks the point; a correct hit makes the calculator show `7`

## The coordinate convention (the important part)

UI-TARS-1.5 is **Qwen2.5-VL based**. It doesn't see your raw image — it sees a
`smart_resize`d version (each side rounded to a multiple of 28, total area clamped
between `MIN_PIXELS` and `MAX_PIXELS`) and returns coordinates in *that* space. We
convert back to real pixels:

```
actual_x = model_x * original_width  / resized_width
actual_y = model_y * original_height / resized_height
```

For our 1280×800 desktop the resized size is 1288×812, so the correction is tiny —
but on other resolutions (or if a provider uses a smaller `MAX_PIXELS`) it matters.
`smart_resize()` in [client.py](client.py) computes the resized dims exactly.

If grounding ever lands off-target, print `raw_model_coord` vs `resized_dims_wh`: the
raw magnitude tells you which space the model used, and you tune `MAX_PIXELS`.

## Cost

~1,400 prompt tokens per call (mostly the image) ≈ **$0.00014 per look** at UI-TARS
1.5-7B pricing. The Eyes are called on *every* step, so this is the line item to watch
in Phase 6 — but it's cheap enough to ignore until real usage proves otherwise.

## Model

`bytedance/ui-tars-1.5-7b` — the only UI-TARS on OpenRouter today (no 72B, no
UI-TARS-2). If 7B grounding proves too weak on real target apps, the fallback is
UI-TARS-72B (more expensive) per the roadmap's Phase 6.
