"""BRYES Phase 1 — The Screen: control API.

Exposes the container's two abilities over HTTP so the other pieces
(Eyes, Brain) can drive it later:

  GET  /health      -> is the virtual display up?
  GET  /screenshot  -> current desktop as a PNG
  GET  /pointer     -> current mouse (x, y) — a model-free way to assert a point
                       action (hover/click/drag/...) landed where intended
  POST /action      -> click / double_click / right_click / hover / scroll /
                       drag / type / key, executed by xdotool

Everything talks to the Xvfb display named by $DISPLAY.
"""
import os
import subprocess
import tempfile

from flask import Flask, request, jsonify, send_file

DISPLAY = os.environ.get("DISPLAY", ":99")
app = Flask(__name__)


def _run(cmd):
    """Run a command against the virtual display, capturing output."""
    env = dict(os.environ, DISPLAY=DISPLAY)
    return subprocess.run(cmd, env=env, capture_output=True, text=True)


@app.get("/health")
def health():
    r = _run(["xdpyinfo"])
    ok = r.returncode == 0
    return jsonify({"status": "ok" if ok else "no-display", "display": DISPLAY}), (
        200 if ok else 503
    )


@app.get("/screenshot")
def screenshot():
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    r = _run(["scrot", "-o", path])
    if r.returncode != 0 or not os.path.exists(path) or os.path.getsize(path) == 0:
        return jsonify({"error": "screenshot failed", "stderr": r.stderr}), 500
    return send_file(path, mimetype="image/png")


@app.get("/pointer")
def pointer():
    """Where the mouse is right now, as {x, y}. Deterministic and model-free — lets a
    test assert that hover/click/drag/... moved the pointer to the intended pixel."""
    r = _run(["xdotool", "getmouselocation", "--shell"])
    if r.returncode != 0:
        return jsonify({"error": "getmouselocation failed", "stderr": r.stderr}), 500
    vals = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            vals[k] = v
    return jsonify({"x": int(vals.get("X", 0)), "y": int(vals.get("Y", 0))})


# Actions that act at a screen coordinate all need (x, y). Each primitive stays
# atomic — one xdotool invocation that does exactly what its name says, nothing
# hidden: `type` never clicks, `hover` never clicks, etc. Composition (focus-then-
# type, locate-then-click) is the caller's job, one level up.
_POINT_ACTIONS = ("click", "double_click", "right_click", "hover", "scroll", "drag")


@app.post("/action")
def action():
    data = request.get_json(force=True, silent=True) or {}
    atype = data.get("type")

    if atype in _POINT_ACTIONS:
        x, y = data.get("x"), data.get("y")
        if x is None or y is None:
            return jsonify({"error": f"{atype} requires x and y"}), 400
        x, y = str(int(x)), str(int(y))

    if atype == "click":                       # left-click at (x, y)
        cmd = ["xdotool", "mousemove", x, y, "click", str(data.get("button", 1))]
    elif atype == "double_click":              # open / activate
        cmd = ["xdotool", "mousemove", x, y, "click", "--repeat", "2", "--delay", "120", "1"]
    elif atype == "right_click":               # context menu
        cmd = ["xdotool", "mousemove", x, y, "click", "3"]
    elif atype == "hover":                     # move the pointer only (reveal menus/tooltips)
        cmd = ["xdotool", "mousemove", x, y]
    elif atype == "scroll":                    # wheel-scroll at (x, y); button 4=up, 5=down
        button = "4" if str(data.get("direction", "down")).lower() == "up" else "5"
        amount = max(1, int(data.get("amount", 3)))
        cmd = ["xdotool", "mousemove", x, y, "click", "--repeat", str(amount), button]
    elif atype == "drag":                      # press at (x, y), release at (x2, y2)
        x2, y2 = data.get("x2"), data.get("y2")
        if x2 is None or y2 is None:
            return jsonify({"error": "drag requires x2 and y2 (the drop point)"}), 400
        cmd = ["xdotool", "mousemove", x, y, "mousedown", "1",
               "mousemove", str(int(x2)), str(int(y2)), "mouseup", "1"]
    elif atype == "type":                      # type into whatever is focused (no click)
        cmd = ["xdotool", "type", "--delay", "40", str(data.get("text", ""))]
    elif atype == "key":                       # a key or chord, e.g. Return, ctrl+a
        key = data.get("key")
        if not key:
            return jsonify({"error": "key requires 'key' (e.g. Return, Escape, ctrl+a)"}), 400
        cmd = ["xdotool", "key", str(key)]
    else:
        return jsonify({"error": f"unknown action type: {atype!r}"}), 400

    r = _run(cmd)
    ok = r.returncode == 0
    return jsonify({"ok": ok, "type": atype, "stderr": "" if ok else r.stderr}), (
        200 if ok else 500
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
