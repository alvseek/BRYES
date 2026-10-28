"""BRYES - drag offsets, coordinate verbs and the post-drag diff, model-free (SP-2 Phase 2).

    python agent/test_drag_and_pointer.py

No screen, no model, no device: these are the three rules the loop now enforces, checked as pure
functions plus the vocabulary the Brain is offered.
"""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import loop  # noqa: E402
from brain.client import _actions_for  # noqa: E402


def test_drag_endpoint_offsets_from_the_start():
    start = {"x": 100, "y": 200}
    assert loop.drag_endpoint({"target": "a node"}, start) is None, "no offset means locate a target"
    assert loop.drag_endpoint({"destination_offset": {"dx": 0, "dy": 0}}, start) == (100, 200)
    assert loop.drag_endpoint({"destination_offset": {"dx": 40, "dy": -15}}, start) == (140, 185)
    assert loop.drag_endpoint({"destination_offset": {"dx": -300, "dy": 12}}, start) == (-200, 212)
    for bad in ({"dx": 1}, {"dx": "a", "dy": 2}, {"dx": 1, "dy": None}):
        try:
            loop.drag_endpoint({"destination_offset": bad}, start)
        except ValueError as e:
            assert "destination_offset" in str(e), str(e)
        else:
            raise AssertionError(f"a malformed offset was accepted: {bad!r}")
    print("PASS: a drag offset is start + delta, and a malformed offset is refused")


def test_a_drag_asks_for_its_own_diff():
    assert loop.wants_diff({}, False) is False
    assert loop.wants_diff({"request_diff": True}, False) is True
    assert loop.wants_diff({}, True) is True, "a completed drag must produce a diff next step"
    assert loop.wants_diff({"request_diff": False}, True) is True
    print("PASS: a drag forces the diff, and the Brain's own request still works")


def test_coordinate_verbs_are_derived_from_the_pointer():
    desk = SimpleNamespace(verbs=frozenset({"click", "hover", "type", "key"}), has_shell=False)
    phone = SimpleNamespace(verbs=frozenset({"click", "type", "key"}), has_shell=False)
    blind = SimpleNamespace(verbs=frozenset({"type", "key"}), has_shell=False)

    desk_acts = _actions_for(desk)
    assert "move_to" in desk_acts and "click_at" in desk_acts, desk_acts
    phone_acts = _actions_for(phone)
    assert "click_at" in phone_acts and "move_to" not in phone_acts, phone_acts
    assert "move_to" not in _actions_for(blind) and "click_at" not in _actions_for(blind)
    assert _actions_for(None).count("click_at") == 1, "the full vocabulary lists it once"
    print("PASS: move_to rides on hover and click_at on click, so both follow the body")


def test_coordinate_branches_translate_to_the_body():
    seen = []

    class FakeDevice:
        caps = SimpleNamespace(name="fake", width=10, height=10,
                               verbs=frozenset({"click", "hover"}), has_shell=False)

        def act(self, action):
            seen.append(action)

    assert loop._COORD_VERB == {"move_to": "hover", "click_at": "click"}, loop._COORD_VERB
    d = FakeDevice()
    d.act({"type": loop._COORD_VERB["move_to"], "x": 5, "y": 6})
    d.act({"type": loop._COORD_VERB["click_at"], "x": 7, "y": 8})
    assert seen == [{"type": "hover", "x": 5, "y": 6}, {"type": "click", "x": 7, "y": 8}], seen
    print("PASS: the coordinate verbs land on the body's own pointer verbs")


if __name__ == "__main__":
    test_drag_endpoint_offsets_from_the_start()
    test_a_drag_asks_for_its_own_diff()
    test_coordinate_verbs_are_derived_from_the_pointer()
    test_coordinate_branches_translate_to_the_body()
    print("PASS: all drag and pointer rules green")
