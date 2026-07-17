# Linux Desktop (base)

Base profile for the Linux desktop container body (Xvfb + fluxbox). Inherited by every
`profiles/linux/<app>/profile.md`.

## Terms & Vocab
- Window title bar — the strip at the top of each app window (title + minimize/maximize/close).
- Desktop — the empty background behind the windows (fluxbox); a right-click there opens its menu.
- Focused window — the window currently on top / receiving input.

## Visual
- You are looking at a Linux desktop (a windowed GUI). Apps open in their own windows that can
  overlap; the focused window is on top.
- Text you type goes to the window/field that currently has focus — check which window is focused
  before typing.

## Operating
- Interact with the mouse: click, double_click, right_click, hover, scroll, drag.
- A full command line is available via the `shell` action — prefer it for files, system info,
  networking, and text processing rather than driving a terminal by vision.
- Keys use X keysyms (Return, Escape, Tab, ctrl+a); the body normalizes common synonyms (Enter → Return).
