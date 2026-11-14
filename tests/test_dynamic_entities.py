"""Tests for dynamic entities in new stack mode."""

from dataclasses import dataclass, field

import pytest

from custom_components.judo_isoft.binary_sensor import JudoiSoftDynamicBinarySensor
from custom_components.judo_isoft.sensor import JudoiSoftDynamicSensor


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


@dataclass
class DummyConfigEntry:
    """Minimal config entry for entity tests."""

    entry_id: str = "entry-1"
    data: dict = field(default_factory=lambda: {"host": "device-1"})


class DummyCoordinator:
    """Minimal coordinator object compatible with CoordinatorEntity."""

    def __init__(self) -> None:
        self.last_update_success = True
        self.data = {
            "device_info": {
                "model": "iSoft",
                "manufacturer": "Judo Wasseraufbereitung GmbH",
                "serial_number": "123",
            },
            "system_status": {"online": True},
            "fields_by_key": {
                "water_total_l": {
                    "key": "water_total_l",
                    "name": "Water Total L",
                    "value": 1057516,
                    "unit": "L",
                    "source_command": 0x28,
                    "state_class": "total_increasing",
                    "device_class": "water",
                    "icon": "mdi:water",
                },
                "alarm_active": {
                    "key": "alarm_active",
                    "name": "Alarm Active",
                    "value": True,
                    "source_command": 0x43,
                    "icon": "mdi:alert",
                },
            },
            "connection": {"transport": "cloud"},
        }

    def async_add_listener(self, update_callback):
        return lambda: None


def test_dynamic_sensor_native_value() -> None:
    """Dynamic sensor should read value from coordinator fields."""
    coordinator = DummyCoordinator()
    entry = DummyConfigEntry()
    field = coordinator.data["fields_by_key"]["water_total_l"]

    sensor = JudoiSoftDynamicSensor(coordinator, entry, field)

    assert sensor.native_value == 1057516
    assert sensor.available is True


def test_dynamic_binary_sensor_is_on() -> None:
    """Dynamic binary sensor should map boolean field."""
    coordinator = DummyCoordinator()
    entry = DummyConfigEntry()
    field = coordinator.data["fields_by_key"]["alarm_active"]

    sensor = JudoiSoftDynamicBinarySensor(coordinator, entry, field)

    assert sensor.is_on is True
    assert sensor.available is True


def test_online_binary_sensor_reflects_device_and_update_state() -> None:
    """Online sensor reports the device status and goes off when updates fail."""
    from types import SimpleNamespace

    from custom_components.judo_isoft.binary_sensor import JudoiSoftOnlineBinarySensor

    coordinator = SimpleNamespace(
        last_update_success=True,
        data={"fields_by_key": {"device_online": {"value": True}}},
    )
    entry = SimpleNamespace(entry_id="abc", data={})
    sensor = JudoiSoftOnlineBinarySensor(coordinator, entry)

    assert sensor.available is True
    assert sensor.is_on is True

    coordinator.data = {"fields_by_key": {"device_online": {"value": False}}}
    assert sensor.is_on is False

    coordinator.data = {"fields_by_key": {"device_online": {"value": True}}}
    coordinator.last_update_success = False
    assert sensor.is_on is False
    assert sensor.available is True
