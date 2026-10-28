# Windows Desktop (base)

Base profile for the real Windows desktop body (`WindowsDevice`). Inherited by every
`profiles/windows/<app>/profile.md`.

## Terms & Vocab
- Taskbar — the strip along the bottom edge holding Start, running apps, the notification tray
  and the clock.
- Title bar — the strip at the top of a window: app name on the left, minimize/maximize/close
  on the right.
- Active window — the window with the highlighted title bar. Keys go there, and only there.
- Dialog — a smaller window owned by an app that must be answered before the app continues.
- Monitor — one physical screen. A run captures the monitor that holds its target window.

## Visual
- You are looking at a real Windows desktop on one monitor. Windows from other work may be
  open; they are not the task.
- A window's content sits inside its border. The taskbar and the desktop behind the windows
  belong to no app.
- The active window is drawn on top with its title bar lit; an inactive one is dimmed.

## Operating
- Click a window's title bar before sending it keys. Keys reach the ACTIVE window, never a
  named one.
- A dialog is its own window: answer or dismiss it first, or the next click lands on the
  dialog instead of the app.
- Do not click the taskbar, the tray or the desktop unless the task is about them.
- Coordinates are image pixels of the captured monitor. The body refuses a point outside the
  target window's rectangle, so a far-off point fails rather than clicking beside the target.
- Prefer the app's own keyboard shortcuts over hunting through its menus.
- The pointer is part of the frame: before every action the body checks where the pointer is and
  moves it back inside the target window if it was left on another display. Ask for
  `GET /pointer` to see where it is and whether it is inside.
