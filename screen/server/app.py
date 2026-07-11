"""BRYES Phase 1 — The Screen: control API.

Exposes the container's two abilities over HTTP so the other pieces
(Eyes, Brain) can drive it later:

  GET  /health      -> is the virtual display up?
  GET  /screenshot  -> current desktop as a PNG
  POST /action      -> click / move / type / key, executed by xdotool

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


@app.post("/action")
def action():
    data = request.get_json(force=True, silent=True) or {}
    atype = data.get("type")

    if atype in ("click", "move"):
        x, y = data.get("x"), data.get("y")
        if x is None or y is None:
            return jsonify({"error": f"{atype} requires x and y"}), 400
        cmd = ["xdotool", "mousemove", str(int(x)), str(int(y))]
        if atype == "click":
            cmd += ["click", str(data.get("button", 1))]
        r = _run(cmd)
    elif atype == "type":
        r = _run(["xdotool", "type", "--delay", "40", str(data.get("text", ""))])
    elif atype == "key":
        key = data.get("key")
        if not key:
            return jsonify({"error": "key requires 'key' (e.g. Return, Escape, ctrl+a)"}), 400
        r = _run(["xdotool", "key", str(key)])
    else:
        return jsonify({"error": f"unknown action type: {atype!r}"}), 400

    ok = r.returncode == 0
    return jsonify({"ok": ok, "type": atype, "stderr": "" if ok else r.stderr}), (
        200 if ok else 500
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
