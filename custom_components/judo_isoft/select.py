"""Support for Judo iSoft writable select entities."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_helpers import supports_write_command, writable_unique_id
from .const import DOMAIN
from .entity_base import JudoiSoftCommandEntity

_WRITE_HARDNESS_UNIT = 0x24
_OPTION_TO_CODE: dict[str, int] = {
    "°dH": 0,
    "°eH": 1,
    "°fH": 2,
    "gpg": 3,
    "ppm": 4,
    "mmol": 5,
    "mval": 6,
}
_PRO_DEVICE_TYPES: set[str] = {"0x58", "0x4b", "0x4c"}


def _supports_writable_hardness_unit(snapshot: dict[str, Any]) -> bool:
    """Check if hardness-unit write should be exposed."""
    return supports_write_command(
        snapshot,
        _WRITE_HARDNESS_UNIT,
        allow_softener_fallback=True,
    )


def _options_for_device(snapshot: dict[str, Any]) -> list[str]:
    """Return unit options based on device capabilities/type."""
    device_type = str(snapshot.get("device_info", {}).get("device_type", "")).strip().lower()
    if device_type in _PRO_DEVICE_TYPES:
        return ["°dH", "°fH"]
    return list(_OPTION_TO_CODE.keys())


def _decode_hardness_unit_option(raw_unit: str | None, options: list[str]) -> str | None:
    """Map decoded hardness unit token to UI option."""
    if raw_unit is None:
        return None
    token = str(raw_unit).strip()
    if token == "dH":
        token = "°dH"
    elif token == "eH":
        token = "°eH"
    elif token == "fH":
        token = "°fH"
    if token in options:
        return token
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Judo iSoft writable selects."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data if isinstance(coordinator.data, dict) else {}

    if not _supports_writable_hardness_unit(snapshot):
        return
    async_add_entities([JudoiSoftHardnessUnitSelect(coordinator, entry)])


class JudoiSoftHardnessUnitSelect(JudoiSoftCommandEntity, SelectEntity):
    """Writable hardness-unit select."""

    _attr_name = "Härteeinheit"
    _attr_icon = "mdi:format-letter-case"
    _attr_should_poll = False

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._optimistic_option: str | None = None
        self._fallback_option: str | None = None
        snapshot = coordinator.data if isinstance(coordinator.data, dict) else {}
        self._attr_unique_id = writable_unique_id(
            config_entry,
            snapshot,
            command_id=_WRITE_HARDNESS_UNIT,
            key="hardness_unit",
        )

    async def async_added_to_hass(self) -> None:
        """Populate hardness unit from direct read if snapshot lacks it."""
        await super().async_added_to_hass()
        await self._async_populate_option_from_command()

    @property
    def options(self) -> list[str]:
        """Return available unit options."""
        snapshot = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
        return _options_for_device(snapshot)

    @property
    def current_option(self) -> str | None:
        """Return currently selected unit from decoded snapshot."""
        snapshot = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
        raw_unit = snapshot.get("fields_by_key", {}).get("hardness_unit", {}).get("value")
        decoded = _decode_hardness_unit_option(raw_unit, self.options)
        return (
            decoded
            or self._optimistic_option
            or self._fallback_option
            or (self.options[0] if self.options else None)
        )

    async def _async_populate_option_from_command(self) -> None:
        """Read command 0x23 once when snapshot did not include hardness_unit."""
        snapshot = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
        raw_unit = snapshot.get("fields_by_key", {}).get("hardness_unit", {}).get("value")
        if _decode_hardness_unit_option(raw_unit, self.options) is not None:
            return

        try:
            result = await self._async_execute_command(
                command=0x23,
                value=None,
                transport="auto",
            )
        except Exception:
            return

        if result.get("status") != "ok":
            return

        for field in result.get("fields", []):
            if field.get("key") != "hardness_unit":
                continue
            option = _decode_hardness_unit_option(field.get("value"), self.options)
            if option:
                self._fallback_option = option
                self.async_write_ha_state()
            return

    async def async_select_option(self, option: str) -> None:
        """Set hardness unit using protocol command 0x24."""
        if option not in self.options:
            raise HomeAssistantError(f"Unsupported hardness unit option: {option}")

        value = _OPTION_TO_CODE[option]
        await self._async_execute_write(
            command=_WRITE_HARDNESS_UNIT,
            value=value,
            error_prefix="Setting hardness unit failed",
        )
        self._optimistic_option = option
        self._fallback_option = option
        await self.coordinator.async_request_refresh()
