#!/usr/bin/env python3
"""Mock Judo iSoft device server for testing."""

import logging
import random
from datetime import datetime

from aiohttp import web
from aiohttp.web import middleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock device state
class MockJudoDevice:
    def __init__(self):
        self.online = True
        self.alarm = False
        self.maintenance_required = False
        self.regeneration_active = False
        self.water_hardness = 15.5
        self.water_consumption = 1500
        self.salt_level = 85
        self.flow_rate = 0.0
        self.system_pressure = 3.2
        self.filter_remaining = 45
        self.error_code = None
        self.last_regeneration = "2026-02-06T20:30:00"
        self.next_maintenance = "2026-03-15T10:00:00"

        # Device info
        self.model = "iSoft Safe"
        self.serial_number = "JS1234567890"
        self.firmware_version = "2.1.03"
        self.hardware_version = "HW-1.2"

    def update_dynamic_values(self):
        """Update values that change over time."""
        # Simulate flow rate changes
        if random.random() < 0.3:  # 30% chance of flow
            self.flow_rate = random.uniform(10.0, 35.0)
        else:
            self.flow_rate = 0.0

        # Gradually decrease salt level
        if random.random() < 0.1:  # 10% chance per request
            self.salt_level = max(0, self.salt_level - random.uniform(0.1, 0.5))

        # Trigger maintenance if salt is very low
        if self.salt_level < 20:
            self.maintenance_required = True

        # Randomly trigger regeneration
        if random.random() < 0.05:  # 5% chance
            self.regeneration_active = not self.regeneration_active
            if self.regeneration_active:
                self.salt_level = min(100, self.salt_level + random.uniform(5, 15))

        # Simulate slight pressure variations
        self.system_pressure = max(
            2.5, min(4.0, self.system_pressure + random.uniform(-0.1, 0.1))
        )

        # Decrease filter days
        if random.random() < 0.05:
            self.filter_remaining = max(0, self.filter_remaining - random.randint(0, 2))


# Global mock device instance
mock_device = MockJudoDevice()


@middleware
async def cors_middleware(request, handler):
    """CORS middleware for development."""
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


async def handle_status(request):
    """Handle /api/status endpoint."""
    mock_device.update_dynamic_values()

    data = {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "device": {
            "online": mock_device.online,
            "model": mock_device.model,
            "serial_number": mock_device.serial_number,
        },
    }

    return web.json_response(data)


async def handle_system_status(request):
    """Handle /api/system/status endpoint."""
    mock_device.update_dynamic_values()

    data = {
        "online": mock_device.online,
        "alarm": mock_device.alarm,
        "maintenance_required": mock_device.maintenance_required,
        "regeneration_active": mock_device.regeneration_active,
        "error_code": mock_device.error_code,
        "timestamp": datetime.now().isoformat(),
        "firmware_version": mock_device.firmware_version,
        "hardware_version": mock_device.hardware_version,
        "serial_number": mock_device.serial_number,
    }

    return web.json_response(data)


async def handle_water_data(request):
    """Handle /api/water/data endpoint."""
    mock_device.update_dynamic_values()

    data = {
        "hardness": mock_device.water_hardness,
        "consumption": mock_device.water_consumption,
        "flow_rate": mock_device.flow_rate,
        "pressure": mock_device.system_pressure,
        "timestamp": datetime.now().isoformat(),
    }

    return web.json_response(data)


async def handle_maintenance_data(request):
    """Handle /api/maintenance/data endpoint."""
    mock_device.update_dynamic_values()

    data = {
        "salt_level": mock_device.salt_level,
        "filter_remaining_days": mock_device.filter_remaining,
        "last_regeneration": mock_device.last_regeneration,
        "next_maintenance": mock_device.next_maintenance,
        "timestamp": datetime.now().isoformat(),
    }

    return web.json_response(data)


async def handle_device_info(request):
    """Handle /api/device/info endpoint."""
    data = {
        "model": mock_device.model,
        "serial_number": mock_device.serial_number,
        "firmware_version": mock_device.firmware_version,
        "hardware_version": mock_device.hardware_version,
        "manufacturer": "Judo Wasseraufbereitung GmbH",
    }

    return web.json_response(data)


