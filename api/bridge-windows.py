"""BRYES visual bridge -- a primitive-level HTTP surface for an outside agent (SP-6).

No Brain, no goal, no loop. The caller lists the windows, screenshots one, points at a thing
by description, and acts at a pixel; BRYES does as it is told and reports what is there.

  GET  /health                            -> {ok: true}
  GET  /windows                           -> {frame: {origin, size}, windows: [{id, title, rect,
                                              image_rect, foreground, ...}]}
  GET  /pointer[?window=<id>]             -> {x, y}, plus window-relative fields when selected
  GET  /screenshot?window=<id>            -> PNG of the body's current frame, 1:1
  GET  /downscaleshot?window=&scale=0.5   -> PNG scaled down, with the mapping headers
  GET  /upscaleshot?window=&x1=&y1=&x2=&y2=&scale=2 -> PNG of that crop, enlarged, same headers
  POST /act      {window, type, x?, y?, x2?, y2?, text?, key?, seconds?, direction?, miliseconds?}
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

Run: python api/bridge-windows.py  ->  http://127.0.0.1:8110
"""
import ctypes
import io
import math
import re
import sys
import threading
import time
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

# Input verbs are checked against the body's capabilities. Delay is handled by the Bridge,
# without forwarding it to the body or sending desktop input.
_POINT_VERBS = {"click", "double_click", "right_click", "hover", "scroll"}
_VERBS = _POINT_VERBS | {"drag", "scroll", "type", "key", "key_hold", "delay"}


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


