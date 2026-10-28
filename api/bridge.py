"""BRYES visual bridge -- a primitive-level HTTP surface for an outside agent (SP-6).

No Brain, no goal, no loop. The caller lists the windows, screenshots one, points at a thing
by description, and acts at a pixel; BRYES does as it is told and reports what is there.

  GET  /health                            -> {ok: true}
  GET  /windows                           -> {frame: {origin, size}, windows: [{id, title, rect,
                                              image_rect, foreground, ...}]}
  GET  /pointer?window=<id>               -> {x, y, image_x, image_y, inside_frame, inside_window}
  GET  /screenshot?window=<id>            -> PNG of the body's current frame, 1:1
  GET  /downscaleshot?window=&scale=0.5   -> PNG scaled down, with the mapping headers
  GET  /upscaleshot?window=&x1=&y1=&x2=&y2=&scale=2 -> PNG of that crop, enlarged, same headers
  POST /act      {window, type, x?, y?, x2?, y2?, text?, key?, seconds?, direction?}
  POST /locate   {window, instruction}    -> {x, y}
  GET  /profiles?path=<a/b>               -> {path, visual, operating}

Why the shape: the task API (api/server.py) takes a GOAL and lets the Brain decide. An agent
that already knows what to do needs the layer below that, and nothing of the layer above it.
Coordinates are pixels of whatever frame `device.screenshot()` returns; the body translates
them to screen pixels itself, so this surface stays correct when SP-2 makes the frame the
target's monitor.

Rectangles: Windows reports a window rect in SCREEN coordinates. The frame the caller receives
is the grabbed image, whose origin is the virtual screen's, not (0,0) on a multi-monitor desk.
So every window carries `image_rect` as well, which is the rectangle in the frame the caller
actually gets, and that is what a click coordinate must be measured in.

Auth: none, by Alvi's call (council decision). What stands in its place is that a body must be
JSON: a cross-origin form post is a "simple request" the browser does not preflight, so
refusing every non-JSON content type is what keeps a page in a tab from clicking the desktop.

Run: python api/bridge.py  ->  http://127.0.0.1:8110
"""
import ctypes
import io
import sys
import threading
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, abort, jsonify, request, send_file  # noqa: E402
from PIL import Image  # noqa: E402
from werkzeug.exceptions import HTTPException  # noqa: E402

from devices.windows import WindowsDevice, monitor_rect, pointer_in_rect  # noqa: E402
from eyes.client import locate as eyes_locate  # noqa: E402
from profiles import load_profiles, profile_exists  # noqa: E402

HOST = "127.0.0.1"
PORT = 8110

# One action at a time, the way the task API allows one task at a time: one desktop, one driver.
_LOCK = threading.Lock()

# Verbs the surface will forward. The body's Capabilities are the second check, so a verb that
# exists here but not on this body is refused with the body's own reason.
_POINT_VERBS = {"click", "double_click", "right_click", "hover"}
_VERBS = _POINT_VERBS | {"drag", "scroll", "type", "key", "key_hold"}


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


