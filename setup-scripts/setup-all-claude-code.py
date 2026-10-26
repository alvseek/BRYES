"""Install BRYES's procedures (/drive-desktop, /make-lesson) as Claude Code slash commands.

Writes ``~/.claude/commands/drive-desktop.md`` and ``make-lesson.md``, each carrying the full
procedure so they work from any project, not just from inside the BRYES clone.

Cross-platform: run directly, or via ``setup-all-claude-code.bat`` on Windows.

Usage:        python setup-scripts/setup-all-claude-code.py
Env override: BRYES_TARGET_DIR (default: ~/.claude/commands)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_skills  # noqa: E402

MANIFEST_NAME = ".bryes-manifest"


def main() -> int:
    target = Path(os.environ.get("BRYES_TARGET_DIR") or Path.home() / ".claude" / "commands")
    return install_skills.run("Claude Code", target, "command", MANIFEST_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
