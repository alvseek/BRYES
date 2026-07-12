"""BRYES — single source of truth for where runtime image artifacts go.

Every screenshot / visual proof (phase tests, ad-hoc debugging) is written under
`artifacts/` at the repo root. That directory is gitignored wholesale (only
`.gitkeep` is tracked), so no screenshot can slip through prefix-matching.

Import `artifact()` instead of hardcoding a path or filename anywhere:

    from paths import artifact
    with open(artifact("agent_final.png"), "wb") as f:
        f.write(png_bytes)
"""
from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def artifact(name):
    """Absolute path for an artifact file; ensures artifacts/ exists first."""
    ARTIFACTS.mkdir(exist_ok=True)
    return str(ARTIFACTS / name)
