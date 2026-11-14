"""Support for Judo iSoft writable number entities."""

from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_helpers import supports_write_command, writable_unique_id
from .const import DOMAIN
from .entity_base import JudoiSoftCommandEntity

_WRITE_TARGET_HARDNESS = 0x30
_TARGET_HARDNESS_MIN_DH = 1
_TARGET_HARDNESS_MAX_DH = 12
_OPTIMISTIC_WRITE_TTL_SEC = 30.0
_DEVICE_UNIT_TARGET_HARDNESS_MULTIPLIERS = {
    # Raw 2-byte retry values use the current device unit without the decimal separator.
    "dh": 1.0,
    "eh": 12.526,
    "fh": 17.848,
    "gpg": 10.427,
    "ppm": 17.848,
    "mmol": 1.7848,
    "mval": 3.5696,
}

_LOGGER = logging.getLogger(__name__)


def _supports_writable_target_hardness(snapshot: dict[str, Any]) -> bool:
    """Check if target hardness write should be exposed."""
    return supports_write_command(
        snapshot,
        _WRITE_TARGET_HARDNESS,
        allow_softener_fallback=True,
    )


def _hardness_display_unit(snapshot: dict[str, Any]) -> str:
    """Return the writable target-hardness unit."""
    # API-KOMMANDOZEILEN examples for read/write target hardness are expressed in dH
    # even when command 0x23 exposes a different display unit on the device.
    return "°dH"


def _device_unit_target_hardness_payload(snapshot: dict[str, Any], requested: int) -> str | None:
    """Return a 2-byte retry payload in the device's current hardness unit."""
    raw_unit = (
        snapshot.get("fields_by_key", {}).get("hardness_unit", {}).get("value")
        if isinstance(snapshot, dict)
        else None
    )
    normalized_unit = str(raw_unit or "").strip().lower()
    multiplier = _DEVICE_UNIT_TARGET_HARDNESS_MULTIPLIERS.get(normalized_unit)
    if multiplier is None or normalized_unit == "dh":
        return None

    raw_value = int(round(float(requested) * multiplier))
    if not (0 < raw_value <= 0xFFFF):
        return None
    return raw_value.to_bytes(2, byteorder="little").hex().upper()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Judo iSoft writable numbers."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data if isinstance(coordinator.data, dict) else {}

    if not _supports_writable_target_hardness(snapshot):
        return
    async_add_entities([JudoiSoftTargetHardnessNumber(coordinator, entry)])


