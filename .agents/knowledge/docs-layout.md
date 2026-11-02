# docs/ layout, and how to move a document without breaking it

Where each kind of document belongs, and the two traps that leave a docs move looking finished
while its links point at nothing. Measured 2026-11-02, reorganizing `docs/` into category
folders.

## Layout

`docs/README.md` is the human-facing table. The short form:

- `architecture/` — structure: the overview and the modularity / dispatch maps.
- `flows/` — behaviour: the per-step loop sequence.
- `standards/` — conventions and the quality standard.
- `tech-debts/` — the backlog.
- `interfaces/` and `modules/` — empty slots, kept by `.gitkeep` because git stores no empty
  directory.
- `procedures/` and `adr/` — as they were.
- Root — `context-index.md` and `orientation-map.md` only, because the loaders name those paths.

## Moving one safely

1. `git mv` the file so history follows it.
2. Rewrite every relative markdown link: resolve the target against the file's **old**
   directory, map it through the move list, then write it relative to the file's **new**
   directory.
3. Rewrite repo-relative strings too (`docs/<name>` in prose and code spans), including the
   `%% Render: mmdc -i ... -o ...` line in a `.mmd`, which names both an input and an output.
4. Verify that every relative link resolves before committing.

## The two traps

- **Only following links whose target moved is not enough.** A moved file's links to files that
  did *not* move (`adr/...`, `agent/loop.py`, `../roadmap.md`) still assume the old directory.
  The first pass here fixed only moved targets and left 17 such links broken.
- **Resolving a moved file's link by filesystem after the move cannot work.** The old path is
  gone, so a link between two moved files resolves to nothing (`architecture-overview.md` became
  `../architecture-overview.md` instead of `../architecture/architecture-overview.md`). Apply
  the move map before computing the relative path, or rebuild the file from `HEAD`.

A verifier that reads only `.md` and `.mmd`, and strips `#anchor` before checking the path,
avoids the false positives a raw `](...)` scan produces from Python code and fragment-only
links.

## What this session found already broken

115 relative links in `plans/` (written as if the plan sat at the repo root, then moved into
`plans/completed/`) and two `tools/platform-tools/` links in `README.md`. Both predate the
reorganization and were left as they were.
