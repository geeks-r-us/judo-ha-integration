"""Command specs for i-soft families."""

from __future__ import annotations

from typing import Any

from ..codec_primitives import (
    bitmask,
    encode_u8,
    encode_u16le,
    encode_u32le,
    u8,
    u16le,
    u32le,
    unix_ts_from_u32le,
)
from ...models import CommandDirection, CommandSpec, DeviceFamily
from .common import (
    INFO_SPECS,
    LEAKAGE_LIMIT_READ_WRITE_SPECS,
    RUNTIME_COUNTER_SPEC,
    SOFT_WATER_READ_SPEC,
    SOFTENER_LEAKAGE_ACTION_SPECS,
    START_REGENERATION_SPEC,
    TOTAL_WATER_READ_SPEC,
    WATER_STATS_SPECS,
    compose_specs,
)


# Usable salt capacity used to estimate fill level. The device only reports grams
# and a range; the app allows refills of up to 50 kg, so the tank is taken as 50 kg.
SALT_TANK_CAPACITY_G = 50000


def salt_level_pct(grams: int) -> float:
    """Estimate salt fill level in percent from the reported salt weight."""
    return round(max(0.0, min(100.0, grams / SALT_TANK_CAPACITY_G * 100.0)), 1)


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


def _decode_fw(data: bytes) -> dict[str, Any]:
    if len(data) < 3:
        return {"firmware_raw": data.hex().upper()}
    major = data[2]
    minor = data[1]
    patch_byte = data[0]
    if 32 <= patch_byte <= 126:
        patch = chr(patch_byte).lower()
    else:
        patch = f"{patch_byte:02X}"
    return {
        # API-KOMMANDOZEILEN examples encode firmware as [patch, minor, major].
        "firmware_version": f"{major}.{minor:02d}{patch}",
    }


def _decode_serial(data: bytes) -> dict[str, Any]:
    if len(data) < 4:
        return {"serial_number_raw": data.hex().upper()}
    return {"serial_number": str(u32le(data, 0))}


def _decode_commissioning(data: bytes) -> dict[str, Any]:
    if len(data) < 4:
        return {"commissioning_raw": data.hex().upper()}
    return {"commissioning_date": unix_ts_from_u32le(data, 0)}


def _decode_runtime(data: bytes) -> dict[str, Any]:
    if len(data) < 4:
        return {"runtime_raw": data.hex().upper()}
    minutes = data[0]
    hours = data[1]
    days = u16le(data, 2)
    return {
        "runtime_minutes": minutes,
        "runtime_hours": hours,
        "runtime_days": days,
    }


def _decode_cloud_node_id(data: bytes) -> dict[str, Any]:
    """Decode observed cloud node id payload."""
    if len(data) < 4:
        return {"cloud_node_id_raw": data.hex().upper()}
    return {"cloud_node_id": u32le(data, 0)}


def _decode_unit(data: bytes) -> dict[str, Any]:
    unit_map = {
        0: "dH",
        1: "eH",
        2: "fH",
        3: "gpg",
        4: "ppm",
        5: "mmol",
        6: "mval",
    }
    if not data:
        return {"hardness_unit_raw": None}
    return {"hardness_unit": unit_map.get(u8(data), f"unknown_{u8(data)}")}


def _decode_device_type(data: bytes) -> dict[str, Any]:
    if not data:
        return {"device_type_raw": None}
    raw = u8(data)
    return {
        "device_type_dec": raw,
        "device_type_hex": f"0x{raw:02X}",
    }


def _decode_total_water(data: bytes) -> dict[str, Any]:
    if len(data) < 4:
        return {"water_total_l_raw": data.hex().upper()}
    liters = u32le(data, 0)
    return {
        "water_total_l": liters,
        "water_total_m3": round(liters / 1000.0, 3),
    }


def _decode_soft_water(data: bytes) -> dict[str, Any]:
    if len(data) < 4:
        return {"soft_water_l_raw": data.hex().upper()}
    liters = u32le(data, 0)
    return {
        "soft_water_l": liters,
        "soft_water_m3": round(liters / 1000.0, 3),
    }


