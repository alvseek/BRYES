"""BRYES devices — swappable vision-controllable bodies (ADR-002).

The loop depends on the `Device` Protocol; concrete bodies keep their transport private.
Exports grow as devices land: `ContainerDevice` (Phase 1), `PhoneDevice` (Phase 3).
"""
from .base import ALL_VERBS, Capabilities, Device
from .container import DESKTOP_CAPS, ContainerDevice
from .phone import PHONE_CAPS, PhoneDevice

__all__ = ["Device", "Capabilities", "ALL_VERBS",
           "ContainerDevice", "DESKTOP_CAPS", "PhoneDevice", "PHONE_CAPS"]
