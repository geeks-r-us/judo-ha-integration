"""Command specs for i-safe devices."""

from __future__ import annotations

from ...models import CommandDirection, CommandSpec, DeviceFamily
from ..codec_primitives import encode_u8, u32le
from .common import (
    INFO_SPECS,
    LEAKAGE_LIMIT_WRITE_SPECS,
    TOTAL_WATER_READ_SPEC,
    WATER_STATS_SPECS,
    compose_specs,
)


def _decode_total_water(data: bytes) -> dict[str, int | float]:
    if len(data) < 4:
        return {"water_total_l": 0}
    liters = u32le(data, 0)
    return {"water_total_l": liters, "water_total_m3": round(liters / 1000.0, 3)}


def get_specs() -> list[CommandSpec]:
    """Return i-safe command specifications."""
    return compose_specs(
        DeviceFamily.ISAFE,
        INFO_SPECS,
        (TOTAL_WATER_READ_SPEC,),
        WATER_STATS_SPECS,
        LEAKAGE_LIMIT_WRITE_SPECS,
        add=(
            CommandSpec(
                0x50,
                DeviceFamily.ISAFE,
                "Leakage Settings",
                CommandDirection.WRITE,
                7,
            ),
            CommandSpec(
                0x51,
                DeviceFamily.ISAFE,
                "Close Protection",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x52,
                DeviceFamily.ISAFE,
                "Open Protection",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x53,
                DeviceFamily.ISAFE,
                "Set Sleep Duration",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
            CommandSpec(
                0x54,
                DeviceFamily.ISAFE,
                "Start Sleep",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x55,
                DeviceFamily.ISAFE,
                "Stop Sleep",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x56,
                DeviceFamily.ISAFE,
                "Set Vacation Mode Type",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
            CommandSpec(
                0x57,
                DeviceFamily.ISAFE,
                "Start Vacation",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x58,
                DeviceFamily.ISAFE,
                "Stop Vacation",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x59,
                DeviceFamily.ISAFE,
                "Read DateTime",
                CommandDirection.READ,
                6,
            ),
            CommandSpec(
                0x5A,
                DeviceFamily.ISAFE,
                "Write DateTime",
                CommandDirection.WRITE,
                6,
            ),
            CommandSpec(
                0x5B,
                DeviceFamily.ISAFE,
                "Microleakage Mode",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
            CommandSpec(
                0x5C,
                DeviceFamily.ISAFE,
                "Start Microleakage Test",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x5D,
                DeviceFamily.ISAFE,
                "Start Learn Mode",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x5E,
                DeviceFamily.ISAFE,
                "Read Absence Limits",
                CommandDirection.READ,
                6,
            ),
            CommandSpec(
                0x5F,
                DeviceFamily.ISAFE,
                "Set Absence Limits",
                CommandDirection.WRITE,
                6,
            ),
            CommandSpec(
                0x60,
                DeviceFamily.ISAFE,
                "Read Absence Slot",
                CommandDirection.READ,
                7,
            ),
            CommandSpec(
                0x61,
                DeviceFamily.ISAFE,
                "Set Absence Slot",
                CommandDirection.WRITE,
                7,
            ),
            CommandSpec(
                0x62,
                DeviceFamily.ISAFE,
                "Clear Absence Slot",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
            CommandSpec(
                0x63,
                DeviceFamily.ISAFE,
                "Reset Message",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x64,
                DeviceFamily.ISAFE,
                "Learn Mode State",
                CommandDirection.READ,
                3,
            ),
            CommandSpec(
                0x65,
                DeviceFamily.ISAFE,
                "Microleakage State",
                CommandDirection.READ,
                1,
            ),
            CommandSpec(
                0x66,
                DeviceFamily.ISAFE,
                "Sleep Duration",
                CommandDirection.READ,
                1,
            ),
        ),
        overrides=(
            CommandSpec(
                0x28,
                DeviceFamily.ISAFE,
                "Total Water",
                CommandDirection.READ,
                4,
                decoder=_decode_total_water,
                unit="L",
            ),
        ),
    )
