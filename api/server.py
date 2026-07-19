"""BRYES task-invocation API -- the Flask surface (ADR-008).

Two task routes over the JobManager, plus a health check, bound to LOCALHOST:
  POST /tasks {goal, device?, profile?, max_steps?}
       -> 202 {task_id, status:"pending"}
       -> 409 {error:"busy", active_task_id}   if a task is already running
       -> 400 {error}                           if goal is missing/empty
  GET  /tasks/<task_id>
       -> 200 {task_id, status, steps, result, error}
       -> 404 {error}                           if the task_id is unknown
  GET  /health -> 200 {ok:true}

Run: python api/server.py  (or python -m api.server)  -> http://127.0.0.1:8100
The task loop runs off-thread in the JobManager, so POST returns immediately and
GET polls. This is the Werkzeug dev server -- fine for localhost / step 0, NOT a
production WSGI server (swap to waitress/gunicorn when binding beyond localhost).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, request  # noqa: E402

from api.jobs import KNOWN_DEVICES, BusyError, JobManager  # noqa: E402

HOST = "127.0.0.1"
PORT = 8100


def create_app(manager=None):
    """Build the Flask app over a JobManager. Inject a stub-backed manager in
    tests (see test_server.py); production uses the default real-loop manager."""
    manager = manager or JobManager()
    app = Flask(__name__)

    @app.post("/tasks")
    def start_task():
        body = request.get_json(silent=True) or {}
        goal = body.get("goal")
        if not goal or not isinstance(goal, str):
            return jsonify({"error": "a non-empty 'goal' string is required"}), 400
        kw = {}
        device = body.get("device")
        if device is not None:
            if device not in KNOWN_DEVICES:
                return jsonify({"error": f"unknown device {device!r}; "
                                        f"use one of {sorted(KNOWN_DEVICES)} or omit to auto-select"}), 400
            kw["device"] = device
        max_steps = body.get("max_steps")
        if max_steps is not None:
            if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
                return jsonify({"error": "'max_steps' must be a positive integer"}), 400
            kw["max_steps"] = max_steps
        if body.get("profile") is not None:     # run() validates the profile path itself
            kw["profile"] = body["profile"]
        try:
            task_id = manager.submit(goal, **kw)
        except BusyError as e:
            return jsonify({"error": "busy", "active_task_id": e.active_task_id}), 409
        return jsonify({"task_id": task_id, "status": "pending"}), 202

    @app.get("/tasks/<task_id>")
    def get_task(task_id):
        job = manager.get(task_id)
        if job is None:
            return jsonify({"error": "unknown task_id"}), 404
        return jsonify(job.public()), 200

    @app.get("/health")
    def health():
        return jsonify({"ok": True}), 200

    return app


def main():
    print(f"BRYES task API on http://{HOST}:{PORT}  "
          "(POST /tasks, GET /tasks/<id>, GET /health)")
    create_app().run(host=HOST, port=PORT, threaded=True)


if __name__ == "__main__":
    main()