def _decode_target_hardness(data: bytes) -> dict[str, Any]:
    if len(data) == 1:
        return {"target_hardness": float(u8(data))}
    if len(data) >= 2:
        return {"target_hardness": float(u16le(data, 0))}
    return {"target_hardness": None}


def _encode_target_hardness(value: Any) -> str:
    """Encode target hardness (default 1-byte dH, optional raw hex passthrough)."""
    if isinstance(value, str):
        return _normalize_hex_payload(value)
    return encode_u8(int(value))


def _encode_vacation_mode(value: Any) -> str:
    """Encode vacation-mode flags with optional duration byte."""
    if isinstance(value, str):
        return _normalize_hex_payload(value)
    if isinstance(value, dict):
        flags = int(value.get("flags", value.get("value", 0)))
        days = value.get("days")
        return encode_u8(flags) if days is None else f"{encode_u8(flags)}{encode_u8(days)}"
    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            return encode_u8(int(value[0]))
        if len(value) == 2:
            return f"{encode_u8(int(value[0]))}{encode_u8(int(value[1]))}"
        raise ValueError("Vacation mode sequence must contain 1 or 2 items")
    return encode_u8(int(value))


def _encode_scene_configuration(value: Any) -> str:
    """Encode scene commands as raw hex or a single scene selector byte."""
    if isinstance(value, str):
        return _normalize_hex_payload(value)
    return encode_u8(int(value))


def _decode_salt(data: bytes) -> dict[str, Any]:
    if len(data) >= 4:
        grams = u16le(data, 0)
        days = u16le(data, 2)
        return {
            "salt_weight_g": grams,
            "salt_weight_kg": round(grams / 1000.0, 2),
            "salt_days_remaining": days,
            "salt_level_pct": salt_level_pct(grams),
        }
    if len(data) >= 2:
        grams = u16le(data, 0)
        return {
            "salt_weight_g": grams,
            "salt_weight_kg": round(grams / 1000.0, 2),
            "salt_level_pct": salt_level_pct(grams),
        }
    return {"salt_weight_g": None}


def _decode_alarm_flags(data: bytes) -> dict[str, Any]:
    if not data:
        return {"alarm_active": None}
    flags = bitmask(
        u8(data),
        {
            0x01: "alarm_active",
            0x02: "maintenance_required",
            0x04: "regeneration_active",
            0x08: "error_active",
            0x20: "microleakage_mode",
            0x40: "microleakage_auto_test",
            0x80: "global_leakage_off",
        },
    )
    return flags


def _decode_cloud_salt_or_absence(data: bytes) -> dict[str, Any]:
    """Decode cloud command 0x5E.

    i-soft devices report the salt reservoir here in the cloud payload with the same
    layout as command 0x56 (u16 grams, u16 days; verified against the Judo app).
    The 6-byte variant is the absence-limits payload of other families.
    """
    if len(data) == 4:
        return _decode_salt(data)
    return _decode_absence_limits(data)


def _decode_service_counters(data: bytes) -> dict[str, Any]:
    """Decode cloud command 0x07.

    Observed 63 09 | 03 00 | 04 00 on an i-soft SAFE+; matches the Judo app
    (next maintenance in 100 days = 2403 h, 3 maintenances). Inferred, undocumented.
    """
    if len(data) < 6:
        return {"service_counters_raw": data.hex().upper()}
    return {
        "maintenance_hours_remaining": u16le(data, 0),
        "maintenance_days_remaining": u16le(data, 0) // 24,
        "maintenance_count": u16le(data, 2),
    }


def _decode_absence_limits(data: bytes) -> dict[str, Any]:
    """Decode documented absence limits payload (flow/volume/time)."""
    if len(data) < 4:
        return {"absence_limits_raw": data.hex().upper()}

    result: dict[str, Any] = {
        "absence_limit_flow_lph": u16le(data, 0),
        "absence_limit_volume_l": u16le(data, 2),
    }
    if len(data) >= 6:
        result["absence_limit_duration_min"] = u16le(data, 4)
    return result


