# SP-4 — Windows and Unreal profiles

*Quick Wizard record. This level has no plan template, so this file is the decision and outcome record the council needs, not a step-by-step plan.*

## Project Info
- **Project**: BRYES
- **Date**: 2026-10-28
- **Agent**: Claude Software Architect
- **Source Protocol**: `/quick-wizard`, launched as sub-plan SP-4 of the council
- **Theme**: the Windows and Unreal profiles, written as vocabulary that both the Eyes and an outside caller share

## Inherited Context

### From the Parent Plan
- **Parent plan**: `core-plan.md` (this folder), sub-plan SP-4, requirement R2.
- **Assigned scope**: `profiles/windows/profile.md`, `profiles/windows/unreal-editor/profile.md`, and the catalog section that lists them.

| # | Inherited decision | Chosen | Parent's reason | Status |
|---|--------------------|--------|-----------------|--------|
| 1 | Where the profile knowledge comes from | Basic Windows and Unreal Editor knowledge, never derived from the `lsgi` lessons | "lessons are for me, not for agents, the knowledge should be populated from basic windows + unreal knowledge (like the previous android / linux / whatsapp / chrome)" | Settled |
| 2 | Who reads the profiles | Both sides. The Eyes get the Visual half, the outside caller gets the same vocabulary so `locate` instructions are phrased in words the Eyes were primed with | "both inside and outside agent need to have those vocabulary so they can communicate well, especially the locate by description" | Settled |
| 3 | Where Unreal puts a new window | The primary monitor, so the profile must tell a caller to move the editor there first | "unreal always want to show new window inside main monitor" | Settled |

- **Integration contracts**: none produced. The profiles are read by the loop (`load_profiles`) and, once SP-6 exists, served to the caller as text.
- **Pushed-down open items**: none.

### From Pre-Planning Discussion
- **Discussion**: none separate from the parent handoff.

## Protocol (Quick Wizard)

- **Scope gate — stays Quick Wizard.** None of the escalation criteria hold: two new text files and one catalog line later, no interdependent code, nothing irreversible, no bug hunt, no formal comparison or ADR, and it fits one session.
- **Rounds — none fired, each skipped out loud because it was settled before this plan existed.** Scope: R2 and the council handoff. Product-flow: no UI, these are files the loop reads. Technical-core: the profile format already exists (Terms & Vocab / Visual / Operating, inheriting up the path), so there is no new mechanism to choose. Integration-points: `load_profiles` and the catalog both exist and nothing new is called.
- **Process note, recorded rather than smoothed over.** The files were written before this procedure was read, so both statements above were produced after execution instead of before it. The content did not change as a result, because every decision had already been settled in conversation, but the order was wrong: QW requires investigate, gate, rounds, then execute.

## What Was Built

- **`profiles/windows/profile.md`** — the base desktop: taskbar, title bar, active window, dialogs, monitor, and the coordinate rule a caller needs (image pixels of the captured monitor; the body refuses points outside the target window).
- **`profiles/windows/unreal-editor/profile.md`** — the editor, inheriting the base: document tabs, toolbar, graph canvas, node, pin, wire, My Blueprint, Details, Content Browser, breadcrumb, then the operating sequences (Ctrl+P, right-click-create, pin drag, Details dropdown, compile, save, and the primary-monitor window rule).

Both were written from general knowledge of Windows and UE5, with two facts taken from my own captures this session rather than from the lessons: the "N Unsaved" indicator in the status bar, and the editor's behaviour of opening Project Settings on the primary monitor.

## Verification

```
profile_exists('windows/unreal-editor') -> True
load_profiles(['windows/unreal-editor']) -> visual 2718 chars, operating 3433 chars
first visual head: "WINDOWS UI ELEMENTS:"   (the base merged, then the editor labelled)
python test_profiles.py -> ALL PASS (19 checks), including "every catalog path resolves on disk"
```

## The One Item Held, Now Landed

The `## windows` section in `profiles/index.md` was held while R9 was in flight, because listing the body is what lets a bare goal select the real desktop.

- **It landed** once SP-2 merged. `_make_device` now refuses a host body that names no window ("refusing to drive the real desktop without a target window"), so the catalog can name the body without opening the unguarded path.
- **Verified**: `python test_profiles.py` -> ALL PASS, including "every catalog path resolves on disk".

## Debts

- Profile content is general UE5 knowledge. It carries no version-specific claims, so if the project moves to a version whose layout differs, it is a re-read rather than a correction.
- SP-2's `WindowsDevice.screenshot()` still captures the whole desktop until R10 lands. The base profile's coordinate rule is written for the monitor frame, which is where that change is heading.
