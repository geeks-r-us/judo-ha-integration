"""Support for Judo iSoft action buttons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .command_helpers import (
    writable_capabilities,
    writable_commands_with_softener_fallback,
    writable_unique_id,
)
from .const import DOMAIN
from .entity_base import JudoiSoftCommandEntity


@dataclass(frozen=True)
class _CommandButtonDef:
    key: str
    name: str
    icon: str
    command_id: int
    value: Any | None = None


_EXPLICIT_ACTION_BUTTONS: tuple[_CommandButtonDef, ...] = (
    _CommandButtonDef(
        key="start_regeneration",
        name="Start Regeneration",
        icon="mdi:refresh",
        command_id=0x35,
        value=0,
    ),
    _CommandButtonDef(
        key="close_leakage_protection",
        name="Close Leakage Protection",
        icon="mdi:valve-closed",
        command_id=0x3C,
        value=None,
    ),
    _CommandButtonDef(
        key="open_leakage_protection",
        name="Open Leakage Protection",
        icon="mdi:valve-open",
        command_id=0x3D,
        value=None,
    ),
)

_EXPLICIT_COMMAND_IDS = {button.command_id for button in _EXPLICIT_ACTION_BUTTONS}


def _slugify(text: str) -> str:
    return "_".join(part for part in str(text).strip().lower().split() if part)


def _icon_for_capability(name: str) -> str:
    lowered = name.lower()
    if "open" in lowered:
        return "mdi:valve-open"
    if "close" in lowered:
        return "mdi:valve-closed"
    if "start" in lowered:
        return "mdi:play"
    if "stop" in lowered:
        return "mdi:stop"
    if "reset" in lowered:
        return "mdi:restart"
    return "mdi:flash"


def _build_generated_button_definition(capability: dict[str, Any]) -> _CommandButtonDef | None:
    command_id = int(capability["command_id"])
    payload_length = capability.get("payload_length")
    default_value = capability.get("default_write_value")

    if payload_length == 0:
        value: Any | None = None
    elif default_value is not None:
        value = default_value
    else:
        return None

    name = str(capability.get("name") or f"Command {command_id:02X}")
    key = f"generated_{command_id:02X}_{_slugify(name)}"
    return _CommandButtonDef(
        key=key,
        name=name,
        icon=_icon_for_capability(name),
        command_id=command_id,
        value=value,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Judo iSoft action buttons."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    snapshot = coordinator.data if isinstance(coordinator.data, dict) else {}
    supported_explicit_commands = writable_commands_with_softener_fallback(
        snapshot,
        fallback_commands=_EXPLICIT_COMMAND_IDS,
    )

    entities: list[ButtonEntity] = []
    for button in _EXPLICIT_ACTION_BUTTONS:
        if button.command_id not in supported_explicit_commands:
            continue
        entities.append(
            JudoiSoftActionButton(
                coordinator,
                entry,
                button,
                generated=False,
            )
        )

    generated_command_ids: set[int] = set()
    for capability in writable_capabilities(snapshot):
        command_id = int(capability["command_id"])
        if command_id in _EXPLICIT_COMMAND_IDS or command_id in generated_command_ids:
            continue
        definition = _build_generated_button_definition(capability)
        if definition is None:
            continue
        entities.append(
            JudoiSoftActionButton(
                coordinator,
                entry,
                definition,
                generated=True,
            )
        )
        generated_command_ids.add(command_id)

    async_add_entities(entities)


class _BaseButton(JudoiSoftCommandEntity, ButtonEntity):
    """Common behavior for action buttons."""

    def __init__(self, coordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)


class JudoiSoftActionButton(_BaseButton):
    """Button entity that executes one protocol write command."""

    def __init__(
        self,
        coordinator,
        config_entry: ConfigEntry,
        definition: _CommandButtonDef,
        *,
        generated: bool = False,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self._definition = definition
        self._generated = generated
        self._attr_name = definition.name
        self._attr_icon = definition.icon
        snapshot = coordinator.data if isinstance(coordinator.data, dict) else {}
        self._attr_unique_id = writable_unique_id(
            config_entry,
            snapshot,
            command_id=definition.command_id,
            key=f"button_{definition.key}",
        )

    async def async_press(self) -> None:
        """Execute configured action command."""
        await self._async_execute_write(
            command=self._definition.command_id,
            value=self._definition.value,
            error_prefix=(
                f"Generated action {self._definition.name} failed"
                if self._generated
                else f"Action {self._definition.name} failed"
            ),
        )
        await self.coordinator.async_request_refresh()
