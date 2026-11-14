"""Core data models for the internal Judo client."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class DeviceFamily(str, Enum):
    """Supported Judo product families."""

    ISOFT = "i_soft"
    SOFTWELL = "softwell"
    IFILL = "i_fill"
    ISAFE = "i_safe"
    IDOS = "i_dos"
    UNKNOWN = "unknown"


class TransportMode(str, Enum):
    """Transport mode for command execution."""

    AUTO = "auto"
    LOCAL = "local"
    CLOUD = "cloud"


class CommandDirection(str, Enum):
    """Direction of command usage."""

    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"


@dataclass(slots=True)
class DecodedField:
    """A decoded telemetry or status field."""

    key: str
    value: Any
    name: str
    source_command: int
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    icon: str | None = None
    raw_hex: str | None = None

    @property
    def is_binary(self) -> bool:
        """Return whether field is represented as a binary sensor."""
        return isinstance(self.value, bool)


@dataclass(slots=True)
class CommandCapability:
    """Supported command capability for a device."""

    command_id: int
    name: str
    direction: CommandDirection
    unit: str | None = None
    payload_length: int | None = None
    default_write_value: Any | None = None


DecoderFunc = Callable[[bytes], dict[str, Any]]
EncoderFunc = Callable[[Any], str]


@dataclass(slots=True)
class CommandSpec:
    """Protocol catalog entry for a single command."""

    command_id: int
    family: DeviceFamily
    name: str
    direction: CommandDirection
    length: int | None
    decoder: DecoderFunc | None = None
    encoder: EncoderFunc | None = None
    unit: str | None = None
    fields: tuple[str, ...] = ()
    default_write_value: Any | None = None


@dataclass(slots=True)
class DeviceDescriptor:
    """Discovered device metadata."""

    device_id: str
    family: DeviceFamily
    device_type: str | None = None
    serial_number: str | None = None
    model: str | None = None
    manufacturer: str = "Judo Wasseraufbereitung GmbH"
    firmware_version: str | None = None
    hardware_version: str | None = None


@dataclass(slots=True)
class DecodedCommandResult:
    """Result of reading a single command."""

    command_id: int
    fields: list[DecodedField]
    raw_hex: str | None
    raw: dict[str, Any] | None = None


@dataclass(slots=True)
class CommandResult:
    """Result of a write command execution."""

    command_id: int
    transport: TransportMode
    status: str
    raw: dict[str, Any] | None = None
    error: str | None = None


@dataclass(slots=True)
class DeviceSnapshot:
    """Decoded snapshot for a device."""

    device: DeviceDescriptor
    fields: list[DecodedField]
    updated_at: str
    transport: TransportMode
    capabilities: list[CommandCapability] = field(default_factory=list)
    raw: dict[str, Any] | None = None
