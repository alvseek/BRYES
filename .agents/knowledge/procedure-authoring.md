# Procedures and the pointers that reach them

One hand-written procedure, three files that point at it, and the checks that keep the
pointers honest. Written after the installed copies were changed from generated duplicates
to absolute-path redirects on 2026-11-02.

## One canonical text, three pointers

`docs/procedures/<name>.md` is the only hand-written version. Everything else points at it:

- **`.opencode/skills/<name>/SKILL.md`** (in this repo) reads it by relative path, so it works
  inside this clone and nowhere else.
- **`~/.claude/commands/<name>.md`** (installed) names it by absolute path, so it resolves from
  any project.
- **`~/.config/opencode/skills/<name>/SKILL.md`** (installed) names it the same way.

The installed forms used to carry the whole procedure, with relative links rewritten to absolute
ones. That made two copies of every procedure, so an edit left a stale duplicate that looked
current and nothing compared it to the source. A pointer cannot go stale: it is either resolving or
broken, and a broken one says so.

```powershell
python setup-scripts/setup-all-opencode.py     # ~/.config/opencode/skills/<name>/SKILL.md
python setup-scripts/setup-all-claude-code.py  # ~/.claude/commands/<name>.md
```

An edit to `docs/procedures/` needs no reinstall. Re-run the installer only when a procedure is
added, renamed or dropped (the manifest removes the old entry), or when the clone moves to a
different path.

## What the installer writes

`install_skills.py` renders the frontmatter plus one paragraph, and nothing else:

- the canonical file as an absolute markdown link, with "read it and follow it exactly";
- the clone root, because the procedure's commands (`python capture.py`, `python lesson.py`,
  `pip install -r requirements.txt`) are relative to that folder;
- a line saying that a missing file should be reported rather than worked around from memory.

The `description:` in a pointer's frontmatter comes from the in-repo pointer skill, not from the
procedure, so discovery text is authored once and cannot differ between the two installed forms.

## The pinned ADR link

`setup-scripts/test_setup.py` asserts that `docs/procedures/drive-the-desktop.md` contains a link
to **`../adr/2026-07-15-effector-hierarchy.md`** — the channel-ordering rule, which is the reason
the procedure tells an agent to prefer an application's own API. Simplifying the procedure on
2026-10-31, I dropped that reference while keeping its meaning in prose, and the suite failed while
every other check passed. The link sits in the opening paragraph, and the assertion now holds on
the canonical file, which is where the link has to live once the copies are pointers.

## Simplifying a procedure without losing its content

`drive-the-desktop.md` had grown a second copy of the API surface. The split that survived:

- **The procedure carries the sequence** — connect, select, observe, act, verify — plus the
  rules that decide whether the sequence is safe.
- **The reference carries the surface** — endpoint tables, every field, every error code.
  `api/README-Bridge.md` and `api/README-Bridge-Client.md` already hold it.

Linking out costs one click. Duplicating costs correctness every time the surface moves,
which is exactly what had happened: the procedure still taught single-action requests with
per-verb flags after the client had moved to `act --json`.

## Checks worth running after any procedure edit

```powershell
python setup-scripts/test_setup.py       # pointer targets, frontmatter, manifests, .bat bytes
git diff --check                          # whitespace errors
```

There is nothing to reinstall and nothing to read back, because the installed file carries no
procedure text. Read one installed pointer if you changed `render()` or the clone path, and confirm
its absolute link resolves to the file you expect.
