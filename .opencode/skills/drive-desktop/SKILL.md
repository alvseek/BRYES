---
name: drive-desktop
description: Drive a real Windows application through BRYES's Windows Bridge (gated), with the calling agent observing, acting, and verifying. Use when the user runs /drive-desktop, asks how to operate an app with BRYES, or wants another agent to take over a Windows application.
---

Read [`docs/procedures/drive-the-desktop.md`](../../../docs/procedures/drive-the-desktop.md) and follow it exactly.

That file is the canonical procedure and the only copy. This file exists so the skill is
discoverable as `/drive-desktop`; it deliberately carries no procedure text of its own.

The four facts that matter before anything else:

- `BRYES_ALLOW_HOST=1` is required in the Bridge server's environment to act; the Bridge has no shell endpoint.
- Select the exact window handle from `/windows`; prefer a target you launched and verify any existing target before acting.
- Kill only a process you created.
- If the application publishes an API (Unreal's Python / Remote Control API), use that instead of
  pixels; see ADR-001.
