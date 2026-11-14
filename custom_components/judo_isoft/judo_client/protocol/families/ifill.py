"""Command specs for i-fill devices."""

from __future__ import annotations

from ...models import CommandDirection, CommandSpec, DeviceFamily
from ..codec_primitives import encode_u8, u32le
from .common import (
    INFO_SPECS,
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
    """Return i-fill command specifications."""
    return compose_specs(
        DeviceFamily.IFILL,
        INFO_SPECS,
        (TOTAL_WATER_READ_SPEC,),
        WATER_STATS_SPECS,
        add=(
            CommandSpec(0x42, DeviceFamily.IFILL, "Threshold Data", CommandDirection.READ, 22),
            CommandSpec(
                0x50,
                DeviceFamily.IFILL,
                "Set Threshold Data",
                CommandDirection.WRITE,
                22,
            ),
            CommandSpec(
                0x51,
                DeviceFamily.IFILL,
                "Close Protection",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x52,
                DeviceFamily.IFILL,
                "Open Protection",
                CommandDirection.WRITE,
                0,
            ),
            CommandSpec(
                0x53,
                DeviceFamily.IFILL,
                "Fill Valve Mode",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
            CommandSpec(
                0x54,
                DeviceFamily.IFILL,
                "Relay Mode",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
            ),
        ),
        overrides=(
            CommandSpec(
                0x28,
                DeviceFamily.IFILL,
                "Total Water",
                CommandDirection.READ,
                4,
                decoder=_decode_total_water,
                unit="L",
            ),
        ),
    )
