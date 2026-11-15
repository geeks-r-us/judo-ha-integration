"""API client for Judo iSoft based on the internal judo_client package."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .judo_client import JudoClient, TransportMode


class JudoiSoftAPIError(Exception):
    """Base exception raised for API errors."""


class JudoiSoftConnectionError(JudoiSoftAPIError):
    """Raised when device discovery or communication fails."""


class JudoiSoftCommandError(JudoiSoftAPIError):
    """Raised when command execution fails."""


class JudoiSoftAPI:
    """High-level API wrapper around the internal JudoClient."""

    def __init__(
        self,
        host: str,
        port: int = 80,
        timeout: int = 10,
        username: str | None = None,
        password: str | None = None,
        force_cloud: bool = False,
    ) -> None:
        self._username = username
        self._password = password
        self._force_cloud = force_cloud
        self._connection_source = "cloud" if force_cloud else "local"
        self._client = JudoClient(
            host=host,
            port=port,
            timeout=timeout,
            username=username,
            password=password,
            force_cloud=force_cloud,
        )

    @property
    def connection_source(self) -> str:
        """Return current connection source."""
        return self._connection_source

    @property
    def is_using_cloud(self) -> bool:
        """Return whether cloud transport is currently in use."""
        return self._connection_source.startswith("cloud") or self._force_cloud

    async def close(self) -> None:
        """Close underlying client resources."""
        await self._client.close()

    async def _first_device_id(self) -> str:
        """Return the first discovered device id."""
        devices = await self._client.discover_devices()
        if not devices:
            raise JudoiSoftConnectionError("No Judo device discovered")
        return devices[0].device_id

    async def test_connection(self) -> bool:
        """Test connectivity in local-first mode."""
        try:
            device_id = await self._first_device_id()
            snapshot = await self._client.read_snapshot(device_id)
            self._connection_source = snapshot.transport.value
            return True
        except Exception as err:
            raise JudoiSoftConnectionError(
                f"Connection failed. Ensure the device supports /api/rest access. Details: {err}"
            ) from err

    async def test_cloud_only(self) -> bool:
        """Test cloud connectivity only."""
        if not self._username or not self._password:
            raise JudoiSoftConnectionError(
                "Username and password are required for cloud mode"
            )

        try:
            device_id = await self._first_device_id()
            snapshot = await self._client.read_snapshot(device_id)
            self._connection_source = snapshot.transport.value
            return True
        except Exception as err:
            raise JudoiSoftConnectionError(f"Cloud test failed: {err}") from err

    async def get_device_info(self) -> dict[str, Any]:
        """Return normalized device information."""
        devices = await self._client.discover_devices()
        if not devices:
            raise JudoiSoftConnectionError("No Judo device discovered")
        device = devices[0]
        return {
            "model": device.model or "Judo",
            "serial_number": device.serial_number,
            "device_type": device.device_type,
            "manufacturer": device.manufacturer,
            "firmware_version": device.firmware_version,
            "hardware_version": device.hardware_version,
            "device_id": device.device_id,
            "family": device.family.value,
        }

    async def get_snapshot_data(self) -> dict[str, Any]:
        """Return decoded snapshot data in a Home Assistant-friendly shape."""
        device_id = await self._first_device_id()
        snapshot = await self._client.read_snapshot(device_id)
        self._connection_source = snapshot.transport.value

        fields = [
            {
                "key": field.key,
                "name": field.name,
                "value": field.value,
                "unit": field.unit,
                "device_class": field.device_class,
                "state_class": field.state_class,
                "icon": field.icon,
                "source_command": field.source_command,
                "raw_hex": field.raw_hex,
            }
            for field in snapshot.fields
        ]
        fields_by_key = {field["key"]: field for field in fields}

        capabilities = [
            {
                "command_id": cap.command_id,
                "name": cap.name,
                "direction": cap.direction.value,
                "unit": cap.unit,
                "payload_length": cap.payload_length,
                "default_write_value": cap.default_write_value,
            }
            for cap in snapshot.capabilities
        ]

        system_status = {
            "online": True,
            "last_update": snapshot.updated_at,
            "serial_number": snapshot.device.serial_number,
            "firmware_version": snapshot.device.firmware_version,
            "hardware_version": snapshot.device.hardware_version,
            "alarm": bool(fields_by_key.get("alarm_active", {}).get("value", False)),
            "maintenance_required": bool(
                fields_by_key.get("maintenance_required", {}).get("value", False)
            ),
            "regeneration_active": bool(
                fields_by_key.get("regeneration_active", {}).get("value", False)
            ),
        }

        device_info = {
            "model": snapshot.device.model,
            "serial_number": snapshot.device.serial_number,
            "device_type": snapshot.device.device_type,
            "manufacturer": snapshot.device.manufacturer,
            "firmware_version": snapshot.device.firmware_version,
            "hardware_version": snapshot.device.hardware_version,
            "device_id": snapshot.device.device_id,
            "family": snapshot.device.family.value,
        }

        return {
            "fields": fields,
            "fields_by_key": fields_by_key,
            "capabilities": capabilities,
            "transport": snapshot.transport.value,
            "updated_at": snapshot.updated_at,
            "device_info": device_info,
            "system_status": system_status,
            "messages": snapshot.raw.get("messages", []),
            "raw": snapshot.raw,
        }

    async def get_system_status(self) -> dict[str, Any]:
        """Return system status information."""
        snapshot = await self.get_snapshot_data()
        return snapshot.get("system_status", {})

    async def get_water_data(self) -> dict[str, Any]:
        """Return normalized water telemetry data."""
        snapshot = await self.get_snapshot_data()
        fields = snapshot.get("fields_by_key", {})
        flow_lph = fields.get("flow_lph", {}).get("value")
        return {
            "hardness": fields.get("target_hardness", {}).get("value"),
            "consumption": fields.get("water_total_l", {}).get("value"),
            "flow_rate": (
                round(float(flow_lph) / 60.0, 2)
                if isinstance(flow_lph, (int, float))
                else None
            ),
            "pressure": fields.get("pressure", {}).get("value"),
            "temperature": fields.get("temperature", {}).get("value"),
        }

    async def get_maintenance_data(self) -> dict[str, Any]:
        """Return normalized maintenance data."""
        snapshot = await self.get_snapshot_data()
        fields = snapshot.get("fields_by_key", {})
        return {
            "salt_level": fields.get("salt_level_pct", {}).get("value"),
            "filter_remaining": fields.get("salt_days_remaining", {}).get("value"),
            "salt_weight_g": fields.get("salt_weight_g", {}).get("value"),
            "last_regeneration": fields.get("last_regeneration", {}).get("value"),
            "next_maintenance": fields.get("next_maintenance", {}).get("value"),
        }

    async def get_all_data(self) -> dict[str, Any]:
        """Return all normalized data groups."""
        system_status = await self.get_system_status()
        water_data = await self.get_water_data()
        maintenance_data = await self.get_maintenance_data()
        device_info = await self.get_device_info()

        return {
            "system_status": system_status,
            "water_data": water_data,
            "maintenance_data": maintenance_data,
            "device_info": device_info,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

    async def get_available_commands(self) -> list[dict[str, Any]]:
        """Return command capabilities from the current snapshot."""
        snapshot = await self.get_snapshot_data()
        return snapshot.get("capabilities", [])

    async def get_system_health(self) -> dict[str, Any]:
        """Compute a coarse health score from snapshot data."""
        all_data = await self.get_all_data()

        system_status = all_data.get("system_status", {})
        maintenance_data = all_data.get("maintenance_data", {})

        health_factors: list[tuple[str, int]] = []
        health_factors.append(
            ("connectivity", 100 if system_status.get("online") else 0)
        )
        health_factors.append(
            ("alarm_status", 0 if system_status.get("alarm") else 100)
        )

        salt_level = maintenance_data.get("salt_level")
        if salt_level is None:
            health_factors.append(("salt_level", 50))
        elif salt_level >= 80:
            health_factors.append(("salt_level", 100))
        elif salt_level >= 50:
            health_factors.append(("salt_level", 70))
        elif salt_level >= 20:
            health_factors.append(("salt_level", 40))
        else:
            health_factors.append(("salt_level", 10))

        health_factors.append(
            ("maintenance", 50 if system_status.get("maintenance_required") else 100)
        )
        score = sum(value for _, value in health_factors) / max(1, len(health_factors))

        return {
            "overall_health": round(score, 1),
            "health_factors": dict(health_factors),
            "status": (
                "excellent"
                if score >= 90
                else "good" if score >= 70 else "fair" if score >= 50 else "poor"
            ),
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

    async def execute_command(
        self,
        device_id: str,
        command: int | str,
        value: Any | None = None,
        transport: str = "auto",
    ) -> dict[str, Any]:
        """Execute a generic read/write command."""
        mode = {
            "auto": TransportMode.AUTO,
            "local": TransportMode.LOCAL,
            "cloud": TransportMode.CLOUD,
        }.get(str(transport).lower(), TransportMode.AUTO)

        resolved_device_id = device_id or await self._first_device_id()

        if value is None:
            read_result = await self._client.read_command(
                resolved_device_id, command, transport=mode
            )
            return {
                "status": "ok",
                "command_id": read_result.command_id,
                "command_hex": f"{read_result.command_id:02X}",
                "fields": [
                    {
                        "key": field.key,
                        "name": field.name,
                        "value": field.value,
                        "unit": field.unit,
                        "source_command": field.source_command,
                    }
                    for field in read_result.fields
                ],
                "raw_hex": read_result.raw_hex,
                "raw_response": read_result.raw,
            }

        write_result = await self._client.write_command(
            resolved_device_id, command, value, transport=mode
        )
        return {
            "status": write_result.status,
            "command_id": write_result.command_id,
            "command_hex": f"{write_result.command_id:02X}",
            "transport": write_result.transport.value,
            "error": write_result.error,
            "raw": write_result.raw,
        }


__all__ = [
    "JudoiSoftAPI",
    "JudoiSoftAPIError",
    "JudoiSoftConnectionError",
    "JudoiSoftCommandError",
]
