# Visual Bridge

[bridge-windows.py](bridge-windows.py) exposes individual operations for an outside caller that already
knows what to do and only needs eyes and hands: no goal, no loop, no decision. Unlike
the [Task API](README.md), it does not run BRYES's Brain.

## Run

Run on the Windows host, from the directory containing `api/`:

```powershell
python api/bridge-windows.py
```

It listens on `http://127.0.0.1:8110`. Any HTTP client can call it. The separate
[Bridge client](README-Bridge-Client.md) provides a command-line interface and coordinate mapping.

## Window, frame, and coordinates

A **window** is the selected application's rectangle on the desktop. Its ID or title selects the target
for screenshots and input. A **frame** is the entire monitor containing that window, not a crop
of the window. A frame can therefore include other windows visible on the same monitor.

**Screen coordinates** are positions in Windows' overall desktop space, which can span multiple
monitors. **Image coordinates** are positions in the frame, measured from that monitor image's
top-left corner. Input actions use image coordinates; the Windows body translates them to screen
coordinates.

## Endpoints

Target-taking routes accept exactly one `window` (positive hexadecimal handle) or `title`
(trimmed, case-insensitive substring). A title must match exactly one visible window: no match
returns 404, and multiple matches return 409 with candidate IDs and titles in `matches`.
Both selectors, empty selectors, and malformed IDs return 400. `/pointer` without a selector
remains global. Each request resolves once; a window can still close or its handle be reused
after selection, so refresh and verify the target rather than relying on a retry.

