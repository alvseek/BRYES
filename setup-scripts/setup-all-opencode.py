"""Install BRYES's procedures (drive-desktop, make-lesson) as OpenCode Agent Skills.

OpenCode reads global skills as folders holding a ``SKILL.md`` in ``~/.config/opencode/skills/``
(``$XDG_CONFIG_HOME/opencode/skills/`` when that is set). Each carries the full procedure so it
works from any project, not just from inside the BRYES clone.

Cross-platform: run directly, or via ``setup-all-opencode.bat`` on Windows.

Usage:        python setup-scripts/setup-all-opencode.py
Env override: BRYES_TARGET_DIR (default: ~/.config/opencode/skills)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install_skills  # noqa: E402

MANIFEST_NAME = ".bryes-opencode-manifest"


def _config_base() -> Path:
    """Base dir for OpenCode global state (respects XDG on Linux/macOS)."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg) / "opencode" if xdg else Path.home() / ".config" / "opencode"


def main() -> int:
    target = Path(os.environ.get("BRYES_TARGET_DIR") or _config_base() / "skills")
    return install_skills.run("OpenCode", target, "skill", MANIFEST_NAME)


if __name__ == "__main__":
    raise SystemExit(main())
