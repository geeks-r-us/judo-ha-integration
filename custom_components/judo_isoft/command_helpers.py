"""Shared helpers for command capability and writable-entity handling."""

from __future__ import annotations

import re
from typing import Any, Iterable

from homeassistant.config_entries import ConfigEntry

_WRITE_DIRECTIONS = {"write", "read_write"}
_SOFTENER_SIGNAL_KEYS: tuple[str, ...] = (
    "salt_level_pct",
    "salt_weight_g",
    "target_hardness",
    "soft_water_l",
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_command_id(raw: Any) -> int | None:
    """Normalize command ids from int/decimal/hex-like values."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    text = str(raw).strip().lower()
    if not text:
        return None
    try:
        if text.startswith("0x"):
            return int(text, 16)
        if all(ch in "0123456789abcdef" for ch in text) and any(
            ch in "abcdef" for ch in text
        ):
            return int(text, 16)
        return int(text, 10)
    except ValueError:
        return None


def _normalize_payload_length(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def writable_capabilities(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized writable capabilities from snapshot metadata."""
    capabilities = snapshot.get("capabilities", [])
    result: list[dict[str, Any]] = []
    for cap in capabilities:
        if not isinstance(cap, dict):
            continue
        direction = str(cap.get("direction", "")).strip().lower()
        if direction not in _WRITE_DIRECTIONS:
            continue
        command_id = normalize_command_id(cap.get("command_id"))
        if command_id is None:
            continue
        result.append(
            {
                "command_id": command_id,
                "name": str(cap.get("name") or f"Command {command_id:02X}"),
                "direction": direction,
                "unit": cap.get("unit"),
                "payload_length": _normalize_payload_length(cap.get("payload_length")),
                "default_write_value": cap.get("default_write_value"),
            }
        )
    return result


def writable_commands(snapshot: dict[str, Any]) -> set[int]:
    """Return writable command ids from snapshot metadata."""
    return {cap["command_id"] for cap in writable_capabilities(snapshot)}


def is_softener_snapshot(snapshot: dict[str, Any]) -> bool:
    """Best-effort check whether snapshot belongs to a softener family."""
    family = str(snapshot.get("device_info", {}).get("family", "")).strip().lower()
    if family in {"i_soft", "softwell"}:
        return True

    fields_by_key = snapshot.get("fields_by_key", {})
    for key in _SOFTENER_SIGNAL_KEYS:
        field = fields_by_key.get(key, {})
        if isinstance(field, dict) and field.get("value") is not None:
            return True
    return False


def supports_write_command(
    snapshot: dict[str, Any],
    command_id: int,
    *,
    allow_softener_fallback: bool = False,
) -> bool:
    """Return whether a command write should be exposed."""
    if command_id in writable_commands(snapshot):
        return True
    return allow_softener_fallback and is_softener_snapshot(snapshot)


def writable_commands_with_softener_fallback(
    snapshot: dict[str, Any],
    *,
    fallback_commands: Iterable[int],
) -> set[int]:
    """Return writable command ids, optionally adding softener fallback ids."""
    commands = writable_commands(snapshot)
    if is_softener_snapshot(snapshot):
        commands.update(int(command_id) for command_id in fallback_commands)
    return commands


def _slug(value: Any) -> str:
    text = _NON_ALNUM_RE.sub("_", str(value).strip().lower()).strip("_")
    return text or "unknown"


def writable_unique_id(
    config_entry: ConfigEntry,
    snapshot: dict[str, Any],
    *,
    command_id: int,
    key: str,
) -> str:
    """Build normalized unique id for writable entities."""
    device_info = snapshot.get("device_info", {})
    raw_device_token = (
        device_info.get("device_id")
        or device_info.get("serial_number")
        or config_entry.data.get("host", "device")
    )
    return (
        f"{_slug(config_entry.entry_id)}_{_slug(raw_device_token)}_"
        f"cmd_{int(command_id):02X}_{_slug(key)}"
    )
