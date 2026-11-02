# BRYES — Repository Layout & Installed Procedures

How `docs/` is organized, and why an installed procedure is a pointer instead of a copy.

---

### 2026-11-02 09.16 - DOCS SORTED INTO CATEGORY FOLDERS, AND INSTALLED COPIES BECAME POINTERS (agent: software-architect)

- **Summary**: Sorted `docs/` into the folders Alvi created, rewrote every live reference, and changed the global procedure installers from full copies to absolute-path pointers. Both installers were re-run; the project work is pushed as `c832972`.
- **Context**: Alvi opened by checking whether the OpenCode procedure copy was "just a redirection, which is a good thing. but not with the claude code". Measurement showed the in-repo skill was a pointer but both *installed* forms were full copies, byte-identical apart from the `name:` line. He approved changing both to pointers. He then asked to sort the files scattered at the `docs/` root into the new folders, and offered `docs/architecture/` when the diagram placement was ambiguous.
- **Discussion**:
  - **The premise check**: my first answer confirmed only half of it. The redirection existed in `.opencode/skills/`, which Claude Code has no equivalent of; the installed OpenCode skill was as much a copy as the Claude Code command. That correction is what made the fix apply to both.
  - **Pointer over copy**: the installer now writes frontmatter plus one paragraph: the canonical file as an absolute link, the clone root its commands are relative to, and a line saying a missing file should be reported rather than improvised. Editing `docs/procedures/` needs no reinstall.
  - **Docs taxonomy**: `standards/` took the conventions and quality standard, `tech-debts/` took the backlog, `flows/` took the loop sequence, `architecture/` (his suggestion) took the overview and all three maps. `interfaces/` and `modules/` stay empty slots.
  - **What stays at the root**: `context-index.md` and `orientation-map.md`, because the context and map loaders name those exact paths.
- **Key Interactions**: "opencode procedures copy is just a redirection, which is a good thing. but not with the claude code. can you confirm this?" · "so the claude also has been installed?" · "does it help if I created docs/architecture?" · "Leave it empty for now" for `interfaces/`.
- **Issues Encountered**:
  - **Problem Description**: The first link-rewrite pass left 17 links pointing from the old directory.
  - **Root Cause**: It rewrote only links whose *target* moved. A moved file's links to unmoved files (ADRs, `agent/loop.py`, `../roadmap.md`) still assumed `docs/`.
  - **Solution Process**: A link checker listed every broken relative link; a second pass rebuilt the moved files from `HEAD` and recomputed all their links against the new directory.
  - **Resolution**: That pass had its own bug: resolving a moved file's link by filesystem after the move could not find the old path, so links between two moved files pointed at nothing (`../architecture-overview.md` instead of `../architecture/...`). A third pass applied the move map before computing the relative path. Zero broken links remain under `docs/`.
  - **Problem Description**: The first verifier reported 126 "broken" links, many false.
  - **Root Cause**: Its regex let `[^)\s]+` swallow the `#anchor`, and it scanned `.py` files, so code such as `(**kw)` looked like a markdown link.
  - **Resolution**: Anchor split out of the path, scan limited to `.md` and `.mmd`. The remaining 115 are real and predate this work.
- **Outcomes**:
  - **Deliverables**: `install_skills.py` renders pointers with a source-exists guard; `test_setup.py` pins the pointer shape (37 checks); both installers re-run (Claude 926/868 B, OpenCode 946/886 B); eight docs moved with `git mv`; new `docs/README.md` and `.agents/knowledge/docs-layout.md`; references rewritten in `README.md`, `AGENTS.md`, `docs/context-index.md`, `docs/orientation-map.md`, three ADRs, `agent/README.md`, `api/README.md`, two knowledge files, the `framediff.py` docstring and twelve plan files; `.gitkeep` in `interfaces/` and `modules/`.
  - **Progress Made**: 37 installer checks pass; `git diff --check` clean; no stale `docs/<old>` string outside `.agents/session`; every relative link under `docs/` resolves. Project work pushed as `c832972` before the memory write.
  - **Tech Debts**:
    - Both installed pointers break if `C:\Work\im\BRYES` moves, until the installer re-runs. The old copies survived a move.
    - No fresh session has loaded the new pointer yet, so its behaviour as a skill and as a command is unproven live.
    - 115 broken relative links in `plans/` and two `tools/platform-tools/` links in `README.md` predate this work and were left alone.
    - The three `.mmd` render commands were updated but not executed, so no SVG proves the new output paths.
    - `interfaces/` and `modules/` are `.gitkeep` placeholders with no content.
    - The docs link checker lives only in a temp script; nothing in the repo tests docs links.
  - **Next Steps**:
    - Load `/drive-desktop` in a fresh session from another project to prove the pointer resolves.
    - Decide whether to fix or retire the stale `plans/` links and the README `tools/` links.
    - Add a docs link check to the repo if docs moves keep happening.
    - Fill `interfaces/` and `modules/` when there is real content.
- **Insights**:
  - **New Understanding**: An installed copy is a second implementation, so it drifts; a pointer removes the class of failure instead of testing for it. That is the same split the procedure itself already made when it stopped restating the API surface.
  - **Pattern Recognition**: Alvi named the design before I did, and the measurement turned his half-true premise into a change that fixed both platforms.
  - **Improvement Areas**: Recompute every link from the destination directory in the first pass. Two verification rounds were spent recovering from a rule I could have stated up front.
- **Promotions**:
  → New shared `docs/README.md` — the docs folder taxonomy.
  → New project knowledge `.agents/knowledge/docs-layout.md` — where documents go and the two traps that break links when one moves.
  → Updated `.agents/knowledge/procedure-authoring.md` — the installer writes a pointer, not a copy.
  → Reasoning: skipped. The existing pointer-vs-copy principle covers the lesson; a new pattern would restate it.
  → Emotional: skipped. Criterion 5 was not met; "nice" is his usual understated close, not a deep-emotion moment.
