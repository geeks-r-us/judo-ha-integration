"""Tests for legacy compatibility aliases."""

from __future__ import annotations

import pytest

from custom_components.judo_isoft.__init__ import _inject_legacy_field_aliases


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


def test_injects_legacy_salt_alias() -> None:
    """salt_level_pct should expose judo_isoft_salt_level compatibility key."""
    fields = [
        {
            "key": "salt_level_pct",
            "name": "Salt Level Pct",
            "value": 80.0,
            "unit": "%",
            "source_command": 0x56,
        }
    ]
    fields_by_key = {"salt_level_pct": fields[0]}

    out_fields, out_by_key = _inject_legacy_field_aliases(fields, fields_by_key)

    assert "judo_isoft_salt_level" in out_by_key
    assert out_by_key["judo_isoft_salt_level"]["value"] == 80.0
    assert (
        out_by_key["judo_isoft_salt_level"]["name"]
        == "Judo iSoft Salt Level (Estimated)"
    )
    assert any(f.get("key") == "judo_isoft_salt_level" for f in out_fields)


def test_injects_legacy_salt_alias_from_weight_when_pct_missing() -> None:
    """salt_weight_g fallback should compute compatibility salt level percent."""
    fields = [
        {
            "key": "salt_weight_g",
            "name": "Salt Weight G",
            "value": 2500,
            "unit": "g",
            "source_command": 0x56,
        }
    ]
    fields_by_key = {"salt_weight_g": fields[0]}

    _, out_by_key = _inject_legacy_field_aliases(fields, fields_by_key)

    assert out_by_key["judo_isoft_salt_level"]["value"] == 5.0
    assert out_by_key["judo_isoft_salt_level"]["unit"] == "%"


def test_injects_legacy_salt_alias_even_when_no_salt_data() -> None:
    """Legacy salt entity should still exist to keep old automations valid."""
    fields = [{"key": "water_total_l", "value": 100, "source_command": 0x28}]
    fields_by_key = {"water_total_l": fields[0]}

    _, out_by_key = _inject_legacy_field_aliases(fields, fields_by_key)

    assert "judo_isoft_salt_level" in out_by_key
    assert out_by_key["judo_isoft_salt_level"]["value"] is None
