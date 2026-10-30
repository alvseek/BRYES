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

A **window** is the selected application's rectangle on the desktop. Its ID selects the target
for screenshots and input. A **frame** is the entire monitor containing that window, not a crop
of the window. A frame can therefore include other windows visible on the same monitor.

**Screen coordinates** are positions in Windows' overall desktop space, which can span multiple
monitors. **Image coordinates** are positions in the frame, measured from that monitor image's
top-left corner. Input actions use image coordinates; the Windows body translates them to screen
coordinates.

## Endpoints

| Method | Endpoint | Description | Returns |
|---|---|---|---|
| GET | `/health` | Check whether the HTTP service is responding. | JSON: `ok`. |
| GET | `/windows` | List targetable windows. | JSON: `windows`, each with `id`, `title`, `rect`, `image_rect`, `frame`, and `foreground`. |
| GET | `/pointer` | Read the global pointer position; optionally add `?window=<id>` for window-relative details. No screenshot is taken or returned. | JSON: `x`, `y` in desktop coordinates. With a window ID, `image_x`, `image_y` are relative to the top-left of that window's monitor; `inside_frame` and `inside_window` indicate whether the pointer is inside that monitor and window. For example, monitor origin `(1920, 0)` and pointer `(2020, 50)` give image coordinates `(100, 50)`. |
| GET | `/screenshot?window=<id>` | Capture the target's monitor at full resolution. | PNG image. |
| GET | `/downscaleshot?window=<id>&scale=0.5` | Capture the target's entire monitor, then shrink the image for a whole-screen overview. `scale` multiplies both width and height: `0.5` (default) halves each dimension. Accepts `0.05` to `1`, inclusive; `1` keeps the original size. Nothing is cropped. | PNG bytes (`image/png`), not JSON. Headers: `X-Bryes-Scale` = applied scale; `X-Bryes-Origin` = `0,0` (no crop); `X-Bryes-Frame` = original monitor dimensions as `width,height`, before resizing. Map a point in the returned image to `/act` coordinates with `x = image_x / scale`, `y = image_y / scale`. Example: a `1920×1080` frame at `0.5` returns `960×540`; image point `(100, 50)` maps to frame point `(200, 100)`. |
| GET | `/upscaleshot?window=<id>&x1=100&y1=200&x2=300&y2=400&scale=2` | Capture the target's monitor, crop a rectangle, then enlarge it to inspect small text or controls. Required integers `x1,y1` and `x2,y2` mark the crop's top-left and bottom-right in the **original full-resolution frame**, not a downscaled image or desktop coordinates. They must satisfy `0 ≤ x1 < x2 ≤ frame width` and `0 ≤ y1 < y2 ≤ frame height`. `scale` accepts `1` to `4`, inclusive (default `2`); `1` returns the crop without enlargement. | PNG bytes (`image/png`), not JSON. Its dimensions are the crop width and height multiplied by `scale` (rounded to whole pixels). Headers: `X-Bryes-Scale` = applied scale; `X-Bryes-Origin` = crop origin as `x1,y1`; `X-Bryes-Frame` = original monitor dimensions as `width,height`, **not** the crop or enlarged dimensions. Map back to `/act` with `x = x1 + image_x / scale`, `y = y1 + image_y / scale`. Example: the request shown returns a `400×400` image; image point `(40, 60)` maps to frame point `(120, 230)`. |
| POST | `/act` | Perform a single mouse/keyboard action or an ordered batch in one selected window. Requires `Content-Type: application/json`, `BRYES_ALLOW_HOST=1`, and `window` (ID from `/windows`). For one action, put `type` and its fields at the top level; for a batch, use a non-empty `actions` array, with `window` only at the request level. Do not send both top-level `type` and `actions`. All actions are validated before any input; execution **stops at the first failure**, with no rollback or automatic retry. The lock covers the entire batch; no other Bridge action can interleave. There is no added delay or UI-state check between actions.<br><br>**Mouse fields:**<br>• `click`, `double_click`, `right_click`, `hover`: numeric `x`, `y`.<br>• `drag`: numeric `x`, `y` (start), `x2`, `y2` (end); left-button drag.<br>• `scroll`: numeric `x`, `y`, optional `direction` (`up` or `down`, default `down`); scrolls three notches there.<br>Points use the **original full-resolution monitor frame**, not scaled-image or desktop coordinates, and must lie inside the target window (checked during execution).<br><br>**Keyboard fields:**<br>• `{"type":"type","text":"abc"}`: type into the focused control without clearing it.<br>• `{"type":"key","key":"ctrl+a"}`: press a key or shortcut once.<br>• `{"type":"key_hold","key":"w","seconds":1.2}`: hold then release; numeric `seconds` is optional (default `1`, clamped to `0.1–5`).<br><br>Batch example: `{"window":"<id>","actions":[{"type":"click","x":200,"y":100},{"type":"type","text":"abc"},{"type":"key","key":"enter"}]}`. | Single success: `{"ok":true,"action":{"type":"click","x":200,"y":100}}`.<br>Batch success: `{"ok":true,"actions":[...]}`, listing all executed actions in order.<br>Execution failure in a batch: `{"ok":false,"error":"Action failed","description":"...","completed":[...],"failed_index":1,"failed_action":{...}}`. `failed_index` is **zero-based**; later actions are not attempted. `completed` contains only calls that returned successfully. The failed action may already have caused partial input; completed actions remain applied. Do not blindly retry the whole batch.<br><br>Echoed actions exclude `window`; `seconds` is the requested value, not necessarily the clamped duration. **Success confirms input execution, not the intended UI outcome**; take a screenshot to verify.<br><br>HTTP `415`: non-JSON request. `400`: invalid request/action or unsupported verb (nothing executed; `description` identifies `actions[index]` for an invalid batch item). `409`: device refusal such as the host gate, focus failure, or an out-of-window point. `500`: unexpected execution error. Errors include JSON `error` and `description`; batch execution errors also include progress as above. |
| POST | `/locate` | Find one point on a fresh frame using the Eyes (UI-TARS). The JSON body contains `window` and `instruction`. | JSON: frame coordinates `x`, `y`, and the `instruction`. |
| GET | `/profiles?path=windows/unreal-editor` | Read the visual and operating vocabulary for a profile. | JSON: `path`, `visual`, and `operating`. |

- **No auth, loopback only**; the standing guard is that a body must be
  `application/json`, which keeps a cross-origin form post out.
- **One request's inputs at a time** — one lock covers a single action or an entire batch. Other applications and human input are not locked out.
- Every dependency (device factory, locator, window lister, frame) is injectable, so the whole
  surface is tested model-free in [test_bridge.py](test_bridge.py).

Measured 2026-10-28 through this surface, with the caller outside BRYES: a `Print String` node
created by right-click and typed name, three execution wires landed in `BP_CombatBody_Enemy`,
and a clean compile, without saving.
