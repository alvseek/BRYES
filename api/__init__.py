"""BRYES task-invocation API (ADR-008): a host-side async HTTP task service over
the native agent/loop.py run() loop. `jobs` owns the JobManager; `server` is the
Flask surface. Distinct from screen/server/ (the container's *body* API)."""
