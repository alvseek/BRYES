# Unreal Editor (Unreal Engine 5, Windows)

The Unreal Editor running on the Windows desktop. Inherits `profiles/windows/profile.md`.

## Terms & Vocab
- Editor window — its title is `<Project> - Unreal Editor`; the project name is the reliable
  part of it.
- Document tab — the tabbed area inside the editor window (Viewport, EventGraph, an asset
  editor). Each tab carries the asset's name and its own close button.
- Toolbar — the strip inside the top of the window: Save, Compile, Diff, Find in Blueprints,
  Class Settings, Class Defaults, then the Play / Simulate / Stop controls.
- Graph canvas — the dark gridded area where nodes are laid out and wires run between them.
- Node — a rounded box with a coloured title bar holding its name; body text sits under the
  title.
- Pin — the small triangle (execution) or circle (data) on a node's side edge. A wire ends at
  a pin.
- Wire — a line between two pins: white for execution order, coloured for data.
- My Blueprint / Components — the left column: graphs, functions, macros, variables and event
  dispatchers, or the component tree.
- Details panel — the right column: the properties of the current selection, including
  dropdowns.
- Content Browser / Content Drawer — the asset grid along the bottom. Each tile is a thumbnail
  with the asset's name beneath it.
- Breadcrumb — the `All > Content > ...` path above the asset grid.

## Visual
- You are looking at the Unreal Editor: toolbar across the top, canvas in the middle, one
  panel column on the left, Details on the right, Content Browser along the bottom.
- A node's title bar is the wide coloured strip at its top and its name is the text there.
  Pins are the tiny shapes at the left and right edges, an order of magnitude smaller than the
  title bar.
- Content Browser tiles show a thumbnail with the name underneath; the selected tile has a
  bright border.
- A context menu opened in the canvas floats over it and hides part of the graph. It is a wide
  panel with a search field at its top and grouped results under it.
- A dropdown in Details opens a narrow list under the field, with its own search box and one
  row per choice.

## Operating
- Open an asset by name: `Ctrl+P`, type the asset name, press Enter. More exact than hunting
  the Content Browser.
- Create a node: right-click the canvas where it belongs, type the node's name, press Enter.
  Measured: the menu's search box already has focus, typing filters the list, and Enter creates
  the highlighted result. Prefer this over dragging one in from a palette.
- Wire two pins: press on the output pin and release on the input pin. A menu opening instead
  means the press began on canvas rather than on the pin.
- A pin is about ten to fourteen pixels. Measured: a press seventeen pixels to its right landed
  on the node body and MOVED the node instead of wiring it, with no error anywhere. Aim at the
  pin measured on a zoomed crop, then confirm the wire appeared rather than trusting the drag.
- Choose a Details value: click the centre of the field, not its label, then click the row in
  the list that opens. Measured: clicking the empty space left of a combo does nothing at all.
- Compile with the toolbar's Compile button. Its tooltip reads `Good to go` after a clean
  compile, and `Dirty, needs to be recompiled` once the graph changes again.
- Save with `Ctrl+S`. The status bar at the bottom right reports how many assets are unsaved.
- `Ctrl+Z` undoes the last graph change and names it in a toast, e.g. `Undo: Move Node`, which
  is the fastest way to tell what an accidental drag actually did.
- Project Settings opens as its OWN window with its own tab and close button, not a panel. Its
  left tree is grouped (PROJECT, GAME, ENGINE) and a project's own classes appear under GAME by
  name. Its header names the ini file the shown values are saved in.
- Unreal opens Project Settings and some dialogs in a **new window on the primary monitor**,
  even when the editor itself is on another screen. Move the editor to the primary monitor
  before a run, or the new window appears on a screen the run is not capturing.
