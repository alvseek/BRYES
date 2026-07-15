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
