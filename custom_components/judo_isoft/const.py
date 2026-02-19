"""Constants for the Judo iSoft integration."""

from __future__ import annotations

# Integration domain
DOMAIN = "judo_isoft"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_TIMEOUT = 10

# Device information
MANUFACTURER = "Judo Wasseraufbereitung GmbH"
MODEL = "iSoft"

# Entity types
SENSOR_TYPES = {
    "water_hardness": {
        "name": "Water Hardness",
        "icon": "mdi:water",
        "unit": "°dH",
        "device_class": None,
    },
    "water_consumption": {
        "name": "Water Consumption",
        "icon": "mdi:water-pump",
        "unit": "L",
        "device_class": "water",
    },
    "salt_level": {
        "name": "Salt Level",
        "icon": "mdi:shaker",
        "unit": "%",
        "device_class": None,
    },
    "flow_rate": {
        "name": "Flow Rate",
        "icon": "mdi:waves",
        "unit": "L/min",
        "device_class": None,
    },
    "system_pressure": {
        "name": "System Pressure",
        "icon": "mdi:gauge",
        "unit": "bar",
        "device_class": "pressure",
    },
    "filter_remaining": {
        "name": "Filter Remaining",
        "icon": "mdi:filter-variant",
        "unit": "days",
        "device_class": None,
    },
    "system_health": {
        "name": "System Health",
        "icon": "mdi:heart-pulse",
        "unit": "%",
        "device_class": None,
    },
    "error_code": {
        "name": "Error Code",
        "icon": "mdi:alert-circle",
        "unit": None,
        "device_class": None,
    },
    "last_regeneration": {
        "name": "Last Regeneration",
        "icon": "mdi:refresh",
        "unit": None,
        "device_class": "timestamp",
    },
    "next_maintenance": {
        "name": "Next Maintenance",
        "icon": "mdi:calendar-clock",
        "unit": None,
        "device_class": "timestamp",
    },
    "connection_mode": {
        "name": "Connection Mode",
        "icon": "mdi:connection",
        "unit": None,
        "device_class": None,
    },
}

BINARY_SENSOR_TYPES = {
    "online": {
        "name": "Online",
        "icon": "mdi:wifi",
        "device_class": "connectivity",
    },
    "alarm": {
        "name": "Alarm",
        "icon": "mdi:alert",
        "device_class": "problem",
    },
    "maintenance_required": {
        "name": "Maintenance Required",
        "icon": "mdi:wrench",
        "device_class": "problem",
    },
    "regeneration_active": {
        "name": "Regeneration Active",
        "icon": "mdi:refresh",
        "device_class": None,
    },
    "low_salt": {
        "name": "Low Salt Level",
        "icon": "mdi:shaker-outline",
        "device_class": "problem",
    },
    "filter_replacement": {
        "name": "Filter Replacement Due",
        "icon": "mdi:filter-remove",
        "device_class": "problem",
    },
}

# Service call constants
SERVICE_START_REGENERATION = "start_regeneration"
SERVICE_STOP_REGENERATION = "stop_regeneration"
SERVICE_CLEAR_ALARM = "clear_alarm"
SERVICE_TRIGGER_MAINTENANCE = "trigger_maintenance"
SERVICE_CLEAR_MAINTENANCE = "clear_maintenance"
SERVICE_SET_SALT_LEVEL = "set_salt_level"
SERVICE_SET_FLOW_RATE = "set_flow_rate"
SERVICE_SET_WATER_HARDNESS = "set_water_hardness"
SERVICE_RESET_SYSTEM = "reset_system"

# Service schemas
ATTR_VALUE = "value"
ATTR_SALT_LEVEL = "salt_level"
ATTR_FLOW_RATE = "flow_rate"
ATTR_WATER_HARDNESS = "water_hardness"

# Error codes
ERROR_CODES = {
    "E001": "General system error",
    "E002": "Salt level critical",
    "E003": "Filter replacement required",
    "E004": "Water pressure too low",
    "E005": "Water pressure too high",
    "E006": "Regeneration failed",
    "E007": "Communication error",
    "E008": "Sensor malfunction",
    "E009": "Power supply issue",
    "E010": "Memory error",
}
