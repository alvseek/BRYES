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
| GET | `/downscaleshot?window=<id>&scale=0.5` | Capture a full scaled-down frame; the default scale is 0.5. | PNG image with mapping headers: `X-Bryes-Scale` is the resize factor, `X-Bryes-Origin` is the image's top-left in the original frame (`0,0` here), and `X-Bryes-Frame` is the original width and height. Convert each axis to `/act` coordinates using `frame_px = origin + returned_px / scale`. |
| GET | `/upscaleshot?window=<id>&x1=&y1=&x2=&y2=&scale=2` | Capture and enlarge a region of the frame; the default scale is 2. You can also crop a section from large monitor with scale = 1. | PNG image with mapping headers: `X-Bryes-Scale` is the resize factor, `X-Bryes-Origin` is the crop's top-left in the original frame, and `X-Bryes-Frame` is the original width and height. Convert each axis to `/act` coordinates using `frame_px = origin + returned_px / scale`: crop origin `(100, 200)`, scale `2`, and image point `(40, 60)` give frame point `(120, 230)`. |
| POST | `/act` | Perform one input action using a JSON body with `window`, `type`, and the action's fields. | JSON: `ok` and the forwarded `action`. |
| POST | `/locate` | Find one point on a fresh frame using the Eyes (UI-TARS). The JSON body contains `window` and `instruction`. | JSON: frame coordinates `x`, `y`, and the `instruction`. |
| GET | `/profiles?path=windows/unreal-editor` | Read the visual and operating vocabulary for a profile. | JSON: `path`, `visual`, and `operating`. |

- **No auth, loopback only**; the standing guard is that a body must be
  `application/json`, which keeps a cross-origin form post out.
- **One action at a time** — a lock, the same intent as the task API's single-flight.
- Every dependency (device factory, locator, window lister, frame) is injectable, so the whole
  surface is tested model-free in [test_bridge.py](test_bridge.py).

Measured 2026-10-28 through this surface, with the caller outside BRYES: a `Print String` node
created by right-click and typed name, three execution wires landed in `BP_CombatBody_Enemy`,
and a clean compile, without saving.