class JudoiSoftTargetHardnessNumber(JudoiSoftCommandEntity, NumberEntity):
    """Writable target hardness number."""

    _attr_name = "Wunschwasserhärte"
    _attr_icon = "mdi:water"
    _attr_native_min_value = _TARGET_HARDNESS_MIN_DH
    _attr_native_max_value = _TARGET_HARDNESS_MAX_DH
    _attr_native_step = 1
    _attr_should_poll = False

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._optimistic_value: float | None = None
        self._optimistic_until: float | None = None
        snapshot = (
            coordinator.data
            if isinstance(coordinator.data, dict)
            else {}
        )
        self._attr_unique_id = writable_unique_id(
            config_entry,
            snapshot,
            command_id=_WRITE_TARGET_HARDNESS,
            key="target_hardness",
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return unit of measurement."""
        if not isinstance(self.coordinator.data, dict):
            return "°dH"
        return _hardness_display_unit(self.coordinator.data)

    @property
    def native_value(self) -> float | None:
        """Return current setpoint from decoded snapshot."""
        field = (
            self.coordinator.data.get("fields_by_key", {}).get("target_hardness", {})
            if isinstance(self.coordinator.data, dict)
            else {}
        )
        value = field.get("value")
        if isinstance(value, (int, float)):
            snapshot_value = float(value)
            optimistic = self._active_optimistic_value()
            if optimistic is not None:
                if int(round(snapshot_value)) == int(round(optimistic)):
                    self._clear_optimistic_value()
                    return snapshot_value
                return optimistic
            return snapshot_value
        return self._active_optimistic_value()

    async def async_set_native_value(self, value: float) -> None:
        """Set target hardness using protocol command 0x30."""
        requested = int(round(value))
        if not (_TARGET_HARDNESS_MIN_DH <= requested <= _TARGET_HARDNESS_MAX_DH):
            raise HomeAssistantError(
                "Target hardness out of range. Allowed range is 1-12 °dH."
            )
        attempted_payloads: set[str] = set()

        result = await self._async_execute_write(
            command=_WRITE_TARGET_HARDNESS,
            value=requested,
            error_prefix="Setting target hardness failed",
        )
        attempted_payloads.add(f"{requested:02X}")
        write_transport = str(result.get("transport", "auto"))
        await self.coordinator.async_request_refresh()

        readback = await self._async_read_target_hardness_with_settle(
            requested, write_transport
        )
        mismatch = readback is not None and int(round(readback)) != requested
        if mismatch:
            snapshot = self._snapshot()
            retry_payloads: list[str] = [
                # Compatibility fallback for devices expecting 2-byte payload shape.
                f"{requested:02X}00"
            ]
            if write_transport == "cloud":
                # API-KOMMANDOZEILEN examples always include command separator "00"
                # in the REST payload (e.g. /api/rest/300007 and /api/rest/30000A00).
                # Some cloud backends expect that shape in the data segment.
                retry_payloads.append(f"00{requested:02X}")
                retry_payloads.append(f"00{requested:02X}00")

            device_unit_payload = _device_unit_target_hardness_payload(
                snapshot, requested
            )
            if device_unit_payload is not None:
                retry_payloads.append(device_unit_payload)
                if write_transport == "cloud":
                    retry_payloads.append(f"00{device_unit_payload}")

            _LOGGER.debug(
                "Target hardness write mismatch requested=%s readback=%s transport=%s "
                "device_type=%s hardness_unit=%s retry_payloads=%s",
                requested,
                readback,
                write_transport,
                snapshot.get("device_info", {}).get("device_type"),
                snapshot.get("fields_by_key", {}).get("hardness_unit", {}).get("value"),
                retry_payloads,
            )

            for payload in retry_payloads:
                if payload in attempted_payloads:
                    continue
                write_result = await self._async_execute_write(
                    command=_WRITE_TARGET_HARDNESS,
                    value=payload,
                    error_prefix="Setting target hardness failed",
                    transport=write_transport,
                )
                attempted_payloads.add(payload)
                _LOGGER.debug(
                    "Target hardness retry payload=%s transport=%s raw=%s",
                    payload,
                    write_transport,
                    write_result.get("raw"),
                )
                await self.coordinator.async_request_refresh()
                readback = await self._async_read_target_hardness_with_settle(
                    requested, write_transport
                )
                if readback is not None and int(round(readback)) == requested:
                    break

        if readback is not None and int(round(readback)) != requested:
            if write_transport == "cloud":
                _LOGGER.debug(
                    "Target hardness cloud write was accepted but readback remained "
                    "%s °dH after the verification window; keeping optimistic value "
                    "until the next successful refresh.",
                    readback,
                )
            else:
                raise HomeAssistantError(
                    f"Target hardness not applied (device reports {readback} °dH)"
                )

        self._set_optimistic_value(float(requested))

    async def _async_read_target_hardness_with_settle(
        self, requested: int, transport: str
    ) -> float | None:
        """Read back target hardness, allowing cloud propagation lag."""
        readback = await self._async_read_target_hardness(transport)
        if transport != "cloud":
            return readback

        # Cloud command processing is occasionally delayed; verify for a short window
        # before treating the write as unsupported.
        for _ in range(3):
            if readback is not None and int(round(readback)) == requested:
                return readback
            await asyncio.sleep(1)
            await self.coordinator.async_request_refresh()
            readback = await self._async_read_target_hardness(transport)
        return readback

    async def _async_read_target_hardness(self, transport: str) -> float | None:
        """Read back target hardness from command 0x51/snapshot."""
        try:
            response = await self._async_execute_command(
                command=0x51,
                value=None,
                transport=transport,
            )
        except Exception:
            response = None

        if isinstance(response, dict) and response.get("status") == "ok":
            for field in response.get("fields", []):
                if field.get("key") != "target_hardness":
                    continue
                value = field.get("value")
                if isinstance(value, (int, float)):
                    return float(value)

        snapshot_value = (
            self.coordinator.data.get("fields_by_key", {})
            .get("target_hardness", {})
            .get("value")
            if isinstance(self.coordinator.data, dict)
            else None
        )
        if isinstance(snapshot_value, (int, float)):
            return float(snapshot_value)

        return None

    def _set_optimistic_value(self, value: float) -> None:
        """Keep a temporary optimistic value while refresh data catches up."""
        self._optimistic_value = value
        self._optimistic_until = monotonic() + _OPTIMISTIC_WRITE_TTL_SEC

    def _active_optimistic_value(self) -> float | None:
        """Return the active optimistic value if still within its TTL."""
        if self._optimistic_value is None:
            return None
        if self._optimistic_until is not None and monotonic() >= self._optimistic_until:
            self._clear_optimistic_value()
            return None
        return self._optimistic_value

    def _clear_optimistic_value(self) -> None:
        """Clear optimistic write state."""
        self._optimistic_value = None
        self._optimistic_until = None
