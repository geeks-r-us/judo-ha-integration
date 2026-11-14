"""Mapping helpers from decoded fields to Home Assistant metadata."""

from __future__ import annotations

from typing import Any

from .models import DecodedField


def suggest_device_class(field: DecodedField) -> str | None:
    """Infer HA device class for a field."""
    key = field.key.lower()
    if "temperature" in key:
        return "temperature"
    if "pressure" in key:
        return "pressure"
    if key == "battery_capacity_pct":
        return "battery"
    if key.endswith("_pct") or "percent" in key:
        return None
    if "water" in key and key.endswith("_l"):
        return "water"
    return None


def suggest_state_class(field: DecodedField) -> str | None:
    """Infer HA state class for a field."""
    key = field.key.lower()
    if (
        key.endswith("_total_l")
        or key.endswith("_total_m3")
        or key in {"regeneration_count", "maintenance_count", "soft_water_l", "soft_water_m3", "water_total_l", "water_total_m3"}
    ):
        return "total_increasing"
    if isinstance(field.value, (int, float)):
        return "measurement"
    return None


def suggest_icon(field: DecodedField) -> str | None:
    """Infer icon for a field."""
    key = field.key.lower()
    if "battery" in key:
        return "mdi:battery"
    if "water_scene" in key:
        return "mdi:shower"
    if "salt" in key:
        return "mdi:shaker"
    if "hardness" in key:
        return "mdi:water"
    if "flow" in key:
        return "mdi:waves"
    if "pressure" in key:
        return "mdi:gauge"
    if "temperature" in key:
        return "mdi:thermometer"
    if "error" in key or "alarm" in key:
        return "mdi:alert-circle"
    return "mdi:water-pump"


def normalize_field(field: DecodedField) -> DecodedField:
    """Return a field enriched with mapping defaults."""
    return DecodedField(
        key=field.key,
        value=field.value,
        name=field.name,
        source_command=field.source_command,
        unit=field.unit,
        device_class=field.device_class or suggest_device_class(field),
        state_class=field.state_class or suggest_state_class(field),
        icon=field.icon or suggest_icon(field),
        raw_hex=field.raw_hex,
    )


def fields_to_dict(fields: list[DecodedField]) -> dict[str, Any]:
    """Convert fields to key/value dictionary."""
    return {field.key: field.value for field in fields}
