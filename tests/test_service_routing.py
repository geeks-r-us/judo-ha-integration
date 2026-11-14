"""Tests for service call coordinator routing."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.judo_isoft.__init__ import _coordinator_for_call
from custom_components.judo_isoft.const import ATTR_DEVICE_ID, DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override integration fixture for pure unit tests."""
    yield


def test_coordinator_for_call_matches_device_identifier() -> None:
    """Service routing should match configured device id/serial."""
    coordinator_a = SimpleNamespace(
        data={"device_info": {"device_id": "1001", "serial_number": "SERIAL_A"}}
    )
    coordinator_b = SimpleNamespace(
        data={"device_info": {"device_id": "1002", "serial_number": "SERIAL_B"}}
    )
    hass = SimpleNamespace(
        data={DOMAIN: {"entry_a": coordinator_a, "entry_b": coordinator_b}}
    )

    call = SimpleNamespace(data={ATTR_DEVICE_ID: "SERIAL_B"})
    assert _coordinator_for_call(hass, call) is coordinator_b

