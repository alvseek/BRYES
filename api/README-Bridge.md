# Visual Bridge

[bridge-windows.py](bridge-windows.py) exposes individual operations for an outside caller that already
knows what to do and only needs eyes and hands: no goal, no loop, no decision. Unlike
the [Task API](README.md), it does not run BRYES's Brain.

## Run

Run on the Windows host, from the directory containing `api/`:

```powershell
python api/bridge-windows.py
```

It listens on `http://127.0.0.1:8110`. Any HTTP client can drive it; [bridge_client.py](bridge_client.py)
is the short one, one line per step, and it saves every image beside a `.json` holding its mapping
so a pixel read off a crop goes straight back as an action:

```powershell
$env:BRIDGE_WINDOW = "0x1402aa"                                # an id from `windows`
python api/bridge_client.py windows
python api/bridge_client.py shot overview --raise              # bring the window forward first
python api/bridge_client.py crop pins 1500 700 2580 1000 --scale 2
python api/bridge_client.py act drag 600 260 900 300 --from pins   # crop pixels -> frame pixels
python api/bridge_client.py act type --text "Event BeginPlay"
```

`--raise` hovers where the pointer already is when it is inside the window, so nothing moves;
`act` waits `--settle` seconds (default 0.4) so the next look sees the UI after the change.

## Endpoints

```
GET  /windows                            every targetable window: id, title, rect,
                                         image_rect (in the frame's own pixels), foreground
GET  /pointer?window=<id>                where the pointer is, in screen and image space, and
                                         whether it is inside the frame and inside the window
GET  /screenshot?window=<id>              PNG of the target's monitor, 1:1
GET  /downscaleshot?window=&scale=0.5     the frame scaled down (default 0.5, as the Eyes'
                                          own overview does)
GET  /upscaleshot?window=&x1=&y1=&x2=&y2=&scale=2   one crop, enlarged
POST /act      {window, type, x, y, ...}  one verb at the caller's pixels
POST /locate   {window, instruction}      one pixel from the Eyes (UI-TARS) on a fresh frame
GET  /profiles?path=windows/unreal-editor the vocabulary both sides read
```

- **Mapping rule for the two scaled shots:** `frame_px = origin + returned_px / scale`, with
  `X-Bryes-Scale`, `X-Bryes-Origin` and `X-Bryes-Frame` returned as headers on every image.
- **No auth, loopback only**; the standing guard is that a body must be
  `application/json`, which keeps a cross-origin form post out.
- **One action at a time** — a lock, the same intent as the task API's single-flight.
- Every dependency (device factory, locator, window lister, frame) is injectable, so the whole
  surface is tested model-free in [test_bridge.py](test_bridge.py).

Measured 2026-10-28 through this surface, with the caller outside BRYES: a `Print String` node
created by right-click and typed name, three execution wires landed in `BP_CombatBody_Enemy`,
and a clean compile, without saving.
