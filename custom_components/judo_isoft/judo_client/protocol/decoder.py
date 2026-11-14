"""Registry-based decoder engine for Judo commands."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import (
    CommandDirection,
    CommandResult,
    CommandSpec,
    DecodedCommandResult,
    DecodedField,
    DeviceFamily,
    TransportMode,
)
from .catalog import normalize_command_id, specs_by_family
from .codec_primitives import ensure_bytes_from_hex


@dataclass(slots=True)
class DecodingContext:
    """Decoder context for a given family."""

    family: DeviceFamily


class DecoderRegistry:
    """Decoder/encoder registry backed by command specs."""

    _FIELD_NAME_OVERRIDES = {
        "salt_days_remaining": "Salt Range Days",
        # Current percent is derived from a fixed 25 kg basis, not a device-reported
        # or app-reported fill percentage.
        "salt_level_pct": "Salt Level (Estimated)",
        "cloud_node_id": "Device Number",
    }

    def __init__(self) -> None:
        grouped = specs_by_family()
        self._by_family: dict[DeviceFamily, dict[int, CommandSpec]] = {
            family: {spec.command_id: spec for spec in specs}
            for family, specs in grouped.items()
        }

    def get_spec(self, family: DeviceFamily, command_id: int) -> CommandSpec | None:
        """Return spec for family and command id."""
        if family in self._by_family and command_id in self._by_family[family]:
            return self._by_family[family][command_id]

        # Fallback to i-soft/shared specs for unknown or partial catalogs.
        if DeviceFamily.ISOFT in self._by_family and command_id in self._by_family[DeviceFamily.ISOFT]:
            return self._by_family[DeviceFamily.ISOFT][command_id]

        return None

    def iter_specs(self, family: DeviceFamily) -> list[CommandSpec]:
        """Return all specs for a family."""
        return list(self._by_family.get(family, {}).values())

    def decode(
        self,
        family: DeviceFamily,
        command: str | int,
        raw_hex: str,
        raw_response: dict[str, Any] | None = None,
    ) -> DecodedCommandResult:
        """Decode one command payload."""
        command_id = normalize_command_id(command)
        spec = self.get_spec(family, command_id)

        try:
            payload = ensure_bytes_from_hex(raw_hex)
        except ValueError:
            payload = b""

        if spec is None or spec.decoder is None:
            field = DecodedField(
                key=f"cmd_{command_id:02X}_raw",
                value=raw_hex,
                name=f"Command {command_id:02X} Raw",
                source_command=command_id,
                raw_hex=raw_hex,
            )
            return DecodedCommandResult(
                command_id=command_id,
                fields=[field],
                raw_hex=raw_hex,
                raw=raw_response,
            )

        decoded = spec.decoder(payload)
        fields = [
            DecodedField(
                key=key,
                value=value,
                name=self._FIELD_NAME_OVERRIDES.get(key, key.replace("_", " ").title()),
                source_command=command_id,
                unit=self._unit_for_field(key, spec),
                raw_hex=raw_hex,
            )
            for key, value in decoded.items()
        ]
        return DecodedCommandResult(
            command_id=command_id,
            fields=fields,
            raw_hex=raw_hex,
            raw=raw_response,
        )

    @staticmethod
    def _unit_for_field(field_key: str, spec: CommandSpec) -> str | None:
        """Resolve unit per decoded field key."""
        key = field_key.lower()
        if key.endswith("_pct"):
            return "%"
        if key.endswith("_hours_remaining"):
            return "h"
        if key.endswith("_days_remaining") or key.endswith("_warning_days"):
            return "d"
        if key == "absence_limit_flow_lph":
            return "L/h"
        if key == "absence_limit_volume_l":
            return "L"
        if key == "absence_limit_duration_min":
            return "min"
        if key.endswith("_runtime_min"):
            return "min"
        if key.endswith("_kg"):
            return "kg"
        if key.endswith("_m3"):
            return "m³"
        return spec.unit

    def encode(self, family: DeviceFamily, command: str | int, value: Any) -> str:
        """Encode payload for write command."""
        command_id = normalize_command_id(command)
        spec = self.get_spec(family, command_id)
        if spec is None:
            raise ValueError(f"Unsupported command {command_id:02X} for family {family}")

        if spec.direction == CommandDirection.READ:
            raise ValueError(f"Command {command_id:02X} is read-only")

        if spec.encoder is None:
            if value is None:
                return ""
            if isinstance(value, str):
                text = value.strip()
                if text.startswith("0x"):
                    text = text[2:]
                return text.upper()
            raise ValueError(f"No encoder for command {command_id:02X}")

        return spec.encoder(value)

    def build_write_result(
        self,
        command: str | int,
        transport: TransportMode,
        raw: dict[str, Any] | None,
        error: str | None,
    ) -> CommandResult:
        """Create standardized write result."""
        command_id = normalize_command_id(command)
        return CommandResult(
            command_id=command_id,
            transport=transport,
            status="ok" if error is None else "error",
            raw=raw,
            error=error,
        )
