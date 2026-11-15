"""Helpers shared by all entity platforms."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, format_mac

_MAC_RE = re.compile(r"^[0-9a-f]{12}$")


def mac_connections(serial: Any) -> set[tuple[str, str]]:
    """Return a network-MAC connection when the serial number is a MAC address.

    Judo connectivity modules report their MAC address as serial number
    (e.g. ``aabbccddeeff``). Registering it as a device connection lets
    integrations such as UniFi attach their network info to the same device.
    """
    text = re.sub(r"[^0-9a-fA-F]", "", str(serial or "")).lower()
    if not _MAC_RE.match(text):
        return set()
    return {(CONNECTION_NETWORK_MAC, format_mac(text))}
