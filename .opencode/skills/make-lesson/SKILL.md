---
name: make-lesson
description: Turn a running application into a tutorial lesson backed by real screenshots. Use when the user runs /make-lesson, asks for the lesson procedure, or wants a step-by-step guide built from captures of their own screen.
---

Read [`docs/procedures/make-a-lesson.md`](../../../docs/procedures/make-a-lesson.md) and follow it exactly.

That file is the canonical procedure, and the only copy. This file exists so the skill is discoverable and shows up as `/make-lesson`; it deliberately carries no procedure text of its own, because two copies of a procedure drift and the drifted one is always the one somebody is reading.

Repo-specific facts the procedure assumes:

- capture: `python capture.py --lesson <id> --step N --phase before|after|result --window "<title>" --note "..."`
- build: `python lesson.py lessons/<id>`
- gate tests: `python test_lesson.py`, `python devices/test_windows.py`