def list_windows_with_handles():
    """[{id, title, rect, foreground}] for every visible top-level window with a title.

    Kept here rather than in devices/windows.py because SP-2 is editing that file for the
    monitor frame; it moves there once that closes.
    """
    user32 = ctypes.windll.user32
    out = []
    fg = user32.GetForegroundWindow()
    enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def collect(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.IsIconic(hwnd):        # minimised: its rect is off-screen and it cannot be shown
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value.strip()
        if not title:
            return True
        r = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        if r.right <= r.left or r.bottom <= r.top:
            return True
        out.append({"id": hex(int(hwnd)), "title": title,
                    "rect": [r.left, r.top, r.right, r.bottom],
                    "foreground": int(hwnd) == int(fg)})
        return True

    user32.EnumWindows(enum_proc(collect), 0)
    return out


def _device_factory(hwnd):
    """The body for one window handle. Its own gate (BRYES_ALLOW_HOST) still applies on act."""
    return WindowsDevice(hwnd=hwnd)


def frame_rect_for(hwnd):
    """(left, top, right, bottom) of the image `screenshot()` returns for this window.

    SP-2 narrowed the frame to the monitor holding the target (R10), so the origin a caller's
    pixels are measured from is that monitor's, not the desktop's. `monitor_rect` answers it
    from the OS; with no handle, or no answer, the whole virtual desktop is still the frame.
    """
    rect = monitor_rect(hwnd) if hwnd else None
    if rect:
        return rect
    user32 = ctypes.windll.user32
    ox, oy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    w, h = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
    return (ox, oy, ox + w, oy + h)


def _parse_window_id(raw):
    try:
        return int(str(raw), 16)
    except (TypeError, ValueError):
        return None


def _scaled(image, scale):
    """PNG bytes of `image` scaled by `scale` (PIL's LANCZOS, size rounded to at least 1 px)."""
    width, height = image.size
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    buf = io.BytesIO()
    image.resize(size, Image.LANCZOS).save(buf, "PNG")
    return buf.getvalue()


def _scale_arg(raw, default, low, high):
    """A scale factor from the query string, refused outside [low, high] rather than clamped."""
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        abort(400, description="scale must be a number")
    if not low <= value <= high:
        abort(400, description=f"scale must be between {low} and {high}")
    return value


def _crop_arg(args, size):
    """(x1, y1, x2, y2) from the query string, validated against the frame it comes from."""
    try:
        x1, y1 = int(args["x1"]), int(args["y1"])
        x2, y2 = int(args["x2"]), int(args["y2"])
    except (KeyError, TypeError, ValueError):
        abort(400, description="x1, y1, x2 and y2 are required integers")
    width, height = size
    if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
        abort(400, description=f"the crop must sit inside the {width}x{height} frame, "
                              f"with x1 < x2 and y1 < y2")
    return (x1, y1, x2, y2)


def _shot_response(png, scale, origin, frame):
    """A PNG with the numbers a caller needs to map what it sees back to frame pixels.

    The rule, for both directions: `frame_px = origin + returned_px / scale`.
    At `scale` 0.5 a returned pixel 2 is frame pixel 4; at `scale` 1.5 a returned pixel 15 is
    frame pixel 10, offset by `origin` if the shot was cropped first.
    """
    resp = send_file(io.BytesIO(png), mimetype="image/png")
    resp.headers["X-Bryes-Scale"] = f"{scale:g}"
    resp.headers["X-Bryes-Origin"] = f"{origin[0]},{origin[1]}"
    resp.headers["X-Bryes-Frame"] = f"{frame[0]},{frame[1]}"
    return resp


def make_app(device_factory=None, locator=None, window_lister=None, frame_provider=None):
    """The Flask app, with every outside dependency injectable so the surface tests model-free."""
    factory = device_factory or _device_factory
    eyes = locator or eyes_locate
    lister = window_lister or list_windows_with_handles
    frame_of = frame_provider or frame_rect_for

    app = Flask(__name__)

    @app.errorhandler(HTTPException)
    def _json_error(err):
        """Every refusal is JSON with a description: the caller is a program, not a browser."""
        return jsonify({"error": err.name, "description": err.description}), err.code

    def _device_for(hwnd):
        if hwnd is None:
            abort(400, description="a window id is required (see GET /windows)")
        return factory(hwnd)

    @app.get("/health")
    def health():
        return jsonify({"ok": True})

    @app.get("/windows")
    def windows():
        """Every targetable window, each with the rectangle IN THE FRAME its screenshot returns.

        Windows reports a rect in screen coordinates, and the frame is the target's monitor, so
        the two differ by that monitor's origin. `image_rect` is the one a click is measured in.
        """
        out = []
        for w in lister():
            hwnd = _parse_window_id(w["id"])
            left, top, right, bottom = frame_of(hwnd)
            rx1, ry1, rx2, ry2 = w["rect"]
            out.append({"id": w["id"], "title": w["title"], "foreground": w["foreground"],
                        "rect": w["rect"],
                        "frame": {"origin": [left, top],
                                  "size": [right - left, bottom - top]},
                        "image_rect": [rx1 - left, ry1 - top, rx2 - left, ry2 - top]})
        return jsonify({"windows": out})

    @app.get("/pointer")
    def pointer():
        """Where the pointer is, in both spaces, and whether it is inside the window.

        A caller that only ever sees frames has no way to know the pointer was left on another
        display; this is the read that answers it, and `inside_window` is the same test the
        body applies before acting.
        """
        hwnd = _parse_window_id(request.args.get("window"))
        device = _device_for(hwnd)
        with _LOCK:
            pos = device.pointer()
        left, top, right, bottom = frame_of(hwnd)
        win = next((w for w in lister() if _parse_window_id(w["id"]) == hwnd), None)
        return jsonify({
            "x": int(pos[0]), "y": int(pos[1]),
            "image_x": int(pos[0]) - left, "image_y": int(pos[1]) - top,
            "inside_frame": pointer_in_rect(pos, (left, top, right, bottom)),
            "inside_window": bool(win) and pointer_in_rect(pos, tuple(win["rect"])),
        })

    @app.get("/downscaleshot")
    def downscaleshot():
        """The frame scaled down, for a caller that wants the whole screen cheaply.

        `scale` defaults to 0.5, which is the factor BRYES's own Eyes use for their overview.
        """
        hwnd = _parse_window_id(request.args.get("window"))
        scale = _scale_arg(request.args.get("scale"), default=0.5, low=0.05, high=1.0)
        with _LOCK:
            png = _device_for(hwnd).screenshot()
        image = Image.open(io.BytesIO(png))
        return _shot_response(_scaled(image, scale), scale, (0, 0), image.size)

    @app.get("/upscaleshot")
    def upscaleshot():
        """One region, cropped then enlarged: the zoom that costs the caller no eyesight.

        The crop is in frame pixels, and every returned pixel maps back through the same rule.
        """
        hwnd = _parse_window_id(request.args.get("window"))
        scale = _scale_arg(request.args.get("scale"), default=2.0, low=1.0, high=4.0)
        with _LOCK:
            png = _device_for(hwnd).screenshot()
        image = Image.open(io.BytesIO(png))
        box = _crop_arg(request.args, image.size)
        crop = image.crop(box)
        return _shot_response(_scaled(crop, scale), scale, (box[0], box[1]), image.size)

    @app.get("/screenshot")
    def screenshot():
        hwnd = _parse_window_id(request.args.get("window"))
        with _LOCK:
            png = _device_for(hwnd).screenshot()
        return send_file(io.BytesIO(png), mimetype="image/png")

    @app.post("/act")
    def act():
        if not request.is_json:
            abort(415, description="send application/json")
        body = request.get_json(silent=True) or {}
        verb = body.get("type")
        if verb not in _VERBS:
            abort(400, description=f"type must be one of {sorted(_VERBS)}")
        hwnd = _parse_window_id(body.get("window"))
        action = {"type": verb}
        for field in ("x", "y", "x2", "y2", "text", "key", "seconds", "direction"):
            if body.get(field) is not None:
                action[field] = body[field]
        if verb in _POINT_VERBS and ("x" not in action or "y" not in action):
            abort(400, description=f"{verb} needs x and y")
        if verb == "drag" and not {"x", "y", "x2", "y2"} <= set(action):
            abort(400, description="drag needs x, y, x2 and y2")
        device = _device_for(hwnd)
        if verb not in device.caps.verbs:
            abort(400, description=f"{device.caps.name} cannot perform {verb}")
        try:
            with _LOCK:
                device.act(action)
        except (RuntimeError, ValueError) as e:
            abort(409, description=str(e))
        return jsonify({"ok": True, "action": action})

    @app.post("/locate")
    def locate():
        if not request.is_json:
            abort(415, description="send application/json")
        body = request.get_json(silent=True) or {}
        instruction = str(body.get("instruction") or "").strip()
        if not instruction:
            abort(400, description="instruction is required")
        hwnd = _parse_window_id(body.get("window"))
        with _LOCK:
            frame = _device_for(hwnd).screenshot()
            try:
                found = eyes(frame, instruction)
            except RuntimeError as e:
                abort(502, description=f"the Eyes failed: {e}")
        return jsonify({"x": int(found["x"]), "y": int(found["y"]),
                        "instruction": instruction})

    @app.get("/profiles")
    def profiles():
        path = str(request.args.get("path") or "").strip()
        if not path or not profile_exists(path):
            abort(404, description=f"no profile at {path!r}")
        merged = load_profiles([path])
        return jsonify({"path": path, "visual": merged["visual"],
                        "operating": merged["operating"]})

    return app


app = make_app()


def main(argv=None):
    print(f"BRYES visual bridge -> http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
