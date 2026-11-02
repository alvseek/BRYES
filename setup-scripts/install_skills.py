"""Shared installer: BRYES's two agent procedures as global Claude Code commands or OpenCode skills.

BRYES carries two procedures other agents need from OTHER projects (the Unreal agent in LSGI is
the reason this exists): ``/drive-desktop`` and ``/make-lesson``. Their one canonical text lives in
``docs/procedures/*.md``; ``.opencode/skills/*/SKILL.md`` is a pointer that reads it by relative
path, so it works inside this clone and nowhere else.

The installed form is a pointer too, written with an absolute path so it resolves from any project.
It carries its frontmatter, the location of the canonical file, and the clone folder its commands
are relative to. It carries no procedure text on purpose: a second copy drifts from the original,
and the drifted copy is always the one somebody is reading. Editing ``docs/procedures/`` therefore
needs no reinstall, and nothing is rewritten in transit.

The skill description is read from the existing pointer skill's frontmatter, so it is authored in
one place and the discovery text cannot drift between the two forms.

Used by ``setup-all-claude-code.py`` (flat ``<name>.md`` commands) and ``setup-all-opencode.py``
(``<name>/SKILL.md`` folders).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# installed name -> procedure file under docs/procedures/
PROCEDURES = {
    "drive-desktop": "drive-the-desktop.md",
    "make-lesson": "make-a-lesson.md",
}

_DESCRIPTION = re.compile(r"(?m)^description:\s*(.+?)\s*$")


def _description(name: str, root: Path) -> str:
    """The pointer skill's own description, so discovery text is written once."""
    pointer = root / ".opencode" / "skills" / name / "SKILL.md"
    match = _DESCRIPTION.search(pointer.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"no description: line in {pointer}")
    return match.group(1)


def _yaml_scalar(value: str) -> str:
    """Always double-quoted: a description is prose, and a bare ': ' would silently unload it."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(name: str, kind: str, root: Path = ROOT) -> str:
    """Build one installed pointer: frontmatter, then where the canonical procedure lives."""
    source = root / "docs" / "procedures" / PROCEDURES[name]
    if not source.is_file():
        raise FileNotFoundError(f"no procedure source at {source}")
    description = _yaml_scalar(_description(name, root))
    if kind == "skill":
        frontmatter = f"---\nname: {name}\ndescription: {description}\n---\n"
    else:
        frontmatter = f"---\ndescription: {description}\n---\n"
    note = (
        f"Read [`{source.as_posix()}`]({source.as_posix()}) and follow it exactly. "
        "That file is the canonical procedure and the only copy; this installed file "
        "deliberately carries none of it, because two copies drift and the drifted one is "
        "always the one somebody is reading.\n"
        f"\nBRYES is cloned at `{root.as_posix()}`. Every relative path and command in that "
        "procedure (`python capture.py`, `python lesson.py`, `pip install -r requirements.txt`) "
        "is relative to that folder, so `cd` there before running any of them. If that path is "
        "missing, say so instead of working from memory.\n"
    )
    return f"{frontmatter}\n{note}"


def _manifest_entries(manifest: Path) -> list[str]:
    if not manifest.is_file():
        return []
    lines = (ln.strip() for ln in manifest.read_text(encoding="utf-8").splitlines())
    # A bare name only: a manifest entry must never walk out of the target directory.
    return [ln for ln in lines if ln and Path(ln).name == ln]


def _cleanup(target_dir: Path, manifest: Path) -> int:
    """Remove what the previous run installed, so a renamed or dropped procedure leaves no orphan."""
    removed = 0
    for entry in _manifest_entries(manifest):
        path = target_dir / entry
        if path.is_dir():
            shutil.rmtree(path)
            removed += 1
        elif path.is_file():
            path.unlink()
            removed += 1
    return removed


def install(
    target_dir: Path | str,
    kind: str,
    manifest_name: str,
    root: Path | str = ROOT,
) -> tuple[list[str], int]:
    """Install both procedures into ``target_dir``.

    ``kind`` is ``"command"`` (flat ``<name>.md``) or ``"skill"`` (``<name>/SKILL.md``).
    Returns ``(installed_names, removed_count)``.
    """
    if kind not in ("command", "skill"):
        raise ValueError(f"kind must be 'command' or 'skill', not {kind!r}")
    root = Path(root)
    target_dir = Path(target_dir)

    # Render everything before touching the target: a missing source then fails the run with
    # the previous install intact, instead of after it was removed.
    rendered = {name: render(name, kind, root) for name in PROCEDURES}

    target_dir.mkdir(parents=True, exist_ok=True)
    removed = _cleanup(target_dir, target_dir / manifest_name)

    entries: list[str] = []
    for name, text in rendered.items():
        if kind == "skill":
            (target_dir / name).mkdir(parents=True, exist_ok=True)
            dest = target_dir / name / "SKILL.md"
            entries.append(name)
        else:
            dest = target_dir / f"{name}.md"
            entries.append(dest.name)
        # Encode first and swap in, so an encode error cannot truncate a file that was fine.
        data = text.encode("utf-8")
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)

    (target_dir / manifest_name).write_text(
        "\n".join(entries) + "\n", encoding="utf-8", newline="\n"
    )
    return list(PROCEDURES), removed


def run(platform: str, target_dir: Path, kind: str, manifest_name: str) -> int:
    """Shared ``main()`` body for a platform entry point."""
    print(f"=== Setup BRYES procedures for {platform} ===\n")
    print(f"Source: {ROOT / 'docs' / 'procedures'}")
    print(f"Target: {target_dir}\n")

    try:
        installed, removed = install(target_dir, kind, manifest_name)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    if removed:
        print(f"Replaced {removed} previously installed entries\n")
    print(f"Installed {len(installed)} procedures:")
    for name in installed:
        print(f"  {name}")
    if kind == "command":
        print("\nType /drive-desktop or /make-lesson in Claude Code.")
    else:
        print("\nSkills are model-invoked: ask for the procedure in your own words.")
    print("No re-run is needed after editing docs/procedures/: the installed file points at it.")
    return 0
