"""BRYES task-invocation API -- the JobManager (ADR-008).

Runs a whole task (the native agent/loop.py run() loop) OFF the HTTP request
thread so a multi-minute task never blocks the API, and enforces GLOBAL
SINGLE-FLIGHT: BRYES drives ONE device per run, so at most one task runs at a
time (a second submit raises BusyError -> the server maps it to 409). The job
store is in-memory: a running task holds a live Device session that dies with
the process anyway, so persisting records buys nothing at this stage.

The `runner` is injectable (defaults to loop.run) so the lifecycle can be tested
model-free with a stub (see test_jobs.py) -- no live model or device needed.
"""
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

# Repo root importable so `agent.loop` resolves no matter who launches us.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.loop import _ROOT_DEVICE, _make_device  # noqa: E402
from agent.loop import run as _default_run  # noqa: E402

KNOWN_DEVICES = frozenset(_ROOT_DEVICE)   # valid `device` names accepted at the API boundary


@dataclass
class Job:
    """One task's record: identity, lifecycle status, and its result/error."""

    task_id: str
    goal: str
    status: str = "pending"          # pending -> running -> done | failed
    steps: int | None = None
    result: dict | None = None
    error: str | None = None

    def public(self) -> dict:
        """The JSON-safe view returned by GET /tasks/{id}."""
        return {"task_id": self.task_id, "status": self.status,
                "steps": self.steps, "result": self.result, "error": self.error}


class BusyError(RuntimeError):
    """Raised by submit() when a task is already running (single-flight)."""

    def __init__(self, active_task_id):
        super().__init__(f"a task is already running: {active_task_id}")
        self.active_task_id = active_task_id


class JobManager:
    """In-memory task store + single-flight runner: one task at a time.

    `runner` defaults to agent.loop.run; inject a stub for model-free tests.
    """

    def __init__(self, runner=_default_run, max_jobs=100):
        self._runner = runner
        self._max_jobs = max_jobs            # cap the in-memory store (evict oldest terminal)
        self._jobs: dict[str, Job] = {}
        self._active: str | None = None      # the running task_id, or None
        self._lock = threading.Lock()        # guards _jobs + _active

    def submit(self, goal, device=None, profile=None, max_steps=12) -> str:
        """Start a task in a background daemon thread; return its task_id.

        Raises BusyError if a task is already running (global single-flight).
        `device` is a body-name string ('android'/'linux') or None (auto-select);
        `profile` a path string / list of them.
        """
        with self._lock:
            if self._active is not None:
                raise BusyError(self._active)
            task_id = uuid.uuid4().hex
            self._jobs[task_id] = Job(task_id=task_id, goal=goal)
            self._active = task_id
            self._prune_locked()
        threading.Thread(
            target=self._run_job,
            args=(task_id, goal, device, profile, max_steps),
            daemon=True, name=f"bryes-task-{task_id[:8]}").start()
        return task_id

    def get(self, task_id) -> Job | None:
        with self._lock:
            return self._jobs.get(task_id)

    def _prune_locked(self):
        """Bound the store: drop the oldest TERMINAL (done/failed) jobs beyond
        max_jobs. Caller holds the lock; the active/pending job is never evicted."""
        for tid in list(self._jobs):          # dict preserves insertion order (oldest first)
            if len(self._jobs) <= self._max_jobs:
                break
            if tid != self._active and self._jobs[tid].status in ("done", "failed"):
                del self._jobs[tid]

    def _run_job(self, task_id, goal, device, profile, max_steps):
        """Background worker: run the loop, record result/error, free the slot.

        Writes result/steps BEFORE flipping status to a terminal value, so a
        concurrent poll that sees 'done' always sees the result too.
        """
        job = self._jobs[task_id]
        job.status = "running"
        try:
            # A body-name string maps to a Device; None -> run() auto-selects
            # (ADR-006 embodiment); an already-built Device passes through.
            dev = _make_device(device) if isinstance(device, str) and device else (
                None if isinstance(device, str) else device)
            result = self._runner(goal, device=dev, profile=profile,
                                  max_steps=max_steps, verbose=False)
            job.result = result
            job.steps = result.get("steps") if isinstance(result, dict) else None
            job.status = "done"
        except Exception as e:                 # degrade, never crash the server
            job.error = f"{type(e).__name__}: {e}"
            job.status = "failed"
        finally:
            with self._lock:
                self._active = None
