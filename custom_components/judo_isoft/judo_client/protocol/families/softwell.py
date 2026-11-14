"""Command specs for SOFTwell devices."""

from __future__ import annotations

from ...models import CommandDirection, CommandSpec, DeviceFamily
from ..codec_primitives import encode_u8, encode_u16le, u32le
from .common import (
    INFO_SPECS,
    RUNTIME_COUNTER_SPEC,
    SOFT_WATER_READ_SPEC,
    START_REGENERATION_SPEC,
    WATER_STATS_SPECS,
    compose_specs,
)


def _decode_soft_water(data: bytes) -> dict[str, int | float]:
    if len(data) < 4:
        return {"soft_water_l": 0}
    liters = u32le(data, 0)
    return {"soft_water_l": liters, "soft_water_m3": round(liters / 1000.0, 3)}


def get_specs() -> list[CommandSpec]:
    """Return SOFTwell command specifications."""
    return compose_specs(
        DeviceFamily.SOFTWELL,
        INFO_SPECS,
        (RUNTIME_COUNTER_SPEC, SOFT_WATER_READ_SPEC, START_REGENERATION_SPEC),
        WATER_STATS_SPECS,
        add=(
            CommandSpec(
                0x30,
                DeviceFamily.SOFTWELL,
                "Set Target Hardness",
                CommandDirection.WRITE,
                None,
                encoder=encode_u16le,
            ),
        ),
        overrides=(
            CommandSpec(
                0x29,
                DeviceFamily.SOFTWELL,
                "Soft Water",
                CommandDirection.READ,
                4,
                decoder=_decode_soft_water,
                unit="L",
            ),
            CommandSpec(
                0x35,
                DeviceFamily.SOFTWELL,
                "Start Regeneration",
                CommandDirection.WRITE,
                1,
                encoder=encode_u8,
                default_write_value=0,
            ),
        ),
    )