def _decode_cloud_profile_5d(data: bytes) -> dict[str, Any]:
    """Decode the 0x5D cloud profile payload.

    Layout observed on an i-soft SAFE+ (02 01 0B 64 AA10 0200 11); matched against the
    Judo app (battery 100 %, runtime 2 min). Both payload samples seen so far carry 0x64
    at offset 3 and 0x0002 at offset 6, so those two mappings are inferred, not documented.
    """
    result: dict[str, Any] = {"cloud_profile_5d_raw": data.hex().upper() if data else None}
    if len(data) >= 8:
        result["battery_capacity_pct"] = u8(data, 3)
        result["battery_runtime_min"] = u16le(data, 6)
        # Judo app reports "emergency power module: yes"; offset 1 is 0x01 in all samples.
        result["emergency_power_module"] = data[1] == 1
    return result


def get_specs() -> list[CommandSpec]:
    """Return i-soft command specifications."""
    return compose_specs(
        DeviceFamily.ISOFT,
        INFO_SPECS,
        (RUNTIME_COUNTER_SPEC, TOTAL_WATER_READ_SPEC, SOFT_WATER_READ_SPEC),
        WATER_STATS_SPECS,
        (START_REGENERATION_SPEC,),
        SOFTENER_LEAKAGE_ACTION_SPECS,
        LEAKAGE_LIMIT_READ_WRITE_SPECS,
        add=(
            CommandSpec(
                0x03,
                DeviceFamily.ISOFT,
                "Cloud Node Id",
                CommandDirection.READ,
                4,
                decoder=_decode_cloud_node_id,
            ),
            # Observed cloud payload variants expose water counters on 0x08/0x09.
            CommandSpec(
                0x07,
                DeviceFamily.ISOFT,
                "Service Counters",
                CommandDirection.READ,
                6,
                decoder=_decode_service_counters,
            ),
            CommandSpec(
                0x08,
                DeviceFamily.ISOFT,
                "Cloud Total Water",
                CommandDirection.READ,
                4,
                decoder=_decode_total_water,
                unit="L",
            ),
            CommandSpec(
                0x09,
                DeviceFamily.ISOFT,
                "Cloud Soft Water",
                CommandDirection.READ,
                4,
                decoder=_decode_soft_water,
                unit="L",
            ),
            CommandSpec(
                0x23,
                DeviceFamily.ISOFT,
                "Hardness Unit",
                CommandDirection.READ,
                1,
                decoder=_decode_unit,
            ),
            CommandSpec(
                0x24,
                DeviceFamily.ISOFT,
                "Set Hardness Unit",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
            CommandSpec(
                0x30,
                DeviceFamily.ISOFT,
                "Set Target Hardness",
                CommandDirection.WRITE,
                None,
                encoder=_encode_target_hardness,
                unit="dH",
            ),
            CommandSpec(
                0x36,
                DeviceFamily.ISOFT,
                "Activate Scene",
                CommandDirection.WRITE,
                None,
            ),
            CommandSpec(
                0x37,
                DeviceFamily.ISOFT,
                "Scene Configuration",
                CommandDirection.READ_WRITE,
                None,
                encoder=_encode_scene_configuration,
            ),
            CommandSpec(
                0x38,
                DeviceFamily.ISOFT,
                "Reset Scene",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
            CommandSpec(
                0x41,
                DeviceFamily.ISOFT,
                "Vacation Mode",
                CommandDirection.WRITE,
                None,
                encoder=_encode_vacation_mode,
            ),
            CommandSpec(
                0x43,
                DeviceFamily.ISOFT,
                "Status Payload",
                CommandDirection.READ,
                29,
                decoder=_decode_alarm_flags,
            ),
            CommandSpec(
                0x51,
                DeviceFamily.ISOFT,
                "Target Hardness",
                CommandDirection.READ,
                2,
                decoder=_decode_target_hardness,
                unit="dH",
            ),
            CommandSpec(
                0x56,
                DeviceFamily.ISOFT,
                "Salt Reservoir",
                CommandDirection.READ_WRITE,
                2,
                decoder=_decode_salt,
                encoder=encode_u16le,
                unit="g",
            ),
            CommandSpec(
                0x57,
                DeviceFamily.ISOFT,
                "Salt Warning Days",
                CommandDirection.READ_WRITE,
                1,
                encoder=encode_u8,
                unit="d",
            ),
            CommandSpec(
                0x58,
                DeviceFamily.ISOFT,
                "Service Address",
                CommandDirection.READ_WRITE,
                16,
                encoder=lambda v: str(v)
                .encode("ascii", errors="ignore")
                .ljust(16, b"\x00")
                .hex()
                .upper(),
            ),
            CommandSpec(
                0x59,
                DeviceFamily.ISOFT,
                "Read DateTime",
                CommandDirection.READ,
                6,
            ),
            CommandSpec(
                0x5A,
                DeviceFamily.ISOFT,
                "Write DateTime",
                CommandDirection.WRITE,
                6,
            ),
            CommandSpec(
                0x5D,
                DeviceFamily.ISOFT,
                "Cloud Protection Profile",
                CommandDirection.READ,
                None,
                decoder=_decode_cloud_profile_5d,
            ),
            CommandSpec(
                0x5E,
                DeviceFamily.ISOFT,
                "Salt Reservoir (Cloud)",
                CommandDirection.READ,
                4,
                decoder=_decode_cloud_salt_or_absence,
            ),
            CommandSpec(
                0xF3,
                DeviceFamily.ISOFT,
                "Salt Day Stats",
                CommandDirection.READ,
                4,
            ),
            CommandSpec(
                0xF4,
                DeviceFamily.ISOFT,
                "Salt Week Stats",
                CommandDirection.READ,
                3,
            ),
            CommandSpec(
                0xF5,
                DeviceFamily.ISOFT,
                "Salt Month Stats",
                CommandDirection.READ,
                3,
            ),
            CommandSpec(
                0xF6,
                DeviceFamily.ISOFT,
                "Salt Year Stats",
                CommandDirection.READ,
                2,
            ),
            CommandSpec(
                0xF7,
                DeviceFamily.ISOFT,
                "Flow Day Stats",
                CommandDirection.READ,
                4,
            ),
            CommandSpec(
                0xF8,
                DeviceFamily.ISOFT,
                "Flow Week Stats",
                CommandDirection.READ,
                3,
            ),
            CommandSpec(
                0xF9,
                DeviceFamily.ISOFT,
                "Flow Month Stats",
                CommandDirection.READ,
                3,
            ),
            CommandSpec(
                0xFA,
                DeviceFamily.ISOFT,
                "Flow Year Stats",
                CommandDirection.READ,
                2,
            ),
        ),
        overrides=(
            CommandSpec(
                0x01,
                DeviceFamily.ISOFT,
                "Firmware Version",
                CommandDirection.READ,
                3,
                decoder=_decode_fw,
            ),
            CommandSpec(
                0x06,
                DeviceFamily.ISOFT,
                "Serial Number",
                CommandDirection.READ,
                4,
                decoder=_decode_serial,
            ),
            CommandSpec(
                0x0E,
                DeviceFamily.ISOFT,
                "Commissioning Date",
                CommandDirection.READ,
                4,
                decoder=_decode_commissioning,
            ),
            CommandSpec(
                0x25,
                DeviceFamily.ISOFT,
                "Runtime Counter",
                CommandDirection.READ,
                4,
                decoder=_decode_runtime,
            ),
            CommandSpec(
                0x28,
                DeviceFamily.ISOFT,
                "Total Water",
                CommandDirection.READ,
                4,
                decoder=_decode_total_water,
                unit="L",
            ),
            CommandSpec(
                0x29,
                DeviceFamily.ISOFT,
                "Soft Water",
                CommandDirection.READ,
                4,
                decoder=_decode_soft_water,
                unit="L",
            ),
            CommandSpec(
                0x35,
                DeviceFamily.ISOFT,
                "Start Regeneration",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
                default_write_value=0,
            ),
            CommandSpec(
                0xFF,
                DeviceFamily.ISOFT,
                "Device Type",
                CommandDirection.READ,
                1,
                decoder=_decode_device_type,
            ),
        ),
    )
