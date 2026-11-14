"""Command specs for i-dos devices."""

from __future__ import annotations

from typing import Any

from ...models import CommandDirection, CommandSpec, DeviceFamily
from ..codec_primitives import encode_u8, encode_u16le, u16le, u32le
from .common import INFO_SPECS, TOTAL_WATER_READ_SPEC, WATER_STATS_SPECS, compose_specs


def _decode_status(data: bytes) -> dict[str, int | bool]:
    if len(data) < 29:
        return {"status_raw": int.from_bytes(data, "little", signed=False)}
    flags = {
        "pump_mode": data[1],
        "concentration_mode": data[3],
        "error_code": u16le(data, 5),
        "warning_code": u16le(data, 7),
        "dosage_ml": u16le(data, 15),
        "flow_lph": u16le(data, 17),
        "remaining_container": u16le(data, 19),
        "water_total_l": u32le(data, 21),
    }
    return flags


def _normalize_hex_payload(value: str) -> str:
    text = str(value).strip()
    if text.startswith("0x"):
        text = text[2:]
    if not text:
        raise ValueError("Payload is empty")
    if any(ch not in "0123456789abcdefABCDEF" for ch in text):
        raise ValueError("Payload must be hex")
    if len(text) % 2:
        text = f"0{text}"
    return text.upper()


def _encode_dosage(value: Any) -> str:
    """Encode dosage payload as reserved byte plus concentration byte."""
    if isinstance(value, str):
        return _normalize_hex_payload(value)
    if isinstance(value, dict):
        reserved = int(value.get("reserved", 0))
        concentration = int(value.get("concentration", value.get("value", 0)))
        return f"{encode_u8(reserved)}{encode_u8(concentration)}"
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError("Dosage payload sequence must contain 2 items")
        return f"{encode_u8(int(value[0]))}{encode_u8(int(value[1]))}"
    return f"00{encode_u8(int(value))}"


def _encode_pump_mode(value: Any) -> str:
    """Encode pump mode as mode byte plus little-endian RPM."""
    if isinstance(value, str):
        return _normalize_hex_payload(value)
    if isinstance(value, dict):
        mode = int(value.get("mode", value.get("value", 0)))
        rpm = int(value.get("rpm", 0))
        return f"{encode_u8(mode)}{encode_u16le(rpm)}"
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError("Pump mode payload sequence must contain 2 items")
        return f"{encode_u8(int(value[0]))}{encode_u16le(int(value[1]))}"
    return f"{encode_u8(int(value))}0000"


def get_specs() -> list[CommandSpec]:
    """Return i-dos command specifications."""
    return compose_specs(
        DeviceFamily.IDOS,
        INFO_SPECS,
        (TOTAL_WATER_READ_SPEC,),
        WATER_STATS_SPECS,
        add=(
            CommandSpec(
                0x43,
                DeviceFamily.IDOS,
                "Status Data",
                CommandDirection.READ,
                29,
                decoder=_decode_status,
            ),
            CommandSpec(
                0x52,
                DeviceFamily.IDOS,
                "Set Dosage",
                CommandDirection.WRITE,
                2,
                encoder=_encode_dosage,
                default_write_value="0002",
            ),
            CommandSpec(
                0x53,
                DeviceFamily.IDOS,
                "Set Pump Mode",
                CommandDirection.WRITE,
                3,
                encoder=_encode_pump_mode,
            ),
            CommandSpec(
                0x61,
                DeviceFamily.IDOS,
                "Read DateTime",
                CommandDirection.READ,
                6,
            ),
            CommandSpec(
                0x71,
                DeviceFamily.IDOS,
                "Write DateTime",
                CommandDirection.WRITE,
                6,
            ),
            CommandSpec(
                0x63,
                DeviceFamily.IDOS,
                "Read Dosing",
                CommandDirection.READ,
                6,
            ),
        ),
    )
