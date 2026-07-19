"""BRYES -- model-free tests for the Flask task API routes (ADR-008).

Uses Flask's test_client over an app built with a STUB-runner JobManager -- no
live model, device, or real network. Run: python api/test_server.py
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.jobs import JobManager  # noqa: E402
from api.server import create_app  # noqa: E402

_passed = 0
_failed = 0


def check(name, cond):
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"PASS: {name}")
    else:
        _failed += 1
        print(f"FAIL: {name}")


def wait_until(pred, timeout=3.0, tick=0.01):
    end = time.perf_counter() + timeout
    while time.perf_counter() < end:
        if pred():
            return True
        time.sleep(tick)
    return pred()


def _client(runner):
    return create_app(JobManager(runner=runner)).test_client()


def test_post_and_poll():
    def stub(goal, **kw):
        return {"status": "done", "steps": 2, "history": ["h"], "findings": ["f"]}

    c = _client(stub)
    r = c.post("/tasks", json={"goal": "hello"})
    check("POST /tasks -> 202", r.status_code == 202)
    tid = r.get_json().get("task_id")
    check("202 body has task_id + pending",
          isinstance(tid, str) and r.get_json().get("status") == "pending")
    ok = wait_until(lambda: c.get(f"/tasks/{tid}").get_json().get("status") == "done")
    body = c.get(f"/tasks/{tid}").get_json()
    check("GET -> 200 done + result findings",
          ok and body.get("status") == "done"
          and (body.get("result") or {}).get("findings") == ["f"])


def test_missing_goal():
    c = _client(lambda goal, **kw: {"status": "done"})
    check("POST missing goal -> 400", c.post("/tasks", json={}).status_code == 400)
    check("POST empty goal -> 400", c.post("/tasks", json={"goal": ""}).status_code == 400)


def test_busy_409():
    release = threading.Event()
    started = threading.Event()

    def slow(goal, **kw):
        started.set()
        release.wait(timeout=3.0)
        return {"status": "done", "steps": 1, "history": [], "findings": []}

    c = _client(slow)
    r1 = c.post("/tasks", json={"goal": "first"})
    tid1 = r1.get_json().get("task_id")
    started.wait(timeout=2.0)
    r2 = c.post("/tasks", json={"goal": "second"})
    check("2nd POST while running -> 409", r2.status_code == 409)
    check("409 names active_task_id", r2.get_json().get("active_task_id") == tid1)
    release.set()
    wait_until(lambda: c.get(f"/tasks/{tid1}").get_json().get("status") == "done")


def test_unknown_404():
    c = _client(lambda goal, **kw: {"status": "done"})
    check("GET unknown -> 404", c.get("/tasks/nope").status_code == 404)


def test_health():
    c = _client(lambda goal, **kw: {"status": "done"})
    r = c.get("/health")
    check("GET /health -> 200 ok", r.status_code == 200 and r.get_json().get("ok") is True)


def test_bad_input_400():
    c = _client(lambda goal, **kw: {"status": "done"})
    check("bad max_steps type -> 400",
          c.post("/tasks", json={"goal": "g", "max_steps": "five"}).status_code == 400)
    check("max_steps < 1 -> 400",
          c.post("/tasks", json={"goal": "g", "max_steps": 0}).status_code == 400)
    check("unknown device -> 400",
          c.post("/tasks", json={"goal": "g", "device": "bogus"}).status_code == 400)


def main():
    test_post_and_poll()
    test_missing_goal()
    test_busy_409()
    test_unknown_404()
    test_health()
    test_bad_input_400()
    print()
    if _failed == 0:
        print(f"ALL PASS ({_passed})")
        return 0
    print(f"{_failed} FAILED, {_passed} passed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
