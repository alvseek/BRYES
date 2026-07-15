"""BRYES Phase 4 proof — run the ONE task end to end, unattended.

Task: compute 7 + 8 on the calculator and leave the result on the display.
Watch the loop drive itself; the final screenshot should show 15.

Prereq: the Screen container is up and the calculator is at a clean state.
Run:  python agent/test_phase4.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from loop import run  # noqa: E402
from devices import ContainerDevice  # noqa: E402
from paths import artifact  # noqa: E402

GOAL = ("Use the on-screen calculator to compute 7 + 8. Click the buttons in order "
        "(7, then +, then 8, then =) and leave the result on the calculator display.")


def main():
    result = run(GOAL, max_steps=12)
    print("\nresult:", {k: v for k, v in result.items() if k != "history"})
    print("history:")
    for h in result["history"]:
        print("  -", h)

    with open(artifact("agent_final.png"), "wb") as f:
        f.write(ContainerDevice().screenshot())
    print("\nsaved agent_final.png — the display should read 15.")
    return 0 if result["status"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
