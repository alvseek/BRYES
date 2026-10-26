# BRYES — Installing Its Procedures Into Other Projects

How `/drive-desktop` and `/make-lesson` reach agents working outside this clone: the installers
under `setup-scripts/`, and why the in-repo pointer skills could not do the job.

---

### [2026-10-26 12.33] (agent: software-architect) — A POINTER THAT ONLY WORKS INSIDE ITS OWN CLONE, AND THE DEAD LINK THE TEST FOUND IN THE SOURCE 🔗📦🪝

- **Summary**: Built Claude Code and OpenCode installers that copy BRYES's two procedures into the global command and skill directories, installed the Claude Code one for real, and fixed a dead ADR link the installer's own test exposed.
- **Context**: The session opened as an awakening and turned into a build. Alvi asked whether I remembered the `.bat` installers in the other agent-memory repo, then asked for the same setup here so the Unreal agent in LSGI could use the two procedures. The pointer skills in `.opencode/skills/` read `docs/procedures/*.md` by a relative path, which resolves to nothing from another project.
- **Discussion**:
  - **Recall versus the repo**:
    - **Alvi's Input**: "do you still remember setup / install using .bat in other agent-memory repo?", then "its .bat should be calling .py or .sh, correct?"
    - **My Response**: Said what my memory held (the WSL `bash` decoy, the Store `python.exe` stub, CRLF, the double-click pause) and that it dated from August. Listed his GitHub account, found the repo had been split into several (`agent-memory-wizards` is not a rename of the old coding-skill repo), and read both `.bat` files before answering. They call a `.py`, and no `.sh` is left in `setup-scripts/`.
  - **What the installed skill contains** (decided with WAIT options):
    - **Alvi's Input**: "1. B, 2. B" (copy the full procedure into the installed file; target Claude Code and OpenCode), then "yes, in setup-scripts/ in BRYES".
    - **My Response**: I had recommended pointer-plus-absolute-path to keep one copy. He chose the full copy. Built it so the copy is generated, names its source, and says where the clone is so the scripts can be run from there.
- **Key Interactions**: He answered a two-decision gate in four characters, then confirmed the location mid-turn. "go" authorised the real install; "nice. let's /hermod:project-wrap-up (MCP)" closed it.
- **Issues Encountered**:
  - **Problem Description**: The installer's new link check failed: the rewritten ADR link in the installed `drive-desktop` pointed at `docs/procedures/adr/...`, which does not exist.
  - **Root Cause**: The source link was already dead. `drive-the-desktop.md` links `adr/...` but sits in `docs/procedures/` while the ADRs are in `docs/adr/`. The installer resolved it faithfully.
  - **Solution Process**: Checked both directories before blaming the test or the installer.
  - **Resolution**: Fixed the source to `../adr/...` and added a check that every rewritten link target exists on disk.
  - **Problem Description**: The `.bat` printed `find: '/i': No such file or directory` when run from Git Bash.
  - **Root Cause**: Git's `find` shadows the Windows one on that PATH; it only affects the double-click detection line.
  - **Resolution**: Left as is. Under `cmd` or a double-click the Windows `find` runs.
- **Outcomes**:
  - **Deliverables**: `setup-scripts/install_skills.py` (shared), `setup-all-claude-code.py/.bat`, `setup-all-opencode.py/.bat`, `test_setup.py`; `*.bat text eol=crlf` in `.gitattributes`; the installer recorded in `AGENTS.md` and the orientation map; the ADR link fix. Pushed as `2869fd2`. Installed `drive-desktop.md` and `make-lesson.md` into `~/.claude/commands`.
  - **Progress Made**: `python setup-scripts/test_setup.py` passes, the OpenCode `.bat` was run end to end against a temp directory, and the Claude Code `.bat` was run for real with the files read back.
  - **Tech Debts**:
    - **[new] Neither command has been seen loading in a fresh session**, and `python capture.py` has not been run from the BRYES root by an agent following the installed copy.
    - **[new] ruff is still not installed**, so the new Python files have had no lint pass.
    - **[new] The OpenCode installer has only run against a temp directory.**
    - **[new] The installed copy goes stale** when `docs/procedures/` is edited until the installer is re-run, and nothing warns when that happens.
    - **[new] The installed `make-lesson` still contains the sentence "The `/make-lesson` skill points here rather than repeating it"**, which is false in the copy.
    - **[new] OpenCode skills share a name** with the in-repo pointer skills; the content is equivalent.
    - **[carry] `lessons/lsgi-03-simple-blueprint/` and `lsgi-04-class-vs-instance/` are untracked** and recorded in no session file; they are Alvi's.
    - **[carry] Unchanged from the three earlier threads**: `key_hold` unproven in a live game, the model-swap set, adb and ruff missing, no QA instrument (vision thread); environment isolation unbuilt, the real Unreal run never done (host-body thread); `capture.py` untested, no lessons index, PNG policy undecided (lesson thread).
  - **Next Steps**:
    - Open a fresh Claude Code session in the LSGI project and run `/make-lesson`.
    - Run `setup-scripts\setup-all-opencode.bat` if OpenCode is used on this machine.
    - Decide whether lessons 03 and 04 are finished, then give the lessons an index.
- **Insights**:
  - **New Understanding**: A pointer is valid only inside the tree it points into. Making a procedure reachable from another project means a self-contained copy plus absolute paths, and the copy has to be generated so it cannot drift silently.
  - **Pattern Recognition**: `0eb34b96` in its recall form. The `.bat` lessons I held were from August and the repo had moved from bash to Python since; reading the files answered his question where recalling them would have been a neighbour of it. The link check is the same discipline pointed at my own output, and it found a defect in the input.
  - **Improvement Areas**: I never ran the lint the repo's `ruff.toml` asks for, and said so only in the report. The test for the unproven end (a real agent running the installed command) is still missing.
- **Promotions**:
  → Promoted to [docs/orientation-map.md](../../docs/orientation-map.md) — a `setup-scripts/` entry, and the install note on the drive-the-desktop entry.
  → Promoted to [AGENTS.md](../../AGENTS.md) — how to install both procedures for another project.

---
