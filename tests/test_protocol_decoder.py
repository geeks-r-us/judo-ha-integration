"""Tests for protocol decoding and command normalization."""

import pytest

from custom_components.judo_isoft.judo_client.models import DeviceFamily
from custom_components.judo_isoft.judo_client.protocol.catalog import (
    infer_family,
    normalize_command_id,
)
from custom_components.judo_isoft.judo_client.protocol.decoder import DecoderRegistry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


def test_normalize_command_id_variants() -> None:
    """Command normalization should accept decimal/hex variants."""
    assert normalize_command_id("28") == 0x28
    assert normalize_command_id("0x28") == 0x28
    assert normalize_command_id(28) == 0x28


def test_infer_family_accepts_hex_without_prefix() -> None:
    """Device type bytes from docs should resolve to family without 0x prefix."""
    assert infer_family("33") == DeviceFamily.ISOFT
    assert infer_family("4b") == DeviceFamily.ISOFT
    assert infer_family("4c") == DeviceFamily.ISOFT
    assert infer_family("58") == DeviceFamily.ISOFT
    assert infer_family("41") == DeviceFamily.IDOS


def test_decoder_matrix_examples_from_docs() -> None:
    """Decode known examples from API docs."""
    decoder = DecoderRegistry()

    total = decoder.decode(DeviceFamily.ISOFT, "28", "EC221000")
    assert any(f.key == "water_total_l" and f.value == 1057516 for f in total.fields)

    soft = decoder.decode(DeviceFamily.ISOFT, "29", "2EDC0000")
    assert any(f.key == "soft_water_l" and f.value == 56366 for f in soft.fields)

    cloud_node = decoder.decode(DeviceFamily.ISOFT, "03", "40E20100")
    assert any(f.key == "cloud_node_id" and f.value == 123456 for f in cloud_node.fields)

    cloud_total = decoder.decode(DeviceFamily.ISOFT, "08", "444F0400")
    assert any(f.key == "water_total_l" and f.value == 282436 for f in cloud_total.fields)

    cloud_soft = decoder.decode(DeviceFamily.ISOFT, "09", "EB900200")
    assert any(f.key == "soft_water_l" and f.value == 168171 for f in cloud_soft.fields)

    hardness = decoder.decode(DeviceFamily.ISOFT, "51", "0600")
    assert any(f.key == "target_hardness" and f.value == 6.0 for f in hardness.fields)

    salt = decoder.decode(DeviceFamily.ISOFT, "56", "f6541100")
    salt_fields = {f.key: f for f in salt.fields}
    assert salt_fields["salt_weight_g"].value == 21750
    assert salt_fields["salt_weight_g"].unit == "g"
    assert salt_fields["salt_weight_kg"].value == 21.75
    assert salt_fields["salt_weight_kg"].unit == "kg"
    assert salt_fields["salt_days_remaining"].value == 17
    assert salt_fields["salt_days_remaining"].name == "Salt Range Days"
    assert salt_fields["salt_days_remaining"].unit == "d"
    assert salt_fields["salt_level_pct"].value == 43.5
    assert salt_fields["salt_level_pct"].name == "Salt Level (Estimated)"
    assert salt_fields["salt_level_pct"].unit == "%"

    # Real i-soft SAFE+ cloud payload: 0x5E carries the salt reservoir (Judo app: 32 weeks, ~50 %).
    cloud_salt = {f.key: f.value for f in decoder.decode(DeviceFamily.ISOFT, "5E", "DE58E300").fields}
    assert cloud_salt["salt_weight_g"] == 22750
    assert cloud_salt["salt_days_remaining"] == 227
    assert cloud_salt["salt_level_pct"] == 45.5

    counters = {f.key: f.value for f in decoder.decode(DeviceFamily.ISOFT, "07", "630903000400").fields}
    assert counters["maintenance_count"] == 3

    profile = decoder.decode(DeviceFamily.ISOFT, "5D", "02010B64AC0A020011")
    assert any(
        f.key == "cloud_profile_5d_raw" and f.value == "02010B64AC0A020011"
        for f in profile.fields
    )


def test_decode_firmware_from_docs_example() -> None:
    """Firmware bytes are encoded as [patch, minor, major] in docs."""
    decoder = DecoderRegistry()
    fw = decoder.decode(DeviceFamily.ISOFT, "01", "6B1502")
    values = {f.key: f.value for f in fw.fields}

    assert "firmware_major" not in values
    assert "firmware_minor" not in values
    assert "firmware_patch" not in values
    assert values["firmware_version"] == "2.21k"


def test_decode_idos_device_type_from_docs_example() -> None:
    """i-dos device type reads should decode into normalized fields."""
    decoder = DecoderRegistry()
    device_type = decoder.decode(DeviceFamily.IDOS, "FF", "41")
    values = {field.key: field.value for field in device_type.fields}

    assert values["device_type_dec"] == 0x41
    assert values["device_type_hex"] == "0x41"


def test_unknown_command_returns_raw_field() -> None:
    """Unknown command should be preserved as raw field."""
    decoder = DecoderRegistry()
    result = decoder.decode(DeviceFamily.ISOFT, "AA", "BEEF")
    assert result.fields[0].key == "cmd_AA_raw"
    assert result.fields[0].value == "BEEF"
