"""BRYES devices — swappable vision-controllable bodies (ADR-002).

The loop depends on the `Device` Protocol; concrete bodies keep their transport private.
Exports grow as devices land: `ContainerDevice` (Phase 1), `PhoneDevice` (Phase 3),
`WindowsDevice` (capture-only: the real desktop Unreal lives on).
"""
from .base import ALL_VERBS, Capabilities, Device, clamp_hold
from .container import DESKTOP_CAPS, ContainerDevice
from .phone import PHONE_CAPS, PhoneDevice
from .windows import WINDOWS_CAPS, WindowsDevice

__all__ = ["Device", "Capabilities", "ALL_VERBS", "clamp_hold",
           "ContainerDevice", "DESKTOP_CAPS", "PhoneDevice", "PHONE_CAPS",
           "WindowsDevice", "WINDOWS_CAPS"]
