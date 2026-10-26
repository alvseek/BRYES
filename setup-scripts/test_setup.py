"""BRYES - installer tests (model-free). Every install points at a temp dir, never at ~/.claude.

Covers what a broken installer gets wrong silently: the installed file must carry the whole
procedure, a relative link must be made absolute, the frontmatter must parse, a re-run must not
pile up files, a dropped entry must be cleaned, and the .bat wrappers must be CRLF and ASCII.

Run:  python setup-scripts/test_setup.py
"""

import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import install_skills as inst  # noqa: E402

ROOT = inst.ROOT
failures: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        failures.append(label)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    block = re.match(r"---\n(.*?)\n---\n", text, re.S)
    out: dict[str, str] = {}
    for line in (block.group(1) if block else "").splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)

    # --- command form (Claude Code) ---
    cmds = tmp_path / "commands"
    names, removed = inst.install(cmds, "command", ".bryes-manifest")
    check(set(names) == set(inst.PROCEDURES), "both procedures reported installed")
    check(removed == 0, "first install removes nothing")
    for name, source_name in inst.PROCEDURES.items():
        installed = read(cmds / f"{name}.md")
        source = read(ROOT / "docs" / "procedures" / source_name)
        fm = frontmatter(installed)
        check(set(fm) == {"description"}, f"{name}: command frontmatter is description only")
        check(fm["description"].startswith('"') and fm["description"].endswith('"'),
              f"{name}: description is a quoted scalar")
        check(source.splitlines()[0] in installed, f"{name}: carries the procedure's own title")
        check(source.splitlines()[-1] in installed, f"{name}: carries the procedure to its end")
        check(ROOT.as_posix() in installed, f"{name}: names the BRYES clone")
    check(read(cmds / ".bryes-manifest").split() == ["drive-desktop.md", "make-lesson.md"],
          "manifest lists exactly the installed commands")

    # a relative link must not survive: it only resolves next to the original file
    drive = read(cmds / "drive-desktop.md")
    check(not re.search(r"\]\((?!https?://|#|/|[A-Za-z]:)", drive),
          "drive-desktop: no relative markdown link left")
    check(f"]({ROOT.as_posix()}/docs/adr/2026-07-15-effector-hierarchy.md)" in drive,
          "drive-desktop: ADR link points into the clone's docs/adr")
    for name in inst.PROCEDURES:
        links = re.findall(r"\]\(([A-Za-z]:/[^)#\s]+)", read(cmds / f"{name}.md"))
        dead = [link for link in links if not Path(link).exists()]
        check(not dead, f"{name}: every rewritten link target exists ({len(links)} checked)")

    # --- idempotence and cleanup ---
    again, removed = inst.install(cmds, "command", ".bryes-manifest")
    check(removed == 2, "re-run replaces the two previous entries, no more")
    check(sorted(p.name for p in cmds.iterdir()) ==
          [".bryes-manifest", "drive-desktop.md", "make-lesson.md"],
          "re-run leaves exactly the same files (no .tmp, no duplicates)")
    (cmds / ".bryes-manifest").write_text("gone.md\n../escape.md\n", encoding="utf-8")
    (cmds / "gone.md").write_text("stale", encoding="utf-8")
    (tmp_path / "escape.md").write_text("outside", encoding="utf-8")
    inst.install(cmds, "command", ".bryes-manifest")
    check(not (cmds / "gone.md").exists(), "a manifest-claimed stale file is removed")
    check((tmp_path / "escape.md").exists(), "a manifest entry cannot delete outside the target")

    # --- skill form (OpenCode) ---
    skills = tmp_path / "skills"
    inst.install(skills, "skill", ".bryes-opencode-manifest")
    for name in inst.PROCEDURES:
        fm = frontmatter(read(skills / name / "SKILL.md"))
        check(fm.get("name") == name == (skills / name).name,
              f"{name}: skill name equals its folder name")
        check("description" in fm, f"{name}: skill has a description")
    check(read(skills / ".bryes-opencode-manifest").split() == ["drive-desktop", "make-lesson"],
          "skill manifest lists the folders")

    # --- a missing source must fail before the previous install is touched ---
    before = read(cmds / "make-lesson.md")
    try:
        inst.install(cmds, "command", ".bryes-manifest", root=tmp_path / "no-such-root")
        check(False, "a missing source raises")
    except OSError:
        check(read(cmds / "make-lesson.md") == before, "a missing source leaves the install intact")

# --- the .bat wrappers ---
for bat in sorted(HERE.glob("*.bat")):
    raw = bat.read_bytes()
    check(raw.count(b"\r\n") == raw.count(b"\n") and raw.count(b"\r") == raw.count(b"\r\n"),
          f"{bat.name}: every line ends CRLF")
    check(all(b < 128 for b in raw), f"{bat.name}: ASCII only")
    target = bat.with_suffix(".py")
    check(target.is_file() and target.name in raw.decode("ascii"),
          f"{bat.name}: names a .py that exists")

print()
if failures:
    print(f"FAIL: {len(failures)} check(s) failed")
    sys.exit(1)
print("PASS: all installer checks")
