"""Test configuration for Judo iSoft integration."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations."""
    yield


@pytest.fixture(name="mock_api")
def mock_api_fixture():
    """Mock API for testing."""
    return {
        "system_status": {
            "online": True,
            "alarm": False,
            "maintenance_required": False,
            "regeneration_active": False,
        },
        "water_data": {
            "hardness": 15.5,
            "consumption": 1500,
            "flow_rate": 25.0,
            "pressure": 3.2,
        },
        "maintenance_data": {
            "salt_level": 85,
            "filter_remaining": 45,
        },
        "connection": {
            "access_mode": "local",
            "using_cloud": False,
        },
    }
