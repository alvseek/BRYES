"""BRYES -- model-free tests for the task API JobManager (ADR-008).

No live model or device: a STUB runner is injected, so these assert the lifecycle
(pending -> running -> done / failed), single-flight (the 409 source), device
pass-through, and error capture -- deterministically, in well under a second.
Run: python api/test_jobs.py
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.jobs import BusyError, JobManager  # noqa: E402

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


def test_happy_path():
    seen = {}

    def stub(goal, **kw):
        seen["goal"] = goal
        seen["kw"] = kw
        return {"status": "done", "steps": 4, "history": ["did x"], "findings": ["f1"]}

    m = JobManager(runner=stub)
    tid = m.submit("do a thing", profile="linux/x", max_steps=7)
    check("submit returns a task_id", isinstance(tid, str) and len(tid) > 0)
    ok = wait_until(lambda: m.get(tid).status == "done")
    job = m.get(tid)
    check("status reaches done", ok and job.status == "done")
    check("result stored verbatim", job.result == {"status": "done", "steps": 4,
          "history": ["did x"], "findings": ["f1"]})
    check("steps pulled from result", job.steps == 4)
    check("runner got the goal", seen.get("goal") == "do a thing")
    check("runner got max_steps + profile", seen["kw"].get("max_steps") == 7
          and seen["kw"].get("profile") == "linux/x")
    check("device None -> runner device None (auto-select)", seen["kw"].get("device") is None)
    check("no error on success", job.error is None)


def test_single_flight():
    release = threading.Event()
    started = threading.Event()

    def slow(goal, **kw):
        started.set()
        release.wait(timeout=3.0)
        return {"status": "done", "steps": 1, "history": [], "findings": []}

    m = JobManager(runner=slow)
    tid1 = m.submit("first")
    started.wait(timeout=2.0)
    check("first task is running", m.get(tid1).status == "running")
    raised = None
    try:
        m.submit("second")
    except BusyError as e:
        raised = e
    check("2nd submit raises BusyError", raised is not None)
    check("BusyError names the active task", raised is not None and raised.active_task_id == tid1)
    release.set()
    wait_until(lambda: m.get(tid1).status == "done")
    check("first completes after release", m.get(tid1).status == "done")
    tid3 = m.submit("third")     # slot must be free again
    check("slot freed after completion", isinstance(tid3, str) and tid3 != tid1)
    wait_until(lambda: m.get(tid3).status == "done")


def test_failure():
    def boom(goal, **kw):
        raise ValueError("kaboom")

    m = JobManager(runner=boom)
    tid = m.submit("will fail")
    wait_until(lambda: m.get(tid).status == "failed")
    job = m.get(tid)
    check("failed status on runner exception", job.status == "failed")
    check("error captures type + message",
          job.error is not None and "ValueError" in job.error and "kaboom" in job.error)
    freed = m.submit("next")     # would raise BusyError if the slot weren't freed
    check("slot freed after failure", isinstance(freed, str))


def test_get_unknown():
    m = JobManager(runner=lambda goal, **kw: {"status": "done"})
    check("get(unknown) returns None", m.get("does-not-exist") is None)


def test_device_passthrough():
    seen = {}

    def stub(goal, **kw):
        seen["device"] = kw.get("device")
        return {"status": "done", "steps": 0, "history": [], "findings": []}

    dummy = object()
    m = JobManager(runner=stub)
    tid = m.submit("g", device=dummy)
    wait_until(lambda: m.get(tid).status == "done")
    check("non-string device passes straight through", seen.get("device") is dummy)


def test_eviction():
    m = JobManager(runner=lambda goal, **kw: {"status": "done", "steps": 0}, max_jobs=3)
    ids = []
    for i in range(5):
        tid = m.submit(f"task{i}")
        ids.append(tid)
        wait_until(lambda t=tid: m.get(t).status == "done")   # single-flight: finish before next
    check("store bounded to max_jobs", len([t for t in ids if m.get(t) is not None]) <= 3)
    check("oldest job evicted", m.get(ids[0]) is None)
    check("newest job retained", m.get(ids[-1]) is not None)


def main():
    test_happy_path()
    test_single_flight()
    test_failure()
    test_get_unknown()
    test_device_passthrough()
    test_eviction()
    print()
    if _failed == 0:
        print(f"ALL PASS ({_passed})")
        return 0
    print(f"{_failed} FAILED, {_passed} passed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
