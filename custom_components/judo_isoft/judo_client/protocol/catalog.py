"""Machine-readable command catalog for Judo families."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from ..models import CommandCapability, CommandDirection, CommandSpec, DeviceFamily
from .families import (
    get_idos_specs,
    get_ifill_specs,
    get_isafe_specs,
    get_isoft_specs,
    get_softwell_specs,
)


DEVICE_TYPE_TO_FAMILY: dict[str, DeviceFamily] = {
    # i-soft
    "0x32": DeviceFamily.ISOFT,
    "0x33": DeviceFamily.ISOFT,
    "0x42": DeviceFamily.ISOFT,
    "0x43": DeviceFamily.ISOFT,
    "0x4b": DeviceFamily.ISOFT,
    "0x4c": DeviceFamily.ISOFT,
    "0x53": DeviceFamily.ISOFT,
    "0x54": DeviceFamily.ISOFT,
    "0x57": DeviceFamily.ISOFT,
    "0x58": DeviceFamily.ISOFT,
    "0x67": DeviceFamily.ISOFT,
    # SOFTwell
    "0x34": DeviceFamily.SOFTWELL,
    "0x35": DeviceFamily.SOFTWELL,
    "0x36": DeviceFamily.SOFTWELL,
    "0x47": DeviceFamily.SOFTWELL,
    "0x48": DeviceFamily.SOFTWELL,
    "0x59": DeviceFamily.SOFTWELL,
    "0x5A": DeviceFamily.SOFTWELL,
    "0x62": DeviceFamily.SOFTWELL,
    "0x63": DeviceFamily.SOFTWELL,
    "0x64": DeviceFamily.SOFTWELL,
    # i-fill
    "0x3C": DeviceFamily.IFILL,
    # i-safe
    "0x44": DeviceFamily.ISAFE,
    # i-dos
    "0x41": DeviceFamily.IDOS,
}


DEVICE_TYPE_TO_MODEL: dict[str, str] = {
    "0x32": "i-soft",
    "0x53": "i-soft",
    "0x33": "i-soft SAFE+",
    "0x57": "i-soft SAFE+",
    "0x42": "i-soft K SAFE+",
    "0x67": "i-soft K SAFE+",
    "0x43": "i-soft K",
    "0x54": "i-soft K",
    "0x58": "i-soft PRO",
    "0x4b": "i-soft PRO",
    "0x4c": "i-soft PRO L",
}


def _normalize_device_type(value: str | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, int):
        return f"0x{value:02X}".lower()
    text = str(value).strip().lower()
    if text.startswith("0x"):
        return text
    # API-KOMMANDOZEILEN commonly encodes device types as 1-byte hex without prefix.
    if all(ch in "0123456789abcdef" for ch in text) and len(text) <= 2:
        hex_candidate = f"0x{text.zfill(2)}"
        if hex_candidate in DEVICE_TYPE_TO_FAMILY:
            return hex_candidate
    try:
        # Numeric decimal as string.
        intval = int(text, 10)
        dec_candidate = f"0x{intval:02X}".lower()
        if dec_candidate in DEVICE_TYPE_TO_FAMILY:
            return dec_candidate
        return dec_candidate
    except ValueError:
        return text


def infer_family(device_type: str | int | None) -> DeviceFamily:
    """Infer family from device type."""
    normalized = _normalize_device_type(device_type)
    return DEVICE_TYPE_TO_FAMILY.get(normalized, DeviceFamily.UNKNOWN)


def model_name(device_type: str | int | None, family: DeviceFamily) -> str:
    """Return the marketing model name for a device type (fallback: family)."""
    name = DEVICE_TYPE_TO_MODEL.get(_normalize_device_type(device_type))
    return f"Judo {name}" if name else f"Judo {family.value}"


def format_firmware_version(value: str | None) -> str | None:
    """Format firmware as shown in the Judo app (e.g. 6E0203 / 3.2n -> 3.02n)."""
    if not value:
        return value
    text = str(value).strip()
    if re.fullmatch(r"[0-9A-Fa-f]{6}", text):
        patch, minor, major = bytes.fromhex(text)
        letter = chr(patch).lower() if 32 <= patch <= 126 else f"{patch:02X}"
        return f"{major}.{minor:02d}{letter}"
    match = re.fullmatch(r"(\d+)\.(\d+)([A-Za-z]?)", text)
    if match:
        return f"{match.group(1)}.{int(match.group(2)):02d}{match.group(3)}"
    return text


def all_specs() -> list[CommandSpec]:
    """Return all command specs across supported families."""
    specs: list[CommandSpec] = []
    specs.extend(get_isoft_specs())
    specs.extend(get_softwell_specs())
    specs.extend(get_ifill_specs())
    specs.extend(get_isafe_specs())
    specs.extend(get_idos_specs())
    return specs


def specs_by_family() -> dict[DeviceFamily, list[CommandSpec]]:
    """Return command specs grouped by family."""
    grouped: dict[DeviceFamily, list[CommandSpec]] = defaultdict(list)
    for spec in all_specs():
        grouped[spec.family].append(spec)
    return dict(grouped)


def build_capabilities(specs: Iterable[CommandSpec]) -> list[CommandCapability]:
    """Build command capabilities list from specs."""
    return [
        CommandCapability(
            command_id=spec.command_id,
            name=spec.name,
            direction=spec.direction,
            unit=spec.unit,
            payload_length=spec.length,
            default_write_value=spec.default_write_value,
        )
        for spec in specs
    ]


def normalize_command_id(command: str | int) -> int:
    """Normalize command values from decimal/hex string or int."""
    known_ids = {spec.command_id for spec in all_specs()}

    if isinstance(command, int):
        if command in known_ids:
            return command
        # Accept decimal ints that were entered from hex-looking docs (e.g. 28 -> 0x28).
        alt = int(str(command), 16)
        if alt in known_ids:
            return alt
        return command

    text = str(command).strip().lower()
    if text.startswith("0x"):
        return int(text, 16)

    if text.endswith("h"):
        return int(text[:-1], 16)

    # If only hex characters and includes alpha, treat as hex.
    is_hex_chars = all(ch in "0123456789abcdef" for ch in text)
    if is_hex_chars and any(ch in "abcdef" for ch in text):
        return int(text, 16)

    if is_hex_chars:
        # In Judo docs command ids are normally represented as hex without prefix.
        as_hex = int(text, 16)
        as_dec = int(text, 10)
        if as_hex in known_ids:
            return as_hex
        if as_dec in known_ids:
            return as_dec
        return as_hex

    return int(text, 10)
