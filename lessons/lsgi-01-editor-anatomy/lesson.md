---
title: Unreal Editor anatomy: the six regions you will use every day
project: LSGI
lesson: lsgi-01-editor-anatomy
created: 2026-10-20
target: Alvi
---

This is your own LSGI editor, captured from your screen today, not a stock screenshot. Read it once now and the battle loop stops being a hunt through menus.

The scope is deliberately narrow. This lesson is about **where things are**, not about how the combat system is designed. Every claim below is either visible in the picture or a property of the editor's layout. Anything about the battle loop itself waits for the next lesson, where the `unreal` agent and LSGI's own docs are the authority, not a screenshot.

## Step 1: Find the six regions of the editor
shot: shots/step-001-before.png
callout: 0.0,0.006,1.0,0.030 | Menu bar: File, Edit, Window, Tools, Build, Platforms, Select, Actor, Help, plus the project name LSGI at the far right
callout: 0.004,0.043,0.475,0.090 | Main toolbar: Save, Selection Mode, and the Play / Simulate / Stop controls
callout: 0.003,0.110,0.795,0.620 | Viewport: the level itself, here rendering in Perspective and Lit
callout: 0.807,0.113,0.990,0.365 | Outliner: the actors that exist in the open level
callout: 0.807,0.370,0.990,0.620 | Details: the properties of whatever you have selected
callout: 0.015,0.630,0.985,0.958 | Content Drawer: the asset browser, docked over the viewport
callout: 0.008,0.964,0.990,0.997 | Bottom strip: Output Log, Cmd console, and the version-control status
instruction:
  Seven boxes, six jobs. The editor is a fixed arrangement: menu bar and toolbar across the top, the viewport in the middle, the Outliner and Details stacked on the right, the Content Drawer docking over the bottom, and one status strip underneath.
  The names matter because every Unreal tutorial you will read uses them without explaining them. When someone writes "open the Details panel", this is the panel they mean.
why:
  Almost every "I cannot find it" in Unreal is one of these regions being closed, hidden behind another, or scrolled out of view. Knowing which region owns which job sends you to the right one instead of clicking through menus.
expected:
  You can point at the viewport, the Outliner, the Details panel and the Content Drawer without hunting for them.

## Step 2: Read the Content Drawer as a drawer, not a window
shot: shots/step-001-before.png
callout: 0.015,0.630,0.985,0.958 | The drawer body: folder tree on the left, asset grid on the right
callout: 0.008,0.964,0.088,0.997 | The Content Drawer toggle, bottom left, next to the Output Log
instruction:
  It is open in this capture. Notice what it covers: the lower half of the viewport. That is the deal a drawer makes. It gives the space back the moment you toggle it closed, which is why it is not a floating window you drag around.
  Its two halves are also doing different jobs: the tree on the left is the folder hierarchy, the grid on the right is the assets inside the folder you have selected.
why:
  The single most common way to lose the asset browser is to look for a window called "Content Browser" in the title bar. There is a Content Browser, but the docked form is the drawer, and it is toggled from the bottom strip.
expected:
  You can open and close the Content Drawer without moving any panel.

## Step 3: Learn to read the path, not just the asset
shot: shots/step-001-before.png
callout: 0.383,0.639,0.512,0.663 | The breadcrumb: All > Content > Tests, the folder you are currently looking at
callout: 0.019,0.890,0.140,0.920 | The same folder in the tree, highlighted
instruction:
  The breadcrumb across the top of the grid is the honest answer to "where does this live". Here it reads `All > Content > Tests`, so every asset in the grid is inside the project's `Content/Tests` folder.
  The tree agrees: `Tests` is selected, under `All > Content`. And the assets are what you would expect to find there: test levels (`L_TestArena_WP_*`, `L_Empty_WP_*`), a data layer, and `BP_LSGIArena`.
why:
  An asset can be reached from the Content Drawer, a Reference, the Place Actors panel, or a Blueprint node that mentions it. Only one of those is the file's real home. Reading the breadcrumb means you can tell someone else, or yourself tomorrow, exactly where it lives: `/Game/Tests`.
expected:
  You can state the content path of the arena test assets without opening a properties window.

## Step 4: Recover the layout when you get lost
shot: none
instruction:
  Two habits, no screenshot needed, because both live in regions you have already seen:
  - **A panel disappeared.** The `Window` menu in the menu bar lists every panel the editor can show. Open it there rather than restarting the editor.
  - **The asset browser disappeared.** The `Content Drawer` button in the bottom strip brings it back.
  - **The console is one click away.** `Cmd` in the bottom strip opens the console input, which is where commands like `stat fps` and console variables go. Most Unreal fixes you will read online are a console command.
  - **Are there unsaved changes?** The bottom-right reads `All Saved` when the editor is holding nothing unsaved. When it changes, the editor is remembering work it has not written to disk.
why:
  Losing the layout feels like losing the editor. It never is: every panel is one menu away, and the console you will use constantly is already docked at the bottom of your screen.
expected:
  You can recover a closed panel and open the console without restarting Unreal.
