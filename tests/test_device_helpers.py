"""Tests for device registry helpers."""

import pytest

from custom_components.judo_isoft.device_helpers import mac_connections


@pytest.fixture(autouse=True)
def enable_custom_integrations():
    """Pure unit test, no Home Assistant instance needed."""
    yield


@pytest.mark.parametrize("serial", ["aabbccddeeff", "AA:BB:CC:DD:EE:FF", "aa-bb-cc-dd-ee-ff"])
def test_mac_serial_becomes_network_connection(serial) -> None:
    assert mac_connections(serial) == {("mac", "aa:bb:cc:dd:ee:ff")}


@pytest.mark.parametrize("serial", [None, "", "12345678", "Unknown"])
def test_non_mac_serial_gives_no_connection(serial) -> None:
    assert mac_connections(serial) == set()