| Method | Endpoint | Description | Returns |
|---|---|---|---|
| GET | `/health` | Check whether the HTTP service is responding. | JSON: `ok`. |
| GET | `/windows` | List targetable windows. | JSON: `windows`, each with `id`, `title`, `rect`, `image_rect`, `frame`, and `foreground`. |
| GET | `/pointer` | Read the global pointer position; optionally add `?window=<id>` for window-relative details. No screenshot is taken or returned. | JSON: `x`, `y` in desktop coordinates. With a window ID, `image_x`, `image_y` are relative to the top-left of that window's monitor; `inside_frame` and `inside_window` indicate whether the pointer is inside that monitor and window. For example, monitor origin `(1920, 0)` and pointer `(2020, 50)` give image coordinates `(100, 50)`. |
| GET | `/screenshot?window=<id>` | Capture the target's monitor at full resolution. | PNG image. |
| GET | `/downscaleshot?window=<id>&scale=0.5` | Capture the target's entire monitor, then shrink the image for a whole-screen overview. `scale` multiplies both width and height: `0.5` (default) halves each dimension. Accepts `0.05` to `1`, inclusive; `1` keeps the original size. Nothing is cropped. | PNG bytes (`image/png`), not JSON. Headers: `X-Bryes-Scale` = applied scale; `X-Bryes-Origin` = `0,0` (no crop); `X-Bryes-Frame` = original monitor dimensions as `width,height`, before resizing. Map a point in the returned image to `/act` coordinates with `x = image_x / scale`, `y = image_y / scale`. Example: a `1920×1080` frame at `0.5` returns `960×540`; image point `(100, 50)` maps to frame point `(200, 100)`. |
| GET | `/upscaleshot?window=<id>&x1=100&y1=200&x2=300&y2=400&scale=2` | Capture the target's monitor, crop a rectangle, then enlarge it to inspect small text or controls. Required integers `x1,y1` and `x2,y2` mark the crop's top-left and bottom-right in the **original full-resolution frame**, not a downscaled image or desktop coordinates. They must satisfy `0 ≤ x1 < x2 ≤ frame width` and `0 ≤ y1 < y2 ≤ frame height`. `scale` accepts `1` to `4`, inclusive (default `2`); `1` returns the crop without enlargement. | PNG bytes (`image/png`), not JSON. Its dimensions are the crop width and height multiplied by `scale` (rounded to whole pixels). Headers: `X-Bryes-Scale` = applied scale; `X-Bryes-Origin` = crop origin as `x1,y1`; `X-Bryes-Frame` = original monitor dimensions as `width,height`, **not** the crop or enlarged dimensions. Map back to `/act` with `x = x1 + image_x / scale`, `y = y1 + image_y / scale`. Example: the request shown returns a `400×400` image; image point `(40, 60)` maps to frame point `(120, 230)`. |
| POST | `/screenshot`, `/downscaleshot`, `/upscaleshot` | JSON object with the same selector and capture fields as GET, plus optional boolean `raise`. For example `{"title":"Unreal Editor","raise":true,"scale":0.5}` on `/downscaleshot`. `raise:true` requires `BRYES_ALLOW_HOST=1`; it hovers safely to focus and captures under one lock. GET cannot raise. | Same PNG and mapping headers as the corresponding GET. A focus refusal returns JSON, not an image. |
| POST | `/act` | Execute one input or delay action, or a non-empty ordered `actions` batch. Supply a window or title selector at request level and `Content-Type: application/json`; desktop input requires `BRYES_ALLOW_HOST=1`. Do not combine top-level `type` and `actions`. The entire batch is validated before input or waiting, runs under one lock, and stops at its first failure without retry or rollback.<br><br>**Mouse:** `click`, `double_click`, `right_click`, `hover` need numeric `x,y`; `drag` also needs `x2,y2` (left button); `scroll` needs `x,y` and optional `direction` (`up` or `down`, default `down`, three notches). Points are original full-resolution monitor-frame pixels and must be inside the target window at execution.<br><br>**Keyboard:** `{"type":"type","text":"abc"}` types without clearing; `{"type":"key","key":"ctrl+a"}` presses once; `{"type":"key_hold","key":"w","seconds":1.2}` holds then releases (`seconds` defaults to `1`, clamped to `0.1–5`).<br><br>**Delay:** `{"type":"delay","miliseconds":1000}` waits one second at that position in the sequence, with no desktop input. `miliseconds` (spelled exactly so) is required, finite, numeric and nonnegative; zero and fractional values are accepted. The server divides it by 1000 for seconds. The lock stays held during the delay, so other Bridge inputs wait too; choose HTTP timeouts to cover the full batch. There is no automatic delay or UI-readiness check.<br><br>Example: `{"window":"<id>","actions":[{"type":"key","key":"enter"},{"type":"delay","miliseconds":1000},{"type":"type","text":"abc"}]}` presses Enter, waits, then types. | Single success: `{"ok":true,"action":{...}}`; batch success: `{"ok":true,"actions":[...]}` in execution order, including completed delays.<br>Batch execution failure: `{"ok":false,"error":"Action failed","description":"...","completed":[...],"failed_index":1,"failed_action":{...}}`. The index is zero-based; later actions do not run. A failed action may have partially executed, and completed inputs remain applied. Never retry the whole batch blindly.<br><br>Echoed actions omit the selector; key-hold `seconds` echoes the requested, not necessarily clamped, duration. Success confirms execution, not the desired UI result; capture again to verify.<br><br>HTTP `415`: non-JSON; `400`: invalid action/request or unsupported verb (no input or delay runs; an invalid batch item is named as `actions[index]`); `409`: device refusal, including host gate, focus or bounds; `500`: unexpected execution failure. Failures include `error` and `description`; batch execution failures also retain progress. |
| POST | `/act` with optional `mapping` | Overrides the default frame-pixel interpretation above: add `"mapping":{"scale":2,"origin":[100,200]}` at request level to send points measured on a cropped/resized image. The server converts `x,y` and both drag endpoints with `frame = origin + image_coordinate / scale`, then rounds to integer pixels using Python's nearest-even rounding. Example: `{"window":"<id>","mapping":{"scale":2,"origin":[100,200]},"type":"click","x":40,"y":60}` clicks frame point `(120,230)`. For a batch, one mapping applies to every pointer action; keyboard fields and delay durations are unchanged. Read scale/origin from that image's `X-Bryes-*` headers; origin is a crop offset within the monitor frame, not the Windows desktop origin. `scale` must be a finite positive number and `origin` an array of two finite numbers; booleans are invalid. Omit mapping for existing frame-pixel behavior. A present null/malformed mapping, per-action mapping, or non-finite conversion is refused before any input or waiting. Window-bound checks still happen during execution on the converted points. No capture is stored, and mapping cannot detect that the UI has moved. | Same success/progress shapes as `/act`; echoed pointer actions, including `completed` and `failed_action`, contain converted **frame coordinates**, never the original image points or mapping. Invalid mapping returns HTTP `400` with JSON `error` and `description`. |
| POST | `/locate` | Find one point on a fresh frame using the Eyes (UI-TARS). The JSON body contains a selector and `instruction`. | JSON: frame coordinates `x`, `y`, and the `instruction`. |
| GET | `/profiles?path=windows/unreal-editor` | Read the visual and operating vocabulary for a profile. | JSON: `path`, `visual`, and `operating`. |

- **No auth, loopback only**; the standing guard is that a body must be
  `application/json`, which keeps a cross-origin form post out.
- **One request's inputs at a time** — one lock covers a single action or an entire batch. Other applications and human input are not locked out.
- **Failures are JSON:** `error` and `description`, with 400 for invalid input, 404 for missing targets or routes, 409 for ambiguous targets or device refusals, 415 for non-JSON POST, 502 for Eyes failures, 503 for unavailable pointer, and 500 for unexpected failures. A failed action may already have changed the desktop; no input is automatically retried or rolled back.
- **Capture is not isolation:** plain GET and POST without `raise` do not send input. Focus does not guarantee privacy or UI readiness, and the image is the whole monitor, including other applications.
- Every dependency (device factory, locator, window lister, frame) is injectable, so the whole
  surface is tested model-free in [test_bridge.py](test_bridge.py).

Measured 2026-10-28 through this surface, with the caller outside BRYES: a `Print String` node
created by right-click and typed name, three execution wires landed in `BP_CombatBody_Enemy`,
and a clean compile, without saving.
