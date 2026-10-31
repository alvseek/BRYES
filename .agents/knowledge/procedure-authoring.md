# Procedures, generated copies, and the test that pins them

What it costs to change a procedure in `docs/procedures/`, written after simplifying
`drive-the-desktop.md` on 2026-10-31 and being stopped by the installer's own checks.

## One canonical text, two generated copies

`docs/procedures/<name>.md` is the only hand-written version. The in-repo
`.opencode/skills/<name>/SKILL.md` is a pointer that reads the procedure by relative path,
so it works inside this clone and nowhere else. From another project the procedure has to
carry its own text, so `setup-scripts/` installs a **generated copy**:

```powershell
python setup-scripts/setup-all-opencode.py     # ~/.config/opencode/skills/<name>/SKILL.md
python setup-scripts/setup-all-claude-code.py  # ~/.claude/commands/<name>.md
```

Editing a procedure therefore changes nothing for other agents until both installers run
again. That is the step that is easy to forget, and the copy it leaves behind looks current
because it is a plain markdown file with a plausible date.

## What the installer does to the copy

`install_skills.py` rewrites two things:

- **Relative links** become absolute paths into this clone, because a link such as
  `adr/2026-07-15-effector-hierarchy.md` only resolves next to the original file.
- **A provenance note** after the frontmatter, naming the source and the clone path.

The `description:` in a copy's frontmatter comes from the pointer skill, not the procedure,
so discovery text is authored once.

## The pinned link

`setup-scripts/test_setup.py` asserts that the generated `drive-desktop` copy contains a
link to **`docs/adr/2026-07-15-effector-hierarchy.md`** — the channel-ordering rule, which
is the reason the procedure tells an agent to prefer an application's own API. Simplifying
the procedure, I dropped that reference while keeping its meaning in prose, and the suite
failed on `drive-desktop: ADR link points into the clone's docs/adr` while every other check
passed. The link now sits in the opening paragraph.

The same suite also rewrites-and-checks every relative link target exists, so a renamed or
deleted ADR fails there rather than in a stranger's clone.

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
python setup-scripts/test_setup.py       # 33 checks: rendering, links, manifests, .bat bytes
git diff --check                          # whitespace errors
```

Then read one installed copy back and confirm it carries the change — the source being
correct says nothing about the copy, and the copy is the one other agents load.
