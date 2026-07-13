# BRYES — Phase 1: The Screen

A disposable Ubuntu desktop running in a container that you can **screenshot** and
**click inside** over HTTP. This is the "Screen + Hands" piece of the BRYES
architecture (see [roadmap.md](../roadmap.md)). The Eyes and Brain (Phases 2–4)
will drive it through the same two endpoints built here.

## What's inside

| Piece | Role |
|---|---|
| **Xvfb** | Virtual display (`:99`) — a desktop with no monitor |
| **fluxbox** | Lightweight window manager |
| **gnome-calculator + xterm + Chrome** | Visible apps to click/type against |
| **xdotool** | The "Hands" — clicks, scrolls, drags, typing, keypresses |
| **scrot** | Takes the screenshots |
| **Flask API** (`:8000`) | Exposes the two abilities over HTTP |
| **x11vnc + noVNC** (`:6080`) | Live view of the desktop in your browser |

## Run it

```bash
cd screen
docker compose up --build -d      # build + start (first build pulls Ubuntu, ~1–2 min)
```

Then either **watch it live** — open <http://localhost:6080/vnc.html> and click *Connect* —
or **prove it from the command line**:

```bash
python test_phase1.py             # saves shot_before.png + shot_after.png
python test_hands.py              # deterministic regression check for the Hands primitives
```

**Done when** (from the roadmap): a screenshot returns a PNG, and a click visibly
changes the next screenshot. `test_phase1.py` checks exactly that.

## The two abilities (HTTP API)

```bash
# Screenshot -> PNG
curl -s http://localhost:8000/screenshot -o desktop.png

# Click at (x, y)   (button: 1=left, 3=right)
curl -s -X POST http://localhost:8000/action \
  -H "Content-Type: application/json" \
  -d '{"type":"click","x":120,"y":200}'

# Type text (into whatever is focused)
curl -s -X POST http://localhost:8000/action \
  -H "Content-Type: application/json" -d '{"type":"type","text":"hello"}'

# Press a key  (Return, Escape, Tab, ctrl+a, ...)
curl -s -X POST http://localhost:8000/action \
  -H "Content-Type: application/json" -d '{"type":"key","key":"Return"}'
```

| Endpoint | Method | Body | Returns |
|---|---|---|---|
| `/health` | GET | — | `{"status":"ok","display":":99"}` |
| `/screenshot` | GET | — | `image/png` |
| `/pointer` | GET | — | `{"x":..,"y":..}` (current mouse position) |
| `/action` | POST | `{"type":"click","x":..,"y":..,"button":1}` | `{"ok":true}` |
| `/action` | POST | `{"type":"double_click","x":..,"y":..}` | `{"ok":true}` |
| `/action` | POST | `{"type":"right_click","x":..,"y":..}` | `{"ok":true}` |
| `/action` | POST | `{"type":"hover","x":..,"y":..}` | `{"ok":true}` |
| `/action` | POST | `{"type":"scroll","x":..,"y":..,"direction":"down","amount":3}` | `{"ok":true}` |
| `/action` | POST | `{"type":"drag","x":..,"y":..,"x2":..,"y2":..}` | `{"ok":true}` |
| `/action` | POST | `{"type":"type","text":".."}` | `{"ok":true}` |
| `/action` | POST | `{"type":"key","key":".."}` | `{"ok":true}` |

## Manage

```bash
docker compose logs -f screen     # watch container logs
docker compose down               # stop + remove (it's disposable)
```

## Notes

- Resolution is `1280x800`; change via `SCREEN_RESOLUTION` (e.g. `1920x1080x24`) in
  [docker-compose.yml](docker-compose.yml).
- The API has **no auth** — it's bound to your machine for local prototyping only.
  Don't expose port 8000 to a network.
