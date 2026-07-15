"""BRYES Phase 1 — The Screen: control API.

Exposes the container's two abilities over HTTP so the other pieces
(Eyes, Brain) can drive it later:

  GET  /health      -> is the virtual display up?
  GET  /screenshot  -> current desktop as a PNG
  GET  /pointer     -> current mouse (x, y) — a model-free way to assert a point
                       action (hover/click/drag/...) landed where intended
  POST /action      -> click / double_click / right_click / hover / scroll /
                       drag / type / key, executed by xdotool
  POST /exec        -> run a non-interactive shell command inside this container
                       (the Tier-2 effector), returning {ok, exit_code, stdout, stderr}

The GUI endpoints talk to the Xvfb display named by $DISPLAY; /exec runs in the
container's plain environment (no display needed).
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


_MAX_OUT = 4096  # cap each stream fed back to the Brain — bounds output SIZE, not time


def _clip(s, limit=_MAX_OUT):
    """Keep output small enough for the Brain's context: head + tail with an elision
    marker. Unbounded stdout would blow the Brain's context and cost."""
    s = s or ""
    if len(s) <= limit:
        return s
    half = limit // 2
    return f"{s[:half]}\n...[{len(s) - limit} chars elided]...\n{s[-half:]}"


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


@app.post("/exec")
def exec_command():
    """Tier-2 shell channel: run a NON-INTERACTIVE command inside this (sandboxed)
    container and return structured output. Runs to completion — it cannot answer a
    mid-run prompt, so the caller uses flags/pipes/heredocs or the optional `stdin`
    (interactive terminals are driven with vision instead).

    A timeout is the ONLY recovery valve: a blocking command would otherwise freeze
    the caller's loop with no way back in, so every call is time-bounded. Default 30s;
    the caller may extend it (e.g. an install) up to a 5-min ceiling that bounds the
    worst-case freeze. Safe because the container has no host mounts / socket / secrets.
    """
    data = request.get_json(force=True, silent=True) or {}
    command = data.get("command")
    if not command or not str(command).strip():
        return jsonify({"error": "exec requires a non-empty 'command'"}), 400

    try:
        t = int(data.get("timeout", 30))
    except (TypeError, ValueError):
        t = 30
    t = max(1, min(t, 300))                     # clamp [1s, 300s]

    stdin = data.get("stdin")
    try:
        r = subprocess.run(
            str(command), shell=True, capture_output=True, text=True,
            errors="replace",     # non-UTF-8 output (e.g. binary) -> readable, never a crash
            timeout=t, input=(str(stdin) if stdin is not None else None),
        )
    except subprocess.TimeoutExpired:
        return jsonify({
            "ok": False, "exit_code": None, "stdout": "",
            "stderr": f"timed out after {t}s", "timed_out": True,
        }), 200

    return jsonify({
        "ok": r.returncode == 0,
        "exit_code": r.returncode,
        "stdout": _clip(r.stdout),
        "stderr": _clip(r.stderr),
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
