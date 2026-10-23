---
project: "BRYES"
tags: [docker, container, entrypoint, crlf, keyboard, focus, xdotool, xev, key-hold]
description: "Why the Screen container fails to boot from a CRLF checkout, when it must be rebuilt, and how keyboard input actually reaches a window inside it."
created: "2026-10-23"
updated: "2026-10-23"
---

# The Screen container: booting it, rebuilding it, getting keys into it

## **PURPOSE**

Load before rebuilding, starting, or driving the Docker Screen body. Three failures here each
look like something else: a crash loop that reads as a broken image, a stale image that reads as
a broken edit, and silence that reads as a broken key action.

## **QUICK REFERENCE**

- Rebuild after **any** edit to `screen/server/app.py`: `cd screen && docker compose up -d --build`
- Boot failure whose log is only `bash\r: No such file or directory` → `scripts/entrypoint.sh` has CRLF
- Check it: the file must contain **zero** carriage returns
- Give a window focus before sending keys: `xdotool windowactivate <id>` **then** `xdotool windowfocus <id>`
- Prove a held key: `xterm -e sh -c 'xev > /tmp/xev.txt'`, focus that window, send `key_hold`, read the timestamps

## **DETAILS**

### A CRLF `entrypoint.sh` makes the container restart-loop

On 2026-10-23 the container would not stay up after a rebuild. The log held one line, repeated:
`/usr/bin/env: 'bash\r': No such file or directory`. The cause was `screen/scripts/entrypoint.sh`
being **stored in git with 48 carriage returns**: a CRLF shebang makes the kernel look for an
interpreter named `bash\r`.

It had gone unnoticed because `core.autocrlf=true` on Windows checks that blob out as CRLF, so the
working copy matched the blob and `git status` was clean the whole time. Docker copies the working
tree, not the blob, so the container got the broken bytes.

Two things are needed, and the second is the one people skip:

1. `*.sh text eol=lf` in `.gitattributes`, so a checkout cannot re-create it.
2. The **blob itself** must be LF. An attribute governs what git materialises; it does not fix a
   CRLF blob already committed, and it does not fix a tree delivered by `scp` or `docker cp`.

### An edit to the server needs `--build`

`docker compose up -d` reuses the existing image. `app.py` is baked in, so a server change without
`--build` leaves the old code serving and every new branch appears missing.

### Keyboard input needs real focus, not just activation

Driving keys into an xterm with `xdotool type` or `xdotool keydown` delivered nothing while
`xdotool windowactivate` had been called on it. `getwindowfocus` still reported the window, yet the
characters never arrived; `xdotool windowfocus` on that same window made them land.
Practical rule: activate **and** focus, or click the target, before sending any keyboard action.
A pointer action is unaffected, which is why the Hands suite never caught it.

### A held key, and how it was proved live

`key_hold` (`{type: key_hold, key, seconds}`, 0.1 to 5 s, default 1.0) presses down, waits, releases.
Proven with `xev` inside the container: a 1.2 s hold produced `KeyPress` at t=3634499 and
`KeyRelease` at t=3635713 (1,214 ms, 15 auto-repeat pairs), so the X server held the key rather than
tapping it twice. The phone does not offer the action: `input keyevent` has no held state.

## **SOURCES**

- 2026-10-23 session (software-architect) building `key_hold`, with the container rebuilt live.
- `docs/backlog.md` — the `key_hold` entry and the focus finding.
- `.gitattributes` — the `*.sh` rule and its reason, in the file itself.
