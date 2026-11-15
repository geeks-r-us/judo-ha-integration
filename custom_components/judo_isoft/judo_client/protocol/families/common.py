"""Shared command-spec blocks and composition helpers."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ...models import CommandDirection, CommandSpec, DeviceFamily
from ..codec_primitives import encode_u8, encode_u16le, u8

_TEMPLATE_FAMILY = DeviceFamily.UNKNOWN


def _decode_device_type(data: bytes) -> dict[str, int | str | None]:
    """Decode a one-byte device type payload."""
    if not data:
        return {"device_type_raw": None}
    raw = u8(data)
    return {
        "device_type_dec": raw,
        "device_type_hex": f"0x{raw:02X}",
    }


def _template_spec(
    command_id: int,
    name: str,
    direction: CommandDirection,
    length: int | None,
    *,
    decoder=None,
    encoder=None,
    unit: str | None = None,
    default_write_value: object | None = None,
) -> CommandSpec:
    return CommandSpec(
        command_id=command_id,
        family=_TEMPLATE_FAMILY,
        name=name,
        direction=direction,
        length=length,
        decoder=decoder,
        encoder=encoder,
        unit=unit,
        default_write_value=default_write_value,
    )


INFO_SPECS: tuple[CommandSpec, ...] = (
    _template_spec(0x01, "Firmware Version", CommandDirection.READ, 3),
    _template_spec(0x06, "Serial Number", CommandDirection.READ, 4),
    _template_spec(0x0E, "Commissioning Date", CommandDirection.READ, 4),
    _template_spec(
        0xFF,
        "Device Type",
        CommandDirection.READ,
        1,
        decoder=_decode_device_type,
    ),
)

RUNTIME_COUNTER_SPEC = _template_spec(
    0x25,
    "Runtime Counter",
    CommandDirection.READ,
    4,
)

TOTAL_WATER_READ_SPEC = _template_spec(
    0x28,
    "Total Water",
    CommandDirection.READ,
    4,
    unit="L",
)

SOFT_WATER_READ_SPEC = _template_spec(
    0x29,
    "Soft Water",
    CommandDirection.READ,
    4,
    unit="L",
)

START_REGENERATION_SPEC = CommandSpec(
    0x35,
    _TEMPLATE_FAMILY,
    "Start Regeneration",
    CommandDirection.WRITE,
    1,
    encoder=encode_u8,
    default_write_value=0,
)

SOFTENER_LEAKAGE_ACTION_SPECS: tuple[CommandSpec, ...] = (
    _template_spec(0x3C, "Close Leakage Protection", CommandDirection.WRITE, 0),
    _template_spec(0x3D, "Open Leakage Protection", CommandDirection.WRITE, 0),
)

LEAKAGE_LIMIT_READ_WRITE_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        0x3E,
        _TEMPLATE_FAMILY,
        "Max Draw Duration",
        CommandDirection.READ_WRITE,
        1,
        encoder=encode_u8,
        unit="min",
    ),
    CommandSpec(
        0x3F,
        _TEMPLATE_FAMILY,
        "Max Flow",
        CommandDirection.READ_WRITE,
        2,
        encoder=encode_u16le,
        unit="L/h",
    ),
    CommandSpec(
        0x40,
        _TEMPLATE_FAMILY,
        "Max Draw Volume",
        CommandDirection.READ_WRITE,
        2,
        encoder=encode_u16le,
        unit="L",
    ),
)

LEAKAGE_LIMIT_WRITE_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec(
        0x3E,
        _TEMPLATE_FAMILY,
        "Max Draw Duration",
        CommandDirection.WRITE,
        1,
        encoder=encode_u8,
    ),
    CommandSpec(
        0x3F,
        _TEMPLATE_FAMILY,
        "Max Flow",
        CommandDirection.WRITE,
        2,
        encoder=encode_u16le,
    ),
    CommandSpec(
        0x40,
        _TEMPLATE_FAMILY,
        "Max Draw Volume",
        CommandDirection.WRITE,
        2,
        encoder=encode_u16le,
    ),
)

WATER_STATS_SPECS: tuple[CommandSpec, ...] = (
    _template_spec(0xFB, "Water Day Stats", CommandDirection.READ, 4),
    _template_spec(0xFC, "Water Week Stats", CommandDirection.READ, 3),
    _template_spec(0xFD, "Water Month Stats", CommandDirection.READ, 3),
    _template_spec(0xFE, "Water Year Stats", CommandDirection.READ, 2),
)


def compose_specs(
    family: DeviceFamily,
    *blocks: Iterable[CommandSpec],
    add: Iterable[CommandSpec] = (),
    remove: Iterable[int] = (),
    overrides: Iterable[CommandSpec] = (),
) -> list[CommandSpec]:
    """Compose family command specs from shared blocks plus deltas."""
    specs: dict[int, CommandSpec] = {}

    for block in blocks:
        for spec in block:
            specs[spec.command_id] = replace(spec, family=family)

    for command_id in remove:
        specs.pop(int(command_id), None)

    for spec in overrides:
        specs[spec.command_id] = replace(spec, family=family)

    for spec in add:
        specs[spec.command_id] = replace(spec, family=family)

    return list(specs.values())


__all__ = [
    "INFO_SPECS",
    "LEAKAGE_LIMIT_READ_WRITE_SPECS",
    "LEAKAGE_LIMIT_WRITE_SPECS",
    "RUNTIME_COUNTER_SPEC",
    "SOFT_WATER_READ_SPEC",
    "SOFTENER_LEAKAGE_ACTION_SPECS",
    "START_REGENERATION_SPEC",
    "TOTAL_WATER_READ_SPEC",
    "WATER_STATS_SPECS",
    "compose_specs",
]
