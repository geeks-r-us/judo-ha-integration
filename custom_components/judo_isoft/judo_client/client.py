"""High-level internal Judo client."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import re
from typing import Any

from .ha_mapping import normalize_field
from .messages import parse_messages
from .models import (
    CommandResult,
    DecodedCommandResult,
    DecodedField,
    DeviceDescriptor,
    DeviceFamily,
    DeviceSnapshot,
    TransportMode,
)
from .protocol.catalog import (
    build_capabilities,
    format_firmware_version,
    infer_family,
    model_name,
    normalize_command_id,
)
from .protocol.decoder import DecoderRegistry
from .protocol.families.isoft import salt_level_pct
from .transport import JudoTransport, JudoTransportError

_LOGGER = logging.getLogger(__name__)


class JudoClient:
    """Internal client with transport and protocol decoding."""

    # API-KOMMANDOZEILEN: i-soft PRO command 0x06 examples are MSB-first.
    _PRO_DEVICE_TYPES_BIG_ENDIAN = {"0x58", "0x4b", "0x4c"}
    # Target hardness cloud writes do not have a reliable public cmd-token spec.
    # Try both plain hex (`30`) and REST-style (`3000`) variants before fallback.
    _CLOUD_MULTI_ENCODING_CMD_IDS = {0x30}
    # Local REST command id -> cloud register index used by `write data`
    # (target hardness verified on an i-soft SAFE+, the others follow the
    # JU-Control register map used by other Judo cloud integrations).
    _CLOUD_WRITE_INDEX = {
        0x30: 60,  # target hardness
        0x35: 65,  # start regeneration
        0x3C: 72,  # close leakage protection valve
        0x3D: 73,  # open leakage protection valve
        0x3E: 74,  # max draw duration (16 bit in the cloud)
        0x3F: 75,  # max flow
        0x40: 76,  # max draw volume
        0x41: 77,  # vacation mode
        0x56: 94,  # salt stock
    }
    _CLOUD_EMPTY_DATA_CMD_IDS = {0x35}
    # Retry decimal command ids only when the primary cloud ack is indeterminate.
    _CLOUD_ALWAYS_DECIMAL_CMD_IDS: set[int] = set()
    _HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
    _HEX_PREFIX_RE = re.compile(r"^0x", re.IGNORECASE)
    _CLOUD_SEGMENT_RE = re.compile(r"^\s*(\d+)\s*:\s*([0-9a-fA-F]+)\s*$")
    _CLOUD_METADATA_SKIP_KEYS = {
        "data",
        "dt",
        "da",
        "sv",
        "hv",
        "sn",
        "serialnumber",
        "serialnumber",
        "serialNumber",
        "ewuid",
        "status",
        "st",
        "er",
        "lu",
    }
    _SALT_METADATA_KEYWORDS = ("salt", "salz", "remaining", "warning", "week")
    _REGENERATION_METADATA_KEYWORDS = ("regen", "regener")
    _HEX_ASSIGNMENT_RE = re.compile(
        r"""(?ix)
        ["']?(?:data|value|raw(?:_response|_text)?)["']?
        \s*[:=]\s*
        ["']?((?:0x)?[0-9a-f]+)["']?
        """
    )

    def __init__(
        self,
        host: str,
        port: int = 80,
        timeout: int = 10,
        username: str | None = None,
        password: str | None = None,
        force_cloud: bool = False,
    ) -> None:
        self._transport = JudoTransport(
            host=host,
            port=port,
            timeout=timeout,
            username=username,
            password=password,
            force_cloud=force_cloud,
        )
        self._decoder = DecoderRegistry()
        self._force_cloud = force_cloud
        self._cached_device: DeviceDescriptor | None = None

    async def close(self) -> None:
        """Close transport resources."""
        await self._transport.close()

    async def discover_devices(self) -> list[DeviceDescriptor]:
        """Discover available devices."""
        if self._cached_device is not None:
            return [self._cached_device]

        # Cloud discovery first if cloud mode is enabled.
        if self._force_cloud:
            descriptor = await self._discover_cloud_device()
            self._cached_device = descriptor
            return [descriptor]

        # Try local discovery, fallback cloud.
        try:
            descriptor = await self._discover_local_device()
            self._cached_device = descriptor
            return [descriptor]
        except Exception:
            descriptor = await self._discover_cloud_device()
            self._cached_device = descriptor
            return [descriptor]

    async def _discover_local_device(self) -> DeviceDescriptor:
        """Discover a local device descriptor."""
        try:
            type_rsp = await self._transport.read_local_command(0xFF)
            serial_rsp = await self._transport.read_local_command(0x06)
            fw_rsp = await self._transport.read_local_command(0x01)

            device_type = self._extract_hex_data(type_rsp)
            serial_hex = self._extract_hex_data(serial_rsp)
            serial = self._decode_device_number(serial_hex, device_type)
            fw = self._extract_hex_data(fw_rsp)
            family = infer_family(device_type)

            return DeviceDescriptor(
                device_id=serial or "local",
                family=family,
                device_type=self._normalize_type_string(device_type),
                serial_number=serial,
                model=model_name(device_type, family),
                firmware_version=format_firmware_version(fw),
            )
        except Exception as err:
            raise RuntimeError(
                "Local discovery via /api/rest failed; device may not support command interface"
            ) from err

    async def _discover_cloud_device(self) -> DeviceDescriptor:
        """Discover a cloud device descriptor."""
        payload = await self._transport.read_cloud_device_data()
        device = self._select_cloud_device(payload)
        if device is None:
            raise RuntimeError("No devices in cloud response")

        dt_raw = self._extract_cloud_device_type(device)
        family = infer_family(dt_raw)
        serial = self._resolve_cloud_serial(device)

        data_blocks = list(self._iter_cloud_device_data(device))
        device_data = (
            next((block for block in data_blocks if block.get("dt") is not None), None)
            or (data_blocks[0] if data_blocks else {})
        )

        descriptor = DeviceDescriptor(
            device_id=serial,
            family=family,
            device_type=self._normalize_type_string(dt_raw),
            serial_number=serial,
            model=model_name(dt_raw, family),
            firmware_version=format_firmware_version(
                device_data.get("sv") or device_data.get("firmware")
            ),
            hardware_version=device_data.get("hv") or device_data.get("hardware"),
        )
        return descriptor

    async def read_command(
        self,
        device_id: str,
        command_id: int | str,
        transport: TransportMode = TransportMode.AUTO,
    ) -> DecodedCommandResult:
        """Read and decode one command."""
        devices = await self.discover_devices()
        device = devices[0]
        command_id = normalize_command_id(command_id)

        if transport == TransportMode.CLOUD or self._force_cloud:
            payload = await self._transport.read_cloud_device_data()
            raw_hex = self._extract_cloud_command_hex(
                payload, command_id, preferred_device_id=device_id or device.device_id
            )
            return self._decoder.decode(device.family, command_id, raw_hex, payload)

        if transport == TransportMode.LOCAL:
            raw = await self._transport.read_local_command(command_id)
            raw_hex = self._extract_hex_data(raw)
            return self._decoder.decode(device.family, command_id, raw_hex, raw)

        # AUTO: local first, cloud fallback.
        try:
            raw = await self._transport.read_local_command(command_id)
            raw_hex = self._extract_hex_data(raw)
            return self._decoder.decode(device.family, command_id, raw_hex, raw)
        except Exception:
            payload = await self._transport.read_cloud_device_data()
            raw_hex = self._extract_cloud_command_hex(
                payload, command_id, preferred_device_id=device_id or device.device_id
            )
            return self._decoder.decode(device.family, command_id, raw_hex, payload)

    async def write_command(
        self,
        device_id: str,
        command_id: int | str,
        value: Any,
        transport: TransportMode = TransportMode.AUTO,
    ) -> CommandResult:
        """Encode and execute one write command."""
        devices = await self.discover_devices()
        device = devices[0]
        command_id = normalize_command_id(command_id)
        payload_hex = self._decoder.encode(device.family, command_id, value)
        resolved_device_id = str(device_id or device.device_id or "").strip()
        cloud_target_sn: str | None = resolved_device_id or None
        cloud_target_serialnumber: str | None = resolved_device_id or None
        cloud_target_ewuid: str | None = None
        if transport != TransportMode.LOCAL or self._force_cloud:
            (
                cloud_target_sn,
                cloud_target_serialnumber,
                cloud_target_ewuid,
            ) = await self._resolve_cloud_write_target(resolved_device_id)

        if transport == TransportMode.CLOUD or self._force_cloud:
            try:
                raw = await self._write_cloud_command_with_fallback(
                    command_id,
                    payload_hex,
                    cloud_target_sn or resolved_device_id,
                    cloud_target_serialnumber,
                    cloud_target_ewuid,
                )
                error = self._extract_write_error(raw)
                return self._decoder.build_write_result(
                    command_id, TransportMode.CLOUD, raw, error
                )
            except Exception as err:
                return self._decoder.build_write_result(
                    command_id, TransportMode.CLOUD, None, str(err)
                )

        if transport == TransportMode.LOCAL:
            try:
                raw = await self._transport.write_local_command(command_id, payload_hex)
                error = self._extract_write_error(raw)
                return self._decoder.build_write_result(
                    command_id, TransportMode.LOCAL, raw, error
                )
            except Exception as err:
                return self._decoder.build_write_result(
                    command_id, TransportMode.LOCAL, None, str(err)
                )

        # AUTO: local first then cloud.
        local_error: str | None = None
        try:
            raw = await self._transport.write_local_command(command_id, payload_hex)
            local_error = self._extract_write_error(raw)
            if local_error is None:
                return self._decoder.build_write_result(
                    command_id, TransportMode.LOCAL, raw, None
                )
        except Exception as err:
            local_error = str(err)

        try:
            raw = await self._write_cloud_command_with_fallback(
                command_id,
                payload_hex,
                cloud_target_sn or resolved_device_id,
                cloud_target_serialnumber,
                cloud_target_ewuid,
            )
            cloud_error = self._extract_write_error(raw)
            if cloud_error and local_error:
                cloud_error = f"{cloud_error} (local fallback failed: {local_error})"
            return self._decoder.build_write_result(
                command_id, TransportMode.CLOUD, raw, cloud_error
            )
        except Exception as err:
            error_text = str(err)
            if local_error:
                error_text = f"{error_text} (local fallback failed: {local_error})"
            return self._decoder.build_write_result(
                command_id, TransportMode.CLOUD, None, error_text
            )

    @staticmethod
    def _extract_write_error(raw: dict[str, Any] | None) -> str | None:
        """Normalize semantic write errors returned in successful HTTP responses."""
        if not isinstance(raw, dict):
            return None

        status_value = raw.get("status")
        if status_value is not None:
            normalized = str(status_value).strip().lower()
            if normalized not in {"ok", "success", "true", "1"}:
                detail = raw.get("error") or raw.get("message") or raw.get("msg")
                return str(detail or status_value)

        state_value = raw.get("st")
        if state_value is not None:
            normalized = str(state_value).strip().lower()
            if normalized not in {"ok", "success"}:
                detail = raw.get("er") or raw.get("error") or raw.get("message")
                return str(detail or state_value)

        return None

    async def _write_cloud_command_with_fallback(
        self,
        command_id: int,
        payload_hex: str,
        sn: str | None,
        serialnumber: str | None,
        ewuid: str | None,
    ) -> dict[str, Any]:
        """Write cloud command, retrying with decimal cmd id when ack is indeterminate."""
        if command_id in self._CLOUD_WRITE_INDEX:
            return await self._write_cloud_register(command_id, payload_hex, serialnumber or sn)

        targets = self._cloud_write_target_variants(
            command_id, sn, serialnumber, ewuid
        )
        if command_id in self._CLOUD_MULTI_ENCODING_CMD_IDS:
            raw = await self._write_cloud_command_with_encodings(
                command_id,
                payload_hex,
                targets,
                cmd_encodings=["hex", "hex00", "rest_inline"],
            )
            if not self._should_retry_cloud_with_decimal(command_id, raw):
                return raw

            try:
                raw_dec = await self._write_cloud_command_variants(
                    command_id,
                    payload_hex,
                    targets,
                    cmd_encoding="dec",
                )
            except Exception:
                return raw

            return self._pick_preferred_cloud_write_result(raw, raw_dec)

        primary_cmd_encoding = self._primary_cloud_cmd_encoding(command_id)
        raw_hex = await self._write_cloud_command_variants(
            command_id,
            payload_hex,
            targets,
            cmd_encoding=primary_cmd_encoding,
        )
        if not self._should_retry_cloud_with_decimal(command_id, raw_hex):
            return raw_hex

        try:
            raw_dec = await self._write_cloud_command_variants(
                command_id,
                payload_hex,
                targets,
                cmd_encoding="dec",
            )
        except Exception:
            return raw_hex

        return self._pick_preferred_cloud_write_result(raw_hex, raw_dec)

    async def _write_cloud_register(
        self, command_id: int, payload_hex: str, preferred_serial: str | None
    ) -> dict[str, Any]:
        """Write a register through the cloud `write data` command."""
        payload = await self._transport.read_cloud_device_data()
        device = self._select_cloud_device(payload, preferred_device_id=preferred_serial)
        if not isinstance(device, dict):
            raise RuntimeError("No cloud device available for write")

        block = next(
            (
                b
                for b in self._iter_cloud_device_data(device)
                if isinstance(b, dict) and b.get("dt") is not None
            ),
            None,
        )
        serial = str(device.get("serialnumber") or preferred_serial or "").strip()
        if block is None or not serial:
            raise RuntimeError("Cloud device identity incomplete for write")

        data_hex = "" if command_id in self._CLOUD_EMPTY_DATA_CMD_IDS else payload_hex
        if command_id == 0x3E and len(data_hex) == 2:
            data_hex = f"{data_hex}00"  # the cloud register is 16 bit wide

        _LOGGER.debug(
            "Cloud register write cmd=%02X index=%s data=%s serial=%s",
            command_id,
            self._CLOUD_WRITE_INDEX[command_id],
            data_hex,
            serial,
        )
        return await self._transport.write_cloud_register(
            serial_number=serial,
            dt=str(block.get("dt")),
            da=str(block.get("da", "")),
            index=self._CLOUD_WRITE_INDEX[command_id],
            data_hex=data_hex,
        )

    async def _write_cloud_command_with_encodings(
        self,
        command_id: int,
        payload_hex: str,
        targets: list[tuple[str | None, str | None, str | None]],
        *,
        cmd_encodings: list[str],
    ) -> dict[str, Any]:
        """Try one cloud write across multiple cmd encodings and combine responses."""
        combined: dict[str, Any] | None = None
        last_error: Exception | None = None

        for cmd_encoding in cmd_encodings:
            try:
                raw = await self._write_cloud_command_variants(
                    command_id,
                    payload_hex,
                    targets,
                    cmd_encoding=cmd_encoding,
                )
            except Exception as err:
                last_error = err
                continue

            combined = self._pick_preferred_cloud_write_result(combined, raw)

        if combined is not None:
            return combined
        if last_error is not None:
            raise last_error
        return {}

    async def _write_cloud_command_variants(
        self,
        command_id: int,
        payload_hex: str,
        targets: list[tuple[str | None, str | None, str | None]],
        *,
        cmd_encoding: str,
    ) -> dict[str, Any]:
        """Try one cloud write across target variants and combine the responses."""
        combined: dict[str, Any] | None = None
        last_error: Exception | None = None

        for target_sn, target_serialnumber, target_ewuid in targets:
            _LOGGER.debug(
                "Cloud write attempt cmd=%02X encoding=%s data=%s sn=%s serialnumber=%s ewuid=%s",
                command_id,
                cmd_encoding,
                payload_hex,
                target_sn,
                target_serialnumber,
                target_ewuid,
            )
            try:
                raw = await self._transport.write_cloud_command(
                    command_id,
                    payload_hex,
                    target_sn,
                    target_serialnumber,
                    target_ewuid,
                    cmd_encoding=cmd_encoding,
                )
            except Exception as err:
                _LOGGER.debug(
                    "Cloud write failed cmd=%02X encoding=%s data=%s sn=%s serialnumber=%s ewuid=%s error=%s",
                    command_id,
                    cmd_encoding,
                    payload_hex,
                    target_sn,
                    target_serialnumber,
                    target_ewuid,
                    err,
                )
                last_error = err
                continue

            _LOGGER.debug(
                "Cloud write response cmd=%02X encoding=%s data=%s sn=%s serialnumber=%s ewuid=%s raw=%s",
                command_id,
                cmd_encoding,
                payload_hex,
                target_sn,
                target_serialnumber,
                target_ewuid,
                raw,
            )
            combined = self._pick_preferred_cloud_write_result(combined, raw)

        if combined is not None:
            return combined
        if last_error is not None:
            raise last_error
        return {}

    def _cloud_write_target_variants(
        self,
        command_id: int,
        sn: str | None,
        serialnumber: str | None,
        ewuid: str | None,
    ) -> list[tuple[str | None, str | None, str | None]]:
        """Build cloud target variants for commands with backend-specific routing."""
        normalized_sn = str(sn or "").strip() or None
        normalized_serialnumber = str(serialnumber or "").strip() or None
        normalized_ewuid = str(ewuid or "").strip() or None

        variants: list[tuple[str | None, str | None, str | None]] = []
        seen: set[tuple[str | None, str | None, str | None]] = set()

        def add_variant(
            target_sn: str | None,
            target_serialnumber: str | None,
            target_ewuid: str | None,
        ) -> None:
            normalized_target = (
                str(target_sn or "").strip() or None,
                str(target_serialnumber or "").strip() or None,
                str(target_ewuid or "").strip() or None,
            )
            if normalized_target in seen:
                return
            seen.add(normalized_target)
            variants.append(normalized_target)

        add_variant(normalized_sn, normalized_serialnumber, normalized_ewuid)

        if command_id == 0x30:
            if normalized_ewuid is not None:
                add_variant(normalized_sn, normalized_serialnumber, None)
            if normalized_sn is not None:
                add_variant(normalized_sn, None, normalized_ewuid)
                if normalized_ewuid is not None:
                    add_variant(normalized_sn, None, None)
            if normalized_serialnumber is not None:
                add_variant(None, normalized_serialnumber, normalized_ewuid)
                if normalized_ewuid is not None:
                    add_variant(None, normalized_serialnumber, None)

        return variants

    def _primary_cloud_cmd_encoding(self, command_id: int) -> str:
        """Return primary cloud cmd encoding for one command id."""
        return "hex"

    def _should_retry_cloud_with_decimal(
        self, command_id: int, raw_hex: dict[str, Any] | None
    ) -> bool:
        """Return whether cloud write should retry with decimal cmd encoding."""
        if command_id in self._CLOUD_ALWAYS_DECIMAL_CMD_IDS:
            return True
        return (
            self._extract_write_error(raw_hex) is None
            and self._is_indeterminate_cloud_write_ack(raw_hex)
        )

    def _pick_preferred_cloud_write_result(
        self,
        raw_hex: dict[str, Any] | None,
        raw_dec: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Select the better cloud write response across hex/decimal cmd attempts."""
        if raw_hex is None and raw_dec is None:
            return {}
        if raw_hex is None:
            return raw_dec or {}
        if raw_dec is None:
            return raw_hex

        hex_error = self._extract_write_error(raw_hex)
        dec_error = self._extract_write_error(raw_dec)

        # Keep successful hex write when decimal fallback fails semantically.
        if hex_error is None and dec_error is not None:
            return raw_hex

        # Prefer any semantic success over an explicit error.
        if hex_error is not None and dec_error is None:
            return raw_dec

        # When both succeed, prefer response with explicit semantic status/value.
        if dec_error is None and not self._is_indeterminate_cloud_write_ack(raw_dec):
            return raw_dec
        if hex_error is None and not self._is_indeterminate_cloud_write_ack(raw_hex):
            return raw_hex

        # Otherwise return decimal retry result for compatibility.
        return raw_dec

    @staticmethod
    def _is_indeterminate_cloud_write_ack(raw: dict[str, Any] | None) -> bool:
        """Return whether cloud write response lacks a semantic success/error signal."""
        if not isinstance(raw, dict):
            return True
        if any(key in raw for key in ("status", "st", "error", "message", "msg", "er")):
            return False
        if "value" in raw and raw.get("value") is not None:
            return False
        return True

    async def _resolve_cloud_write_target(
        self, preferred_device_id: str
    ) -> tuple[str | None, str | None, str | None]:
        """Resolve cloud write target identifiers (`sn`, `serialnumber`, `ewuid`)."""
        normalized_preferred = str(preferred_device_id).strip()
        try:
            payload = await self._transport.read_cloud_device_data()
        except Exception:
            fallback = normalized_preferred or None
            return fallback, fallback, None

        selected = self._select_cloud_device(
            payload, preferred_device_id=preferred_device_id
        )
        if not isinstance(selected, dict):
            fallback = normalized_preferred or None
            return fallback, fallback, None

        resolved_sn, resolved_serialnumber = self._resolve_cloud_target_ids(selected)
        if normalized_preferred:
            candidates = self._cloud_serial_candidates(selected)
            if normalized_preferred in candidates:
                if not resolved_sn:
                    resolved_sn = normalized_preferred
                if not resolved_serialnumber:
                    resolved_serialnumber = normalized_preferred

        if not resolved_sn and resolved_serialnumber:
            resolved_sn = resolved_serialnumber
        if not resolved_serialnumber and resolved_sn:
            resolved_serialnumber = resolved_sn
        if not resolved_sn and normalized_preferred:
            resolved_sn = normalized_preferred
        if not resolved_serialnumber and normalized_preferred:
            resolved_serialnumber = normalized_preferred

        raw_ewuid = selected.get("ewuid")
        if raw_ewuid is None:
            for block in self._iter_cloud_device_data(selected):
                if not isinstance(block, dict):
                    continue
                raw_ewuid = block.get("ewuid")
                if raw_ewuid is not None:
                    break
        ewuid = str(raw_ewuid).strip() if raw_ewuid is not None else None
        if ewuid == "":
            ewuid = None

        return resolved_sn, resolved_serialnumber, ewuid

    @classmethod
    def _resolve_cloud_target_ids(
        cls, device: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """Resolve cloud write target ids while preserving distinct key values."""
        resolved_sn: str | None = None
        resolved_serialnumber: str | None = None

        for source in [*cls._iter_cloud_device_data(device), device]:
            if not isinstance(source, dict):
                continue
            if resolved_sn is None:
                raw_sn = source.get("sn")
                if raw_sn is not None:
                    text = str(raw_sn).strip()
                    if text:
                        resolved_sn = text
            if resolved_serialnumber is None:
                raw_serial = source.get("serialnumber") or source.get("serialNumber")
                if raw_serial is not None:
                    text = str(raw_serial).strip()
                    if text:
                        resolved_serialnumber = text
            if resolved_sn is not None and resolved_serialnumber is not None:
                break

        if resolved_sn is None:
            resolved_sn = cls._resolve_cloud_node_id(device)

        return resolved_sn, resolved_serialnumber

    @classmethod
    def _resolve_cloud_node_id(cls, device: dict[str, Any]) -> str | None:
        """Resolve numeric cloud node id from observed command 0x03 payload."""
        command_map = cls._extract_cloud_command_map_for_device(device)
        raw_hex = command_map.get("03")
        if not isinstance(raw_hex, str):
            return None

        normalized_hex = raw_hex.strip()
        if len(normalized_hex) < 8 or not cls._HEX_RE.fullmatch(normalized_hex):
            return None

        try:
            raw_bytes = bytes.fromhex(normalized_hex[:8])
        except ValueError:
            return None

        return str(int.from_bytes(raw_bytes, byteorder="little"))

    async def read_snapshot(self, device_id: str) -> DeviceSnapshot:
        """Read and decode a complete device snapshot."""
        devices = await self.discover_devices()
        device = devices[0]
        specs = self._decoder.iter_specs(device.family)
        capabilities = build_capabilities(specs)

        fields: list[DecodedField] = []
        raw_bundle: dict[str, Any] = {}
        transport_mode = TransportMode.LOCAL

        if self._force_cloud:
            transport_mode = TransportMode.CLOUD
            payload = await self._transport.read_cloud_device_data()
            raw_bundle["cloud"] = payload
            fields.extend(
                self._decode_cloud_payload(
                    device.family, payload, preferred_device_id=device.device_id
                )
            )
        else:
            # Local-first snapshot from all readable specs.
            try:
                for spec in specs:
                    if spec.direction.value not in ("read", "read_write"):
                        continue
                    try:
                        rsp = await self._transport.read_local_command(spec.command_id)
                    except JudoTransportError:
                        continue
                    raw_hex = self._extract_hex_data(rsp)
                    decoded = self._decoder.decode(
                        device.family, spec.command_id, raw_hex, rsp
                    )
                    fields.extend(decoded.fields)
                raw_bundle["local"] = True
                transport_mode = TransportMode.LOCAL
            except Exception:
                payload = await self._transport.read_cloud_device_data()
                raw_bundle["cloud"] = payload
                fields.extend(
                    self._decode_cloud_payload(
                        device.family, payload, preferred_device_id=device.device_id
                    )
                )
                transport_mode = TransportMode.CLOUD

            if not fields:
                payload = await self._transport.read_cloud_device_data()
                raw_bundle["cloud"] = payload
                fields.extend(
                    self._decode_cloud_payload(
                        device.family, payload, preferred_device_id=device.device_id
                    )
                )
                transport_mode = TransportMode.CLOUD

        if transport_mode == TransportMode.LOCAL and fields:
            # A successful local read means the device answered.
            fields.append(
                DecodedField(
                    key="device_online", value=True, name="Online", source_command=0x00
                )
            )

        if transport_mode == TransportMode.CLOUD and device.serial_number:
            # Prefer cloud app/device serial (sn) as canonical serial field.
            fields.append(
                DecodedField(
                    key="serial_number",
                    value=device.serial_number,
                    name="Serial Number",
                    source_command=0x06,
                )
            )

        if transport_mode == TransportMode.CLOUD:
            messages = await self._read_messages(device.serial_number)
            if messages:
                raw_bundle["messages"] = messages
                newest = messages[0]
                fields.append(
                    DecodedField(
                        key="last_message",
                        value=newest["text"],
                        name="Last Message",
                        source_command=0x00,
                    )
                )
                fields.append(
                    DecodedField(
                        key="last_message_time",
                        value=newest["timestamp"],
                        name="Last Message Time",
                        source_command=0x00,
                        device_class="timestamp",
                    )
                )
                fields.append(
                    DecodedField(
                        key="unconfirmed_messages",
                        value=sum(1 for m in messages if not m["confirmed"]),
                        name="Unconfirmed Messages",
                        source_command=0x00,
                    )
                )

        # Normalize and deduplicate by key (last value wins).
        dedup: dict[str, DecodedField] = {}
        for field in fields:
            dedup[field.key] = normalize_field(field)

        return DeviceSnapshot(
            device=device,
            fields=list(dedup.values()),
            updated_at=datetime.now(timezone.utc).isoformat(),
            transport=transport_mode,
            capabilities=capabilities,
            raw=raw_bundle,
        )

    async def _read_messages(self, serial: str | None) -> list[dict[str, Any]]:
        """Read the cloud message log; failures must not break the snapshot."""
        try:
            payload = await self._transport.read_cloud_messages()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Reading cloud messages failed: %s", err)
            return []
        return parse_messages(payload, serial)

    def _decode_cloud_payload(
        self,
        family,
        payload: dict[str, Any],
        preferred_device_id: str | None = None,
    ) -> list[DecodedField]:
        def _decode_fields(
            decode_family: DeviceFamily, command_map: dict[str, str]
        ) -> list[DecodedField]:
            decoded_fields: list[DecodedField] = []
            for raw_cmd, raw_hex in command_map.items():
                try:
                    command_id = normalize_command_id(raw_cmd)
                except Exception:
                    continue

                spec = self._decoder.get_spec(decode_family, command_id)
                # Keep snapshot entities readable: skip commands without decoders.
                if spec is None or spec.decoder is None:
                    continue

                try:
                    decoded = self._decoder.decode(
                        decode_family, command_id, raw_hex, payload
                    )
                except Exception:
                    # Ignore unknown/non-command keys from cloud payload variants.
                    continue
                decoded_fields.extend(decoded.fields)
            return decoded_fields

        selected_device = self._select_cloud_device(
            payload, preferred_device_id=preferred_device_id
        )
        if selected_device is None:
            return []

        selected_family = infer_family(self._extract_cloud_device_type(selected_device))
        if selected_family == DeviceFamily.UNKNOWN:
            selected_family = family

        active_device = selected_device
        active_family = selected_family
        selected_map = self._extract_cloud_command_map_for_device(selected_device)
        fields = _decode_fields(selected_family, selected_map)

        # If a preferred device id points to a non-softener/incomplete block, recover by
        # selecting the best-scored device from payload.
        if preferred_device_id:
            softener_signal_keys = {
                "salt_level_pct",
                "salt_weight_g",
                "target_hardness",
                "soft_water_l",
            }
            has_softener_signals = any(
                field.key in softener_signal_keys and field.value is not None
                for field in fields
            )
            if not has_softener_signals:
                fallback_device = self._select_cloud_device(
                    payload,
                    preferred_device_id=None,
                    allow_cached_preference=False,
                )
                if fallback_device is not None and fallback_device is not selected_device:
                    fallback_family = infer_family(
                        self._extract_cloud_device_type(fallback_device)
                    )
                    if fallback_family == DeviceFamily.UNKNOWN:
                        fallback_family = selected_family
                    fallback_map = self._extract_cloud_command_map_for_device(
                        fallback_device
                    )
                    fallback_fields = _decode_fields(fallback_family, fallback_map)
                    fallback_has_signals = any(
                        field.key in softener_signal_keys and field.value is not None
                        for field in fallback_fields
                    )
                    if fallback_has_signals or len(fallback_fields) > len(fields):
                        active_device = fallback_device
                        active_family = fallback_family
                        fields = fallback_fields

        if active_family == DeviceFamily.ISOFT:
            has_salt = any(
                field.key in {"salt_weight_g", "salt_level_pct"}
                and isinstance(field.value, (int, float))
                for field in fields
            )
            if not has_salt:
                fields.extend(self._derive_salt_from_segmented_blob(active_device))

            fields.extend(self._derive_regeneration_count_from_segmented_blob(active_device))
            fields.extend(self._derive_water_scene(active_device))
            fields.extend(self._derive_leakage_settings_from_segmented_blob(active_device))

            self._log_cloud_salt_metadata_candidates(active_device, fields)
            self._log_cloud_regeneration_metadata_candidates(active_device, fields)

            has_target_hardness = any(
                field.key == "target_hardness"
                and isinstance(field.value, (int, float))
                for field in fields
            )
            if not has_target_hardness:
                fields.extend(
                    self._derive_target_hardness_from_segmented_blob(active_device)
                )
                has_target_hardness = any(
                    field.key == "target_hardness"
                    and isinstance(field.value, (int, float))
                    for field in fields
                )
            if not has_target_hardness:
                fields.extend(
                    self._derive_target_hardness_from_cloud_metadata(active_device)
                )

        cloud_status = str(active_device.get("status") or "").strip().lower()
        if cloud_status:
            fields.append(
                DecodedField(
                    key="device_online",
                    value=cloud_status == "online",
                    name="Online",
                    source_command=0x00,
                )
            )

        module_version = format_firmware_version(
            str(active_device.get("sv") or "").strip() or None
        )
        if module_version:
            fields.append(
                DecodedField(
                    key="connectivity_module_version",
                    value=module_version,
                    name="Connectivity Module Version",
                    source_command=0x01,
                )
            )

        installation_date = self._extract_cloud_installation_date(active_device)
        if installation_date:
            # Cloud payload exposes stable installation metadata; prefer it over
            # command 0x0E variants that can carry volatile counters/time values.
            fields.append(
                DecodedField(
                    key="commissioning_date",
                    value=installation_date,
                    name="Commissioning Date",
                    source_command=0x0E,
                )
            )

        return fields

    @classmethod
    def _extract_cloud_metadata_candidates(
        cls, device: dict[str, Any], keywords: tuple[str, ...]
    ) -> dict[str, Any]:
        """Collect plain cloud metadata entries matching one of the supplied keywords."""
        candidates: dict[str, Any] = {}

        def _collect(source: Any) -> None:
            if not isinstance(source, dict):
                return
            for raw_key, value in source.items():
                key = str(raw_key).strip()
                if (
                    not key
                    or key.isdigit()
                    or key in cls._CLOUD_METADATA_SKIP_KEYS
                    or str(key).lower().startswith("0x")
                ):
                    continue
                lower_key = key.lower()
                if not any(keyword in lower_key for keyword in keywords):
                    continue
                if isinstance(value, bool):
                    candidates.setdefault(key, value)
                elif isinstance(value, (int, float)):
                    candidates.setdefault(key, value)
                elif isinstance(value, str):
                    text = value.strip()
                    if text:
                        candidates.setdefault(key, text)

        _collect(device)
        for source in cls._iter_cloud_device_data(device):
            _collect(source)

        return candidates

    @classmethod
    def _log_cloud_salt_metadata_candidates(
        cls, device: dict[str, Any], fields: list[DecodedField]
    ) -> None:
        """Log salt-related cloud metadata candidates next to decoded salt fields."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return

        salt_days_field = next(
            (field for field in fields if field.key == "salt_days_remaining"),
            None,
        )
        salt_weight_field = next(
            (field for field in fields if field.key == "salt_weight_g"),
            None,
        )
        if salt_days_field is None and salt_weight_field is None:
            return

        candidates = cls._extract_cloud_metadata_candidates(
            device, cls._SALT_METADATA_KEYWORDS
        )
        _LOGGER.debug(
            "Cloud salt decode serial=%s salt_weight_g=%s "
            "salt_days_remaining=%s source_command=%s raw_hex=%s metadata=%s",
            device.get("serialnumber") or device.get("sn"),
            salt_weight_field.value if salt_weight_field is not None else None,
            salt_days_field.value if salt_days_field is not None else None,
            salt_days_field.source_command if salt_days_field is not None else None,
            salt_days_field.raw_hex if salt_days_field is not None else None,
            candidates or {},
        )

    @classmethod
    def _log_cloud_regeneration_metadata_candidates(
        cls, device: dict[str, Any], fields: list[DecodedField]
    ) -> None:
        """Log regeneration-related cloud metadata candidates next to decoded status."""
        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return

        regeneration_field = next(
            (field for field in fields if field.key == "regeneration_active"),
            None,
        )
        candidates = cls._extract_cloud_metadata_candidates(
            device, cls._REGENERATION_METADATA_KEYWORDS
        )
        _LOGGER.debug(
            "Cloud regeneration decode serial=%s regeneration_active=%s "
            "source_command=%s raw_hex=%s metadata=%s",
            device.get("serialnumber") or device.get("sn"),
            regeneration_field.value if regeneration_field is not None else None,
            regeneration_field.source_command if regeneration_field is not None else None,
            regeneration_field.raw_hex if regeneration_field is not None else None,
            candidates or {},
        )

    @classmethod
    def _derive_target_hardness_from_cloud_metadata(
        cls, device: dict[str, Any]
    ) -> list[DecodedField]:
        """Derive target hardness from cloud metadata when cmd 0x51 is unavailable."""
        hardness_keys = (
            "hardness_shower",
            "hardness_watering",
            "hardness_heater",
            "hardness_washing",
        )
        sources = [device, *cls._iter_cloud_device_data(device)]

        def _as_float(value: Any) -> float | None:
            if isinstance(value, bool):
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if value is None:
                return None
            try:
                text = str(value).strip().replace(",", ".")
                if not text:
                    return None
                return float(text)
            except ValueError:
                return None

        values: dict[str, float | None] = {key: None for key in hardness_keys}
        waterscene: str | None = None

        for source in sources:
            if not isinstance(source, dict):
                continue
            if waterscene is None:
                raw_scene = source.get("waterscene")
                if raw_scene is not None:
                    scene_text = str(raw_scene).strip().lower()
                    if scene_text:
                        waterscene = scene_text
            for key in hardness_keys:
                if values[key] is not None:
                    continue
                parsed = _as_float(source.get(key))
                if parsed is not None:
                    values[key] = parsed

        scene_to_key = {
            "normal": "hardness_shower",
            "shower": "hardness_shower",
            "garden": "hardness_watering",
            "watering": "hardness_watering",
            "heater": "hardness_heater",
            "washing": "hardness_washing",
        }

        selected: float | None = None
        if waterscene in scene_to_key:
            selected = values.get(scene_to_key[waterscene])

        if selected is None:
            for key in (
                "hardness_shower",
                "hardness_watering",
                "hardness_heater",
                "hardness_washing",
            ):
                candidate = values.get(key)
                if candidate is not None:
                    selected = candidate
                    break

        if selected is None:
            return []

        return [
            DecodedField(
                key="target_hardness",
                value=selected,
                name="Target Hardness",
                source_command=0x51,
                unit="dH",
            )
        ]

    @classmethod
    def _derive_target_hardness_from_segmented_blob(
        cls, device: dict[str, Any]
    ) -> list[DecodedField]:
        """Derive target hardness from segmented cloud status blob (790..799)."""
        blob_hex = cls._extract_segmented_blob_hex_for_device(device)
        if not blob_hex:
            return []

        try:
            payload = bytes.fromhex(blob_hex)
        except ValueError:
            return []

        # Observed i-soft segmented payload layout:
        # target hardness in dH at byte offset 8.
        if len(payload) < 9:
            return []

        target_hardness = int(payload[8])
        if not (0 < target_hardness <= 80):
            return []

        return [
            DecodedField(
                key="target_hardness",
                value=float(target_hardness),
                name="Target Hardness",
                source_command=0x51,
                unit="dH",
                raw_hex=f"{target_hardness:02X}",
            )
        ]

    @classmethod
    def _normalize_type_string(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if text.startswith("0x"):
            return text.lower()
        if cls._HEX_RE.fullmatch(text) and len(text) <= 2:
            hex_candidate = f"0x{text.zfill(2)}".lower()
            if infer_family(hex_candidate) != DeviceFamily.UNKNOWN:
                return hex_candidate
        try:
            intval = int(text, 10)
            dec_candidate = f"0x{intval:02X}".lower()
            if infer_family(dec_candidate) != DeviceFamily.UNKNOWN:
                return dec_candidate
            return dec_candidate
        except ValueError:
            return text.lower()

    @classmethod
    def _extract_hex_data(cls, response: dict[str, Any]) -> str:
        if not isinstance(response, dict):
            return ""
        for key in ("data", "value", "raw_response", "raw_text"):
            value = response.get(key)
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    continue

                # Most transports return direct hex payload.
                normalized = cls._normalize_hex_payload(text)
                if normalized:
                    return normalized

                # Some /api/rest variants return assignment-style text (e.g. data=f6541100).
                match = cls._HEX_ASSIGNMENT_RE.search(text)
                if match:
                    normalized = cls._normalize_hex_payload(match.group(1))
                    if normalized:
                        return normalized
        return ""

    def _extract_cloud_command_map(
        self, payload: dict[str, Any], preferred_device_id: str | None = None
    ) -> dict[str, str]:
        command_map: dict[str, str] = {}
        device = self._select_cloud_device(payload, preferred_device_id=preferred_device_id)
        if device is None:
            return command_map
        return self._extract_cloud_command_map_for_device(device)

    @staticmethod
    def _extract_cloud_devices(payload: dict[str, Any] | Any) -> list[dict[str, Any]]:
        """Extract cloud device list from supported response shapes."""
        if not isinstance(payload, dict):
            return []

        candidates: list[dict[str, Any]] = []

        for key in ("data", "devices", "value"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates = [item for item in value if isinstance(item, dict)]
                if candidates:
                    return candidates
            elif isinstance(value, dict):
                nested_devices = value.get("devices")
                if isinstance(nested_devices, list):
                    candidates = [
                        item for item in nested_devices if isinstance(item, dict)
                    ]
                    if candidates:
                        return candidates
                return [value]

        return []

    @staticmethod
    def _extract_cloud_device_data(device: dict[str, Any]) -> dict[str, Any]:
        """Extract first cloud device data block from supported response shapes."""
        raw = device.get("data")
        if isinstance(raw, list):
            first = raw[0] if raw else {}
            return first if isinstance(first, dict) else {}
        if isinstance(raw, dict):
            return raw
        return {}

    @staticmethod
    def _iter_cloud_device_data(device: dict[str, Any]) -> list[dict[str, Any]]:
        """Iterate all cloud device data blocks from supported response shapes."""
        raw = device.get("data")
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            return [raw]
        return []

    @classmethod
    def _extract_cloud_command_map_for_device(cls, device: dict[str, Any]) -> dict[str, str]:
        """Extract normalized command map for one cloud device."""
        command_map: dict[str, str] = {}
        visited: set[int] = set()

        def _walk(node: Any, depth: int = 0) -> None:
            if depth > 12:
                return
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)

            if isinstance(node, dict):
                for cmd, item in node.items():
                    try:
                        normalized_cmd = normalize_command_id(str(cmd).strip())
                    except Exception:
                        normalized_cmd = None

                    if normalized_cmd is not None and 0 <= normalized_cmd <= 0xFF:
                        hex_payload = cls._extract_hex_payload(item)
                        if hex_payload:
                            key = f"{normalized_cmd:02X}"
                            existing = command_map.get(key)
                            # Prefer richer payloads when duplicate command ids appear
                            # in multiple cloud response blocks.
                            if existing is None or len(hex_payload) > len(existing):
                                command_map[key] = hex_payload

                    if isinstance(item, (dict, list)):
                        _walk(item, depth + 1)
                return

            if isinstance(node, list):
                for item in node:
                    if isinstance(item, (dict, list)):
                        _walk(item, depth + 1)

        for device_data in cls._iter_cloud_device_data(device):
            _walk(device_data)
        _walk(device)
        return command_map

    @classmethod
    def _parse_segmented_cloud_entry(cls, value: Any) -> tuple[int, str] | None:
        """Parse cloud segmented payload entries (e.g. '0:ABCD...')."""
        if isinstance(value, str):
            match = cls._CLOUD_SEGMENT_RE.match(value.strip())
            if not match:
                return None
            index = int(match.group(1), 10)
            payload = match.group(2).upper()
            if len(payload) % 2:
                return None
            if not cls._HEX_RE.fullmatch(payload):
                return None
            return index, payload

        if isinstance(value, dict):
            for key in ("data", "value", "raw", "raw_hex", "rawHex", "hex", "v"):
                parsed = cls._parse_segmented_cloud_entry(value.get(key))
                if parsed:
                    return parsed
            for nested in value.values():
                if isinstance(nested, (dict, list, str)):
                    parsed = cls._parse_segmented_cloud_entry(nested)
                    if parsed:
                        return parsed
            return None

        if isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list, str)):
                    parsed = cls._parse_segmented_cloud_entry(item)
                    if parsed:
                        return parsed
            return None

        return None

    @classmethod
    def _extract_segmented_blob_hex_for_device(cls, device: dict[str, Any]) -> str | None:
        """Extract and join segmented blob commands (790..799) from one device."""
        segments: dict[int, str] = {}
        visited: set[int] = set()

        def _walk(node: Any, depth: int = 0) -> None:
            if depth > 12:
                return
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)

            if isinstance(node, dict):
                for raw_cmd, item in node.items():
                    cmd_text = str(raw_cmd).strip()
                    if cmd_text.isdigit():
                        cmd_num = int(cmd_text, 10)
                        if 790 <= cmd_num <= 799:
                            parsed = cls._parse_segmented_cloud_entry(item)
                            if parsed:
                                seg_idx, seg_hex = parsed
                                current = segments.get(seg_idx)
                                if current is None or len(seg_hex) > len(current):
                                    segments[seg_idx] = seg_hex
                    if isinstance(item, (dict, list)):
                        _walk(item, depth + 1)
                return

            if isinstance(node, list):
                for item in node:
                    if isinstance(item, (dict, list)):
                        _walk(item, depth + 1)

        for block in cls._iter_cloud_device_data(device):
            _walk(block)
        _walk(device)

        if not segments or 0 not in segments:
            return None

        max_index = max(segments.keys())
        ordered: list[str] = []
        for index in range(0, max_index + 1):
            part = segments.get(index)
            if not part:
                return None
            ordered.append(part)

        joined = "".join(ordered).upper()
        if len(joined) % 2:
            return None
        if not cls._HEX_RE.fullmatch(joined):
            return None
        return joined

    @classmethod
    def _derive_water_scene(cls, device: dict[str, Any]) -> list[DecodedField]:
        """Expose the active water scene and per-scene hardness from cloud metadata."""
        scene_keys = {
            "waterscene_normal": ("water_scene_normal_hardness", "Water Scene Normal Hardness"),
            "hardness_shower": ("water_scene_shower_hardness", "Water Scene Shower Hardness"),
            "hardness_watering": ("water_scene_garden_hardness", "Water Scene Garden Hardness"),
            "hardness_heater": ("water_scene_heater_hardness", "Water Scene Heating Fill Hardness"),
            "hardness_washing": ("water_scene_washing_hardness", "Water Scene Washing Hardness"),
        }
        fields: list[DecodedField] = []
        seen: set[str] = set()
        for source in [device, *cls._iter_cloud_device_data(device)]:
            if not isinstance(source, dict):
                continue
            scene = str(source.get("waterscene") or "").strip()
            if scene and "water_scene" not in seen:
                seen.add("water_scene")
                fields.append(
                    DecodedField(
                        key="water_scene",
                        value=scene.lower(),
                        name="Water Scene",
                        source_command=0x36,
                    )
                )
            for meta_key, (key, name) in scene_keys.items():
                value = source.get(meta_key)
                if key in seen or isinstance(value, bool) or value in (None, ""):
                    continue
                try:
                    number = float(str(value).replace(",", "."))
                except ValueError:
                    continue
                seen.add(key)
                fields.append(
                    DecodedField(
                        key=key, value=number, name=name, source_command=0x36, unit="dH"
                    )
                )
        return fields

    @classmethod
    def _derive_leakage_settings_from_segmented_blob(
        cls, device: dict[str, Any]
    ) -> list[DecodedField]:
        """Derive leakage protection / vacation / sleep settings from blob 790..792.

        Offsets verified against the Judo app on an i-soft SAFE+ (flow 4000 l/h,
        volume 900 l, duration 120 min): u16 at 76/78/80 (same order as command 0x50).
        Byte 82 follows the 0x41 vacation flag layout (bit1=U1, bit2=U2, bit3=U3; raw
        0/3/5/9 = U0/U1/U2/U3, confirmed on U1 and U2) and byte 83 is the sleep duration
        in hours. Judo's manual: after 72 h without consumption the protection switches to
        the selected vacation mode (U1: 6 min / 50 L / 500 L/h, U2: 12 min / 100 L /
        1000 L/h, U3: valve closed).
        """
        blob_hex = cls._extract_segmented_blob_hex_for_device(device)
        if not blob_hex:
            return []
        payload = bytes.fromhex(blob_hex)
        if len(payload) < 84:
            return []

        def _u16(offset: int) -> int:
            return int.from_bytes(payload[offset : offset + 2], "little")

        flags = payload[82]
        vacation = next(
            (name for bit, name in ((0x02, "U1"), (0x04, "U2"), (0x08, "U3")) if flags & bit),
            "U0",
        )
        return [
            DecodedField(
                key="leakage_max_flow_lph", value=_u16(76), unit="L/h",
                name="Leakage Max Flow", source_command=0x40,
            ),
            DecodedField(
                key="leakage_max_volume_l", value=_u16(78), unit="L",
                name="Leakage Max Draw Volume", source_command=0x3F,
            ),
            DecodedField(
                key="leakage_max_duration_min", value=_u16(80), unit="min",
                name="Leakage Max Draw Duration", source_command=0x3E,
            ),
            DecodedField(
                key="vacation_mode_type", value=vacation,
                name="Vacation Mode Type", source_command=0x41,
            ),
            # Offsets 7 and 64 both flip 00 -> 01 while the vacation mode is active
            # (observed twice with U1, valve open). Other projects call byte 64 "valve
            # closed", so it may also be set when the valve is closed (e.g. U3).
            DecodedField(
                key="vacation_mode_active", value=payload[64] == 1,
                name="Vacation Mode Active", source_command=0x41,
            ),
            DecodedField(
                key="sleep_mode_duration_h", value=payload[83], unit="h",
                name="Sleep Mode Duration", source_command=0x53,
            ),
        ]

    @classmethod
    def _derive_regeneration_count_from_segmented_blob(
        cls, device: dict[str, Any]
    ) -> list[DecodedField]:
        """Derive the regeneration counter (u16 at offset 62 of blob 790..792)."""
        blob_hex = cls._extract_segmented_blob_hex_for_device(device)
        if not blob_hex:
            return []
        payload = bytes.fromhex(blob_hex)
        if len(payload) < 64:
            return []
        return [
            DecodedField(
                key="regeneration_count",
                value=int.from_bytes(payload[62:64], byteorder="little", signed=False),
                name="Regeneration Count",
                source_command=0x316,
            )
        ]

    @classmethod
    def _derive_salt_from_segmented_blob(
        cls, device: dict[str, Any]
    ) -> list[DecodedField]:
        """Derive salt fields from segmented cloud status blob when cmd 0x56 is absent."""
        blob_hex = cls._extract_segmented_blob_hex_for_device(device)
        if not blob_hex:
            return []

        try:
            payload = bytes.fromhex(blob_hex)
        except ValueError:
            return []

        # Observed i-soft cloud segmented payload layout (commands 790..792):
        # salt days at offset 6, salt grams at offset 22.
        if len(payload) < 24:
            return []
        salt_days = int.from_bytes(payload[6:8], byteorder="little", signed=False)
        salt_grams = int.from_bytes(payload[22:24], byteorder="little", signed=False)

        if not (0 <= salt_days <= 365):
            return []
        if not (0 <= salt_grams <= 30000):
            return []
        if salt_days == 0 and salt_grams == 0:
            return []

        raw_hex = (
            int(salt_grams).to_bytes(2, byteorder="little", signed=False).hex().upper()
            + int(salt_days).to_bytes(2, byteorder="little", signed=False).hex().upper()
        )
        salt_pct = salt_level_pct(salt_grams)

        return [
            DecodedField(
                key="salt_weight_g",
                value=salt_grams,
                name="Salt Weight G",
                source_command=0x56,
                unit="g",
                raw_hex=raw_hex,
            ),
            DecodedField(
                key="salt_weight_kg",
                value=round(salt_grams / 1000.0, 2),
                name="Salt Weight Kg",
                source_command=0x56,
                unit="kg",
                raw_hex=raw_hex,
            ),
            DecodedField(
                key="salt_days_remaining",
                value=salt_days,
                name="Salt Days Remaining",
                source_command=0x56,
                unit="d",
                raw_hex=raw_hex,
            ),
            DecodedField(
                key="salt_level_pct",
                value=salt_pct,
                name="Salt Level Pct",
                source_command=0x56,
                unit="%",
                raw_hex=raw_hex,
            ),
        ]

    @classmethod
    def _extract_hex_payload(cls, value: Any) -> str | None:
        """Extract a hex payload from common cloud value shapes."""
        if isinstance(value, str):
            return cls._normalize_hex_payload(value)

        if isinstance(value, dict):
            for key in ("data", "value", "raw", "raw_hex", "rawHex", "hex", "v"):
                normalized = cls._normalize_hex_payload(value.get(key))
                if normalized:
                    return normalized

            # Fallback: nested response wrappers like {"result": {"data": "..."}}
            for nested in value.values():
                if isinstance(nested, (dict, list)):
                    normalized = cls._extract_hex_payload(nested)
                    if normalized:
                        return normalized
            return None

        if isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list, str)):
                    normalized = cls._extract_hex_payload(item)
                    if normalized:
                        return normalized
            return None

        return None

    @classmethod
    def _normalize_hex_payload(cls, value: Any) -> str | None:
        """Normalize potential hex payload strings to uppercase compact form."""
        if not isinstance(value, str):
            return None
        text = value.strip().replace(" ", "")
        if not text:
            return None
        text = cls._HEX_PREFIX_RE.sub("", text)
        if not text:
            return None
        if len(text) % 2:
            text = f"0{text}"
        if not cls._HEX_RE.fullmatch(text):
            return None
        return text.upper()

    def _select_cloud_device(
        self,
        payload: dict[str, Any],
        preferred_device_id: str | None = None,
        allow_cached_preference: bool = True,
    ) -> dict[str, Any] | None:
        """Select the most relevant cloud device from payload."""
        devices = self._extract_cloud_devices(payload)
        if not devices:
            return None

        preferred = preferred_device_id
        if not preferred and allow_cached_preference and self._cached_device is not None:
            preferred = self._cached_device.device_id
        preferred = str(preferred).strip() if preferred else ""

        if preferred:
            for device in devices:
                if preferred in self._cloud_serial_candidates(device):
                    return device

        scored = sorted(
            devices,
            key=self._score_cloud_device,
            reverse=True,
        )
        return scored[0]

    def _score_cloud_device(self, device: dict[str, Any]) -> int:
        """Score cloud device preference (softeners first)."""
        score = 0
        family = infer_family(self._extract_cloud_device_type(device))
        if family == DeviceFamily.ISOFT:
            score += 1000
        elif family == DeviceFamily.SOFTWELL:
            score += 900
        elif family == DeviceFamily.IDOS:
            score += 700
        elif family == DeviceFamily.IFILL:
            score += 500
        elif family == DeviceFamily.ISAFE:
            score += 120

        command_map = self._extract_cloud_command_map_for_device(device)
        commands = set(command_map.keys())
        if "56" in commands:
            score += 120
        if "51" in commands:
            score += 50
        if "29" in commands:
            score += 40
        if "28" in commands:
            score += 30

        # Reward commands that we can actually decode for this family.
        decoded_count = 0
        for raw_cmd, raw_hex in command_map.items():
            try:
                command_id = normalize_command_id(raw_cmd)
            except Exception:
                continue
            spec = self._decoder.get_spec(family, command_id)
            if spec is None or spec.decoder is None:
                continue
            decoded_count += 1
            score += 12
            if command_id == 0x56:
                payload_len = len(raw_hex) // 2 if raw_hex else 0
                if payload_len >= 4:
                    score += 50
                elif payload_len >= 2:
                    score += 20
            elif command_id in (0x51, 0x29):
                score += 18
            elif command_id == 0x28:
                score += 8

        if decoded_count == 0:
            score -= 80

        # Typical i-safe signature; deprioritize when no salt command is present.
        if "56" not in commands and len({"5C", "5D", "5E", "63"} & commands) >= 2:
            score -= 120

        # i-safe command 56 is write-oriented and often not a salt reservoir payload.
        if family == DeviceFamily.ISAFE and "56" in commands:
            payload_56 = command_map.get("56", "")
            payload_len = len(payload_56) // 2 if payload_56 else 0
            if payload_len < 4:
                score -= 80

        return score

    @classmethod
    def _cloud_serial_candidates(cls, device: dict[str, Any]) -> set[str]:
        """Collect candidate serial ids from one cloud device structure."""
        candidates: set[str] = set()
        for source in [device, *cls._iter_cloud_device_data(device)]:
            for key in ("sn", "serialnumber", "serialNumber"):
                value = source.get(key) if isinstance(source, dict) else None
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    candidates.add(text)
        return candidates

    @classmethod
    def _extract_cloud_installation_date(cls, device: dict[str, Any]) -> str | None:
        """Extract installation date metadata from cloud payload."""
        for source in [device, *cls._iter_cloud_device_data(device)]:
            if not isinstance(source, dict):
                continue
            for key in ("installation_date", "installationDate", "inbetriebnahmedatum"):
                value = source.get(key)
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    return text
        return None

    @classmethod
    def _resolve_cloud_serial(cls, device: dict[str, Any]) -> str:
        """Resolve preferred serial/device id for cloud device."""
        for source in [*cls._iter_cloud_device_data(device), device]:
            for key in ("sn", "serialnumber", "serialNumber"):
                value = source.get(key) if isinstance(source, dict) else None
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    return text
        return "cloud"

    @classmethod
    def _extract_cloud_device_type(cls, device: dict[str, Any]) -> Any:
        """Resolve device type from cloud payload."""
        for block in cls._iter_cloud_device_data(device):
            dt_raw = block.get("dt")
            if dt_raw is not None:
                return dt_raw
        command_map = cls._extract_cloud_command_map_for_device(device)
        ff_payload = command_map.get("FF")
        if isinstance(ff_payload, str):
            raw = ff_payload.strip()
            if len(raw) >= 2 and cls._HEX_RE.fullmatch(raw):
                return f"0x{raw[:2]}".lower()
        return (
            device.get("devicetype")
            or device.get("deviceType")
            or device.get("device_type")
        )

    def _extract_cloud_command_hex(
        self,
        payload: dict[str, Any],
        command_id: int,
        preferred_device_id: str | None = None,
    ) -> str:
        command_map = self._extract_cloud_command_map(
            payload, preferred_device_id=preferred_device_id
        )
        raw_hex = self._extract_from_command_map(command_map, command_id)
        if raw_hex:
            return raw_hex

        # Fallback: scan all devices by preference. Some accounts return multiple
        # device blocks where the preferred id can be stale or incomplete.
        devices = self._extract_cloud_devices(payload)
        if not devices:
            return ""

        preferred = str(preferred_device_id).strip() if preferred_device_id else ""
        preferred_device: dict[str, Any] | None = None
        if preferred:
            for device in devices:
                if preferred in self._cloud_serial_candidates(device):
                    preferred_device = device
                    break

        remaining = [device for device in devices if device is not preferred_device]
        ordered = sorted(remaining, key=self._score_cloud_device, reverse=True)
        if preferred_device is not None:
            ordered.insert(0, preferred_device)

        for device in ordered:
            raw_hex = self._extract_from_command_map(
                self._extract_cloud_command_map_for_device(device), command_id
            )
            if raw_hex:
                return raw_hex

        # FF (device type) is often available as dt in cloud payload without a raw cmd FF.
        if int(command_id) == 0xFF:
            for device in ordered:
                dt_raw = self._extract_cloud_device_type(device)
                normalized_dt = self._normalize_type_string(dt_raw)
                if isinstance(normalized_dt, str) and normalized_dt.startswith("0x"):
                    value = normalized_dt[2:].strip()
                    if value:
                        return value.zfill(2).upper()

        return ""

    @staticmethod
    def _extract_from_command_map(command_map: dict[str, str], command_id: int) -> str:
        """Extract one command payload from normalized command map."""
        dec_key = str(int(command_id))
        if dec_key in command_map:
            return command_map[dec_key]

        hex_key = f"{int(command_id):02X}"
        if hex_key in command_map:
            return command_map[hex_key]

        return ""

    @classmethod
    def _decode_device_number(
        cls, raw_hex: str, device_type: str | int | None
    ) -> str | None:
        """Decode command 0x06 payload into device number per API-KOMMANDOZEILEN."""
        if not raw_hex:
            return None

        text = str(raw_hex).strip().replace(" ", "")
        if text.startswith("0x"):
            text = text[2:]

        try:
            payload = bytes.fromhex(text)
        except ValueError:
            return raw_hex

        if len(payload) < 4:
            return raw_hex

        # Command 0x06 is documented as 4-byte payload; ignore trailing bytes.
        core = payload[:4]
        normalized_type = cls._normalize_type_string(device_type)
        byteorder = (
            "big" if normalized_type in cls._PRO_DEVICE_TYPES_BIG_ENDIAN else "little"
        )
        return str(int.from_bytes(core, byteorder=byteorder, signed=False))
