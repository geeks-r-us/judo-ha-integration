"""Tests for command encoding."""

import pytest

from custom_components.judo_isoft.judo_client.models import DeviceFamily
from custom_components.judo_isoft.judo_client.protocol.decoder import DecoderRegistry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


def test_encode_target_hardness() -> None:
    """Hardness command should encode as 1-byte dH payload."""
    decoder = DecoderRegistry()
    assert decoder.encode(DeviceFamily.ISOFT, "30", 10) == "0A"


def test_encode_target_hardness_accepts_raw_hex_payload() -> None:
    """Target hardness encoder should accept raw hex payload for compatibility."""
    decoder = DecoderRegistry()
    assert decoder.encode(DeviceFamily.ISOFT, "30", "0700") == "0700"


def test_encode_salt_weight() -> None:
    """Salt command should encode as little-endian u16."""
    decoder = DecoderRegistry()
    assert decoder.encode(DeviceFamily.ISOFT, "56", 18500) == "4448"


def test_encode_vacation_mode_with_optional_duration() -> None:
    """Vacation mode should support the documented flag-plus-days payload."""
    decoder = DecoderRegistry()
    assert (
        decoder.encode(DeviceFamily.ISOFT, "41", {"flags": 0x01, "days": 5}) == "0105"
    )


def test_encode_isoft_pro_scene_commands_from_docs_examples() -> None:
    """i-soft PRO scene commands from the doc should be addressable."""
    decoder = DecoderRegistry()
    assert (
        decoder.encode(
            DeviceFamily.ISOFT,
            "37",
            "01060B01010001010107080F0E1E",
        )
        == "01060B01010001010107080F0E1E"
    )
    assert decoder.encode(DeviceFamily.ISOFT, "38", 1) == "01"


def test_encode_idos_dosage_and_pump_mode() -> None:
    """i-dos write payloads should follow the documented byte layout."""
    decoder = DecoderRegistry()
    assert decoder.encode(DeviceFamily.IDOS, "52", 2) == "0002"
    assert (
        decoder.encode(DeviceFamily.IDOS, "53", {"mode": 1, "rpm": 0}) == "010000"
    )


def test_encode_read_only_command_raises() -> None:
    """Encoding read-only command should fail."""
    decoder = DecoderRegistry()
    with pytest.raises(ValueError):
        decoder.encode(DeviceFamily.ISOFT, "28", 1)