def _resolve_target(args, lister, required=True):
    """Resolve one selector against the live list without choosing an arbitrary match."""
    has_window, has_title = "window" in args, "title" in args
    if has_window and has_title:
        abort(400, description="send either window or title, not both")
    if not has_window and not has_title:
        if required:
            abort(400, description="a window or title is required")
        return None, None
    if has_window:
        raw = args["window"]
        if not isinstance(raw, str) or not re.fullmatch(r"(?:0[xX])?[0-9a-fA-F]+", raw.strip()):
            abort(400, description="window must be a positive hexadecimal window id")
        hwnd = _parse_window_id(raw)
        if hwnd is None or hwnd <= 0:
            abort(400, description="window must be a positive hexadecimal window id")
        matches = [w for w in lister() if _parse_window_id(w["id"]) == hwnd]
    else:
        title = args["title"]
        if not isinstance(title, str) or not title.strip():
            abort(400, description="title must be a nonempty string")
        needle = title.strip().casefold()
        matches = [w for w in lister() if needle in w["title"].casefold()]
    if not matches:
        abort(404, description="no matching window")
    if len(matches) > 1:
        response = jsonify({"error": "Conflict", "description": "multiple matching windows",
                            "matches": [{"id": w["id"], "title": w["title"]}
                                        for w in matches]})
        response.status_code = 409
        abort(response)
    selected = matches[0]
    return _parse_window_id(selected["id"]), selected


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _action_mapping(body):
    """Optional screenshot-to-frame mapping, supplied by the caller, never stored."""
    if "mapping" not in body:
        return None
    mapping = body["mapping"]
    if not isinstance(mapping, dict):
        abort(400, description="mapping must be an object with scale and origin")
    scale, origin = mapping.get("scale"), mapping.get("origin")
    if not _finite_number(scale) or scale <= 0:
        abort(400, description="mapping.scale must be a finite positive number")
    if (not isinstance(origin, list) or len(origin) != 2
            or not all(_finite_number(value) for value in origin)):
        abort(400, description="mapping.origin must contain two finite numbers")
    return scale, origin


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
    if isinstance(raw, bool):
        abort(400, description="scale must be a number")
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
        if any(isinstance(args[k], bool) or not isinstance(args[k], (int, str))
               for k in ("x1", "y1", "x2", "y2")):
            raise ValueError("not an integer")
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

    @app.errorhandler(Exception)
    def _unexpected_error(err):
        app.logger.exception("Unexpected Bridge failure", exc_info=err)
        return jsonify({"error": "Internal Server Error",
                        "description": "An unexpected Bridge error occurred"}), 500

    def device_call(fn, *args):
        try:
            return fn(*args)
        except (RuntimeError, ValueError) as exc:
            abort(409, description=str(exc))

    def _device_for(hwnd):
        if hwnd is None:
            abort(400, description="a window id is required (see GET /windows)")
        return device_call(factory, hwnd)

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
        hwnd, win = _resolve_target(request.args, lister, required=False)
        device = device_call(factory, hwnd)
        with _LOCK:
            pos = device_call(device.pointer)
        if pos is None:
            abort(503, description="pointer position is unavailable")
        if hwnd is None:
            return jsonify({"x": int(pos[0]), "y": int(pos[1])})
        left, top, right, bottom = frame_of(hwnd)
        return jsonify({
            "x": int(pos[0]), "y": int(pos[1]),
            "image_x": int(pos[0]) - left, "image_y": int(pos[1]) - top,
            "inside_frame": pointer_in_rect(pos, (left, top, right, bottom)),
            "inside_window": bool(win) and pointer_in_rect(pos, tuple(win["rect"])),
        })

    def capture(kind):
        if request.method == "POST":
            if not request.is_json:
                abort(415, description="send application/json")
            args = request.get_json(silent=True)
            if not isinstance(args, dict):
                abort(400, description="send a JSON object")
            raise_window = args.get("raise", False)
            if not isinstance(raise_window, bool):
                abort(400, description="raise must be a boolean")
        else:
            args = request.args
            if "raise" in args:
                abort(400, description="use POST to raise a window")
            raise_window = False
        hwnd, win = _resolve_target(args, lister)
        scale = None
        if kind == "down":
            if request.method == "POST" and "scale" in args and args["scale"] is None:
                abort(400, description="scale must be a number")
            scale = _scale_arg(args.get("scale"), 0.5, 0.05, 1.0)
        elif kind == "up":
            if request.method == "POST" and "scale" in args and args["scale"] is None:
                abort(400, description="scale must be a number")
            scale = _scale_arg(args.get("scale"), 2.0, 1.0, 4.0)
        if raise_window and kind == "up":
            left, top, right, bottom = frame_of(hwnd)
            _crop_arg(args, (right - left, bottom - top))
        device = _device_for(hwnd)
        with _LOCK:
            if raise_window:
                pos = device_call(device.pointer)
                if pos is None:
                    abort(503, description="pointer position is unavailable")
                left, top, _, _ = frame_of(hwnd)
                x1, y1, x2, y2 = win["rect"]
                x, y = pos if pointer_in_rect(pos, win["rect"]) else (
                    (x1 + x2) // 2, (y1 + y2) // 2)
                device_call(device.act, {"type": "hover", "x": x - left, "y": y - top})
                time.sleep(0.3)
            png = device_call(device.screenshot)
        if kind == "plain":
            return send_file(io.BytesIO(png), mimetype="image/png")
        image = Image.open(io.BytesIO(png))
        if kind == "up":
            box = _crop_arg(args, image.size)
            return _shot_response(_scaled(image.crop(box), scale), scale, box[:2], image.size)
        return _shot_response(_scaled(image, scale), scale, (0, 0), image.size)

    @app.route("/downscaleshot", methods=["GET", "POST"])
    def downscaleshot():
        return capture("down")

    @app.route("/upscaleshot", methods=["GET", "POST"])
    def upscaleshot():
        return capture("up")

    @app.route("/screenshot", methods=["GET", "POST"])
    def screenshot():
        return capture("plain")

    @app.post("/act")
    def act():
        if not request.is_json:
            abort(415, description="send application/json")
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            abort(400, description="send a JSON object")
        batch = "actions" in body
        if batch and "type" in body:
            abort(400, description="send either type or actions, not both")
        items = body.get("actions") if batch else [body]
        if not isinstance(items, list) or not items:
            abort(400, description="actions must be a non-empty array")
        mapping = _action_mapping(body)
        hwnd, _ = _resolve_target(body, lister)
        device = _device_for(hwnd)
        actions = []
        # Validate every action before sending any input. Geometry/focus still depend on
        # live desktop state and are checked by the device at each point of execution.
        for index, item in enumerate(items):
            prefix = f"actions[{index}]: " if batch else ""

            def refuse(message):
                abort(400, description=prefix + message)

            if not isinstance(item, dict):
                refuse("each action must be an object")
            verb = item.get("type")
            if not isinstance(verb, str) or verb not in _VERBS:
                refuse(f"type must be one of {sorted(_VERBS)}")
            if batch and ("window" in item or "title" in item):
                refuse("window and title belong at the request level")
            if batch and "mapping" in item:
                refuse("mapping belongs at the request level")
            if verb == "delay":
                value = item.get("miliseconds")
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or value < 0):
                    refuse("delay needs finite nonnegative numeric miliseconds")
                try:
                    finite = math.isfinite(value)
                except OverflowError:
                    finite = False
                if not finite:
                    refuse("delay needs finite nonnegative numeric miliseconds")
                actions.append({"type": verb, "miliseconds": value})
                continue
            if verb not in device.caps.verbs:
                refuse(f"{device.caps.name} cannot perform {verb}")
            action = {"type": verb}
            for field in ("x", "y", "x2", "y2", "text", "key", "seconds", "direction"):
                if item.get(field) is not None:
                    action[field] = item[field]
            points = ("x", "y", "x2", "y2") if verb == "drag" else (
                ("x", "y") if verb in _POINT_VERBS else ())
            for field in points:
                value = action.get(field)
                if not _finite_number(value):
                    refuse(f"{verb} needs finite numeric {field}")
            if mapping and points:
                scale, origin = mapping
                for field in points:
                    try:
                        value = origin[0 if field in ("x", "x2") else 1] + action[field] / scale
                        if not _finite_number(value):
                            raise ValueError
                        action[field] = round(value)
                    except (OverflowError, ValueError):
                        refuse(f"mapping produces a non-finite frame coordinate for {field}")
            field = "text" if verb == "type" else "key" if verb in {"key", "key_hold"} else None
            if field and not isinstance(action.get(field), str):
                refuse(f"{verb} needs a string {field}")
            if field == "key" and not action[field].strip():
                refuse("key must not be empty")
            if verb == "scroll" and action.get("direction", "down") not in ("up", "down"):
                refuse("direction must be up or down")
            if verb == "key_hold" and "seconds" in action:
                value = action["seconds"]
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or not math.isfinite(value)):
                    refuse("seconds must be a finite number")
            actions.append(action)
        completed = []
        with _LOCK:
            for index, action in enumerate(actions):
                try:
                    if action["type"] == "delay":
                        time.sleep(action["miliseconds"] / 1000)
                    else:
                        device.act(action)
                except Exception as e:
                    status = 409 if isinstance(e, (RuntimeError, ValueError)) else 500
                    if status == 500:
                        app.logger.exception("Unexpected Bridge action failure")
                    description = str(e) if status == 409 else "An unexpected Bridge error occurred"
                    if batch:
                        return jsonify({"ok": False, "error": "Action failed",
                                        "description": description, "completed": completed,
                                        "failed_index": index, "failed_action": action}), status
                    if status == 409:
                        abort(409, description=str(e))
                    raise
                completed.append(action)
        if batch:
            return jsonify({"ok": True, "actions": completed})
        return jsonify({"ok": True, "action": action})

    @app.post("/locate")
    def locate():
        if not request.is_json:
            abort(415, description="send application/json")
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            abort(400, description="send a JSON object")
        instruction = str(body.get("instruction") or "").strip()
        if not instruction:
            abort(400, description="instruction is required")
        hwnd, _ = _resolve_target(body, lister)
        with _LOCK:
            frame = device_call(_device_for(hwnd).screenshot)
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
