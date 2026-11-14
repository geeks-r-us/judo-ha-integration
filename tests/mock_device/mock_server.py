#!/usr/bin/env python3
"""Mock Judo iSoft command endpoint server for development/testing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from aiohttp import web
from aiohttp.web import middleware

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def _u16le_hex(value: int) -> str:
    return int(value).to_bytes(2, byteorder="little", signed=False).hex().upper()


def _u32le_hex(value: int) -> str:
    return int(value).to_bytes(4, byteorder="little", signed=False).hex().upper()


@dataclass
class MockJudoDevice:
    """Simple mutable in-memory mock state."""

    device_type: int = 0x33
    serial_number: int = 121188
    firmware_major: int = 0x6B
    firmware_minor: int = 0x15
    firmware_patch: int = 0x02
    target_hardness: int = 6
    water_total_l: int = 1057516
    soft_water_l: int = 56366
    salt_weight_g: int = 21750
    salt_days_remaining: int = 17
    alarm_active: bool = False
    maintenance_required: bool = False
    regeneration_active: bool = False

    def status_flags(self) -> int:
        flags = 0
        if self.alarm_active:
            flags |= 0x01
        if self.maintenance_required:
            flags |= 0x02
        if self.regeneration_active:
            flags |= 0x04
        return flags

    def read_command_hex(self, command_id: int) -> str:
        """Return command payload as uppercase hex."""
        if command_id == 0x01:  # firmware version
            return f"{self.firmware_major:02X}{self.firmware_minor:02X}{self.firmware_patch:02X}"
        if command_id == 0x06:  # serial
            return _u32le_hex(self.serial_number)
        if command_id == 0x25:  # runtime counter
            return "060C7500"
        if command_id == 0x28:  # total water
            return _u32le_hex(self.water_total_l)
        if command_id == 0x29:  # soft water
            return _u32le_hex(self.soft_water_l)
        if command_id == 0x43:  # status flags
            return f"{self.status_flags():02X}"
        if command_id == 0x51:  # target hardness
            return _u16le_hex(self.target_hardness)
        if command_id == 0x56:  # salt reservoir
            return _u16le_hex(self.salt_weight_g) + _u16le_hex(self.salt_days_remaining)
        if command_id == 0x57:  # salt warning days
            return f"{self.salt_days_remaining & 0xFF:02X}"
        if command_id == 0xFF:  # device type
            return f"{self.device_type:02X}"
        return ""

    def write_command(self, command_id: int, payload_hex: str) -> None:
        """Apply command write payload to mock state."""
        data = bytes.fromhex(payload_hex) if payload_hex else b""

        if command_id == 0x30 and len(data) >= 1:
            if len(data) >= 2:
                self.target_hardness = int.from_bytes(data[:2], byteorder="little")
            else:
                self.target_hardness = data[0]
        elif command_id == 0x35:
            self.regeneration_active = True
        elif command_id == 0x3C:
            self.alarm_active = True
        elif command_id == 0x3D:
            self.alarm_active = False
            self.maintenance_required = False
            self.regeneration_active = False
        elif command_id == 0x56 and len(data) >= 2:
            self.salt_weight_g = int.from_bytes(data[:2], byteorder="little")
        elif command_id == 0x57 and len(data) >= 1:
            self.salt_days_remaining = data[0]


MOCK_DEVICE = MockJudoDevice()


@middleware
async def cors_middleware(request, handler):
    """CORS middleware for development convenience."""
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


async def handle_root(request: web.Request) -> web.Response:
    """Return server and endpoint information."""
    return web.json_response(
        {
            "device": "Judo iSoft Mock Command Server",
            "timestamp": datetime.now().isoformat(),
            "supported_path": "/api/rest/<COMMAND_HEX>",
            "examples": [
                "/api/rest/FF00",
                "/api/rest/0600",
                "/api/rest/2800",
                "/api/rest/5600",
                "/api/rest/30000A00",
                "/api/rest/350000",
            ],
        }
    )


async def handle_rest_command(request: web.Request) -> web.Response:
    """Handle /api/rest/<payload> command requests."""
    payload = request.match_info["payload"].strip()
    if len(payload) < 4:
        return web.json_response(
            {"status": "error", "error": "invalid payload"}, status=400
        )

    try:
        command_id = int(payload[:2], 16)
    except ValueError:
        return web.json_response(
            {"status": "error", "error": "invalid command id"}, status=400
        )

    is_write = len(payload) > 4
    write_payload = payload[4:]

    if is_write:
        try:
            MOCK_DEVICE.write_command(command_id, write_payload)
        except ValueError:
            return web.json_response(
                {"status": "error", "error": "invalid write payload"}, status=400
            )
        return web.json_response(
            {
                "status": "ok",
                "command": f"{command_id:02X}",
                "data": MOCK_DEVICE.read_command_hex(command_id),
            }
        )

    return web.json_response(
        {
            "status": "ok",
            "command": f"{command_id:02X}",
            "data": MOCK_DEVICE.read_command_hex(command_id),
        }
    )


def create_app() -> web.Application:
    """Create the web application."""
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/", handle_root)
    app.router.add_get(r"/api/rest/{payload:[A-Fa-f0-9]+}", handle_rest_command)
    return app


if __name__ == "__main__":
    app = create_app()

    LOGGER.info("Starting Judo iSoft mock command server")
    LOGGER.info("Available endpoints:")
    LOGGER.info("  GET /")
    LOGGER.info("  GET /api/rest/<payload>")
    LOGGER.info("Example commands:")
    LOGGER.info("  curl http://localhost:8080/api/rest/FF00")
    LOGGER.info("  curl http://localhost:8080/api/rest/2800")
    LOGGER.info("  curl http://localhost:8080/api/rest/30000A00")
    LOGGER.info("Server starting on http://0.0.0.0:8080")

    web.run_app(app, host="0.0.0.0", port=8080)
