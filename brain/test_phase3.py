"""BRYES Phase 3 proof.

Give the Brain a goal + a text description of the screen and check it outputs a
sensible single next action in structured terms. Two scenarios prove it both
*advances* toward a goal and *recognizes completion*.

Run:  python brain/test_phase3.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import decide  # noqa: E402

GOAL = "Use the calculator to compute 7 + 8 and leave the result on the display."

SCENARIOS = [
    {
        "name": "mid-task (display shows 7)",
        "observation": (
            "A calculator window titled 'Calculator'. The display shows '7'. "
            "Buttons are visible for digits 0-9, operators + - * /, equals =, "
            "and clear (AC). A terminal window is also open beside it."
        ),
        "history": ["click the 7 button (display now shows 7)"],
        "expect": "should click the + button next",
    },
    {
        "name": "goal reached (display shows 15)",
        "observation": (
            "The calculator display shows '15'. The full sequence 7 + 8 = has been "
            "entered."
        ),
        "history": [
            "click the 7 button", "click the + button",
            "click the 8 button", "click the = button (display now shows 15)",
        ],
        "expect": "should report done",
    },
]


def main():
    print(f"GOAL: {GOAL}\n")
    for sc in SCENARIOS:
        print(f"--- scenario: {sc['name']} ---")
        print(f"    expectation: {sc['expect']}")
        # Positional (goal, observation, history) uses decide()'s back-compat path (ADR-007):
        # `observation` fills the CURRENT CONDITION 'Current screen'. Live-model eyeball test.
        action = decide(GOAL, sc["observation"], sc["history"])
        usage = action.pop("_usage", None)
        print(f"    Brain decided: {action}")
        if usage:
            print(f"    usage: {usage.get('total_tokens')} tok, "
                  f"cost ${usage.get('cost')}")
        print()
    print("Eyeball the decisions above: action 1 should target the '+' button, "
          "action 2 should be 'done'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
