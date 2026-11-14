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

# Service call constants
SERVICE_EXECUTE_COMMAND = "execute_command"

# Service schemas
ATTR_VALUE = "value"
ATTR_DEVICE_ID = "device_id"
ATTR_COMMAND = "command"
ATTR_TRANSPORT = "transport"