async def handle_root(request):
    """Handle root endpoint with device information."""
    data = {
        "device": "Judo iSoft Mock Server",
        "version": "1.0.0",
        "endpoints": [
            "/api/status",
            "/api/system/status",
            "/api/water/data",
            "/api/maintenance/data",
            "/api/device/info",
        ],
        "description": "Mock Judo iSoft device for Home Assistant integration testing",
        "timestamp": datetime.now().isoformat(),
    }

    return web.json_response(data)


async def handle_control(request):
    """Handle control endpoints for testing."""
    if request.method == "POST":
        try:
            data = await request.json()
            command = data.get("command")

            if command == "trigger_alarm":
                mock_device.alarm = True
                mock_device.error_code = "E001"
            elif command == "clear_alarm":
                mock_device.alarm = False
                mock_device.error_code = None
            elif command == "trigger_maintenance":
                mock_device.maintenance_required = True
            elif command == "clear_maintenance":
                mock_device.maintenance_required = False
            elif command == "start_regeneration":
                mock_device.regeneration_active = True
            elif command == "stop_regeneration":
                mock_device.regeneration_active = False
            elif command == "set_salt_level":
                mock_device.salt_level = float(data.get("value", 85))
            elif command == "set_flow_rate":
                mock_device.flow_rate = float(data.get("value", 0))
            elif command == "go_offline":
                mock_device.online = False
            elif command == "go_online":
                mock_device.online = True

            return web.json_response({"status": "ok", "command": command})

        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # GET request - show available commands
    commands = {
        "available_commands": [
            {"command": "trigger_alarm", "description": "Trigger system alarm"},
            {"command": "clear_alarm", "description": "Clear system alarm"},
            {
                "command": "trigger_maintenance",
                "description": "Trigger maintenance required",
            },
            {
                "command": "clear_maintenance",
                "description": "Clear maintenance required",
            },
            {
                "command": "start_regeneration",
                "description": "Start regeneration cycle",
            },
            {"command": "stop_regeneration", "description": "Stop regeneration cycle"},
            {
                "command": "set_salt_level",
                "description": "Set salt level",
                "parameter": "value",
            },
            {
                "command": "set_flow_rate",
                "description": "Set flow rate",
                "parameter": "value",
            },
            {"command": "go_offline", "description": "Simulate device offline"},
            {"command": "go_online", "description": "Simulate device online"},
        ],
        "usage": 'POST /api/control with JSON: {"command": "trigger_alarm"}',
        "current_state": {
            "online": mock_device.online,
            "alarm": mock_device.alarm,
            "maintenance_required": mock_device.maintenance_required,
            "regeneration_active": mock_device.regeneration_active,
            "salt_level": mock_device.salt_level,
            "flow_rate": mock_device.flow_rate,
        },
    }

    return web.json_response(commands)


def create_app():
    """Create the web application."""
    app = web.Application(middlewares=[cors_middleware])

    # Add routes
    app.router.add_get("/", handle_root)
    app.router.add_get("/api/status", handle_status)
    app.router.add_get("/api/system/status", handle_system_status)
    app.router.add_get("/api/water/data", handle_water_data)
    app.router.add_get("/api/maintenance/data", handle_maintenance_data)
    app.router.add_get("/api/device/info", handle_device_info)
    app.router.add_get("/api/control", handle_control)
    app.router.add_post("/api/control", handle_control)

    return app


if __name__ == "__main__":
    app = create_app()

    logger.info("🚰 Starting Judo iSoft Mock Device Server...")
    logger.info("📡 Available endpoints:")
    logger.info("  • GET  /                    - Device information")
    logger.info("  • GET  /api/status          - Basic status")
    logger.info("  • GET  /api/system/status   - System status")
    logger.info("  • GET  /api/water/data      - Water data")
    logger.info("  • GET  /api/maintenance/data - Maintenance data")
    logger.info("  • GET  /api/device/info     - Device information")
    logger.info("  • GET  /api/control         - Control commands help")
    logger.info("  • POST /api/control         - Execute control command")
    logger.info("")
    logger.info("🔧 Test commands:")
    logger.info(
        "  curl -X POST http://localhost:8080/api/control -H 'Content-Type: application/json' -d '{\"command\":\"trigger_alarm\"}'"
    )
    logger.info("")
    logger.info("🌐 Server starting on http://0.0.0.0:8080")

    web.run_app(app, host="0.0.0.0", port=8080)
