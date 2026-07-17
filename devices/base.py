"""BRYES — the Device abstraction (ADR-002).

A `Device` is a *vision-controllable body* the agent inhabits: something that can be
screenshotted, acted on (pointer + keyboard), and optionally handed a shell command.
The loop (`agent/loop.py`) depends on this Protocol, never on a transport — so the same
perceive->decide->act loop drives a Docker desktop (`ContainerDevice`), an Android phone
(`PhoneDevice`), or a future Windows desktop, each keeping its own transport private.

`Capabilities` makes each body's differences first-class: a phone has no right_click,
adds Back/Home, uses portrait coordinates and an Android shell. The Brain reads the
ACTIVE device's Capabilities to assemble its action vocabulary, so it is only ever
offered verbs the current body can actually perform.
"""
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Every pointer/keyboard verb a body MAY support. A device advertises the subset it can
# do via Capabilities.verbs. The loop-level actions (wait, screenshot, done, fail) are
# always available and are NOT device verbs; `shell` is gated by Capabilities.has_shell.
# See brain/client.py for how the full vocabulary is assembled from these.
ALL_VERBS = frozenset({
    "click", "double_click", "right_click", "hover", "scroll", "drag", "type", "key",
})


@dataclass(frozen=True)
class Capabilities:
    """What one specific body can do — read by the Brain to shape its action vocabulary
    and by the loop/Eyes for the coordinate space."""
    name: str                                   # e.g. "docker-desktop", "android-phone"
    width: int                                  # screen coordinate space (pixels)
    height: int
    verbs: frozenset[str]                       # subset of ALL_VERBS this body supports
    has_shell: bool = False                     # is shell() available? (Tier-2)
    shell_flavor: str = ""                      # "bash" | "android" | "powershell" | ...
    keys: dict[str, str] = field(default_factory=dict)  # named key -> device keycode,
    #                                             e.g. {"Back": "KEYCODE_BACK"}


@runtime_checkable
class Device(Protocol):
    """A vision-controllable body. The loop depends on THIS, not on any transport.

    Concrete devices (ContainerDevice, PhoneDevice, ...) implement these members; how
    each one reaches its body (HTTP, adb subprocess, in-process) is its own private
    business.
    """

    caps: Capabilities

    def screenshot(self) -> bytes:
        """The current screen as PNG bytes."""
        ...

    def act(self, action: dict) -> None:
        """Perform ONE pointer/keyboard action. `action` carries {"type": <verb>, ...}
        plus whatever that verb needs: click/double_click/right_click/hover -> x, y;
        scroll -> x, y, direction; drag -> x, y, x2, y2; type -> text; key -> key.
        The verb is always one the device advertised in `caps.verbs`."""
        ...

    def clear_field(self) -> None:
        """Clear the currently-focused text field. Device-specific gesture: a desktop does
        select-all + delete (ctrl+a, Delete); a phone uses its own idiom. May raise
        NotImplementedError on a body whose clear gesture isn't built yet."""
        ...

    def type_into(self, text: str, *, click_xy: tuple[int, int] | None = None,
                  clear_first: bool = False, press_enter: bool = False) -> None:
        """Enter text as ONE hand gesture: optionally click `click_xy` to focus, optionally
        clear_field() first, type `text`, optionally press Enter after. `click_xy` is ALREADY
        grounded by the loop (the device has no Eyes — it never sees a description). Most
        bodies delegate to `default_type_into`; a body whose gesture genuinely differs (e.g.
        a send-button submit instead of Enter) implements this itself."""
        ...

    def shell(self, command: str, timeout: int | None = None,
              stdin: str | None = None) -> dict:
        """Run a NON-interactive shell command (Tier-2) and return
        {ok, exit_code, stdout, stderr, timed_out?}. Only meaningful when
        `caps.has_shell` is True."""
        ...

    def pointer(self) -> tuple[int, int] | None:
        """Current pointer (x, y) for model-free test assertions, or None if the body
        has no queryable pointer (a touchscreen doesn't)."""
        ...


_FOCUS_SETTLE = 0.15   # seconds to let a click land focus before typing into the field


def default_type_into(device, text, *, click_xy=None, clear_first=False, press_enter=False):
    """The standard 'type into a field' gesture, composed from a body's own atomic
    primitives (`act` + `clear_field`). ContainerDevice and PhoneDevice both delegate here;
    a body whose gesture genuinely differs overrides `type_into` instead.

    The per-body differences stay where they belong: `act` maps the click/type/key to the
    body's transport (and normalizes the Enter key — X `Return`, Android `KEYCODE_ENTER`),
    and `clear_field` owns the body's clear idiom. `click_xy` is pre-grounded by the loop.
    """
    if click_xy is not None:
        device.act({"type": "click", "x": click_xy[0], "y": click_xy[1]})
        time.sleep(_FOCUS_SETTLE)              # let focus land before typing
    if clear_first:
        device.clear_field()
    device.act({"type": "type", "text": text})
    if press_enter:
        device.act({"type": "key", "key": "Enter"})    # each body's act() maps Enter for it
