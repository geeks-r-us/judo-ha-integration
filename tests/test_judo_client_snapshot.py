"""Tests for JudoClient snapshot and command execution."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.judo_isoft.judo_client.client import JudoClient
from custom_components.judo_isoft.judo_client.models import (
    DeviceDescriptor,
    DeviceFamily,
    TransportMode,
)
from custom_components.judo_isoft.judo_client.transport import JudoTransport, JudoTransportError


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


def test_decode_device_number_examples_from_docs() -> None:
    """Device number decoding should follow API-KOMMANDOZEILEN examples."""
    assert JudoClient._decode_device_number("64d90100", "0x33") == "121188"
    assert JudoClient._decode_device_number("0774ed0b", "0x41") == "200111111"
    assert JudoClient._decode_device_number("10D36F28", "0x58") == "282292008"
    assert JudoClient._decode_device_number("aabbccddeeff", "0x67") == "3721182122"


def test_resolve_cloud_target_ids_uses_cloud_node_id_when_sn_missing() -> None:
    """Cloud node id should be used as sn fallback when no explicit sn is present."""
    device = {
        "serialnumber": "aabbccddeeff",
        "ewuid": "5de883b6-9e3b-11ef-af7e-005056930189",
        "data": [
            {
                "dt": "0x33",
                "data": {
                    "3": {"data": "40E20100", "st": "OK", "er": ""},
                    "51": {"data": "0700", "st": "OK", "er": ""},
                },
            }
        ],
    }

    resolved_sn, resolved_serialnumber = JudoClient._resolve_cloud_target_ids(device)

    assert resolved_sn == "123456"
    assert resolved_serialnumber == "aabbccddeeff"


def test_extract_cloud_salt_metadata_candidates_filters_plain_metadata_keys() -> None:
    """Salt metadata helper should ignore command maps and keep plain candidate keys."""
    device = {
        "serialnumber": "aabbccddeeff",
        "waterscene": "normal",
        "salt_remaining_weeks": 32,
        "salt_warning_text": "Refill soon",
        "data": [
            {
                "dt": "0x33",
                "salz_reichweite_wochen": 32,
                "data": {
                    "56": {"data": "D44B1000", "st": "OK", "er": ""},
                    "57": {"data": "10", "st": "OK", "er": ""},
                },
            }
        ],
    }

    candidates = JudoClient._extract_cloud_metadata_candidates(
        device, JudoClient._SALT_METADATA_KEYWORDS
    )

    assert candidates == {
        "salt_remaining_weeks": 32,
        "salt_warning_text": "Refill soon",
        "salz_reichweite_wochen": 32,
    }


@pytest.mark.asyncio
async def test_transport_write_cloud_command_hex00_uses_3000_cmd_token() -> None:
    """Cloud write transport should support `/api/rest`-style `3000` cmd token."""
    transport = JudoTransport(
        host="cloud.device",
        port=80,
        timeout=10,
        username="user",
        password="pass",
        force_cloud=True,
    )
    auth = type(
        "AuthStub",
        (),
        {
            "ensure_token": AsyncMock(return_value="token-1"),
            "clear_token": lambda self: None,
        },
    )()

    with patch.object(transport, "authenticator", new=AsyncMock(return_value=auth)):
        with patch.object(
            transport, "request_cloud", new=AsyncMock(return_value={"status": "ok"})
        ) as request_cloud:
            await transport.write_cloud_command(
                0x30,
                "0A00",
                sn="123456",
                serialnumber="739891554",
                cmd_encoding="hex00",
            )

    request_cloud.assert_awaited_once()
    params = request_cloud.await_args.kwargs["params"]
    assert params["cmd"] == "3000"
    assert params["data"] == "0A00"
    assert params["sn"] == "123456"
    assert params["serialnumber"] == "739891554"

    await transport.close()


@pytest.mark.asyncio
async def test_transport_write_cloud_command_rest_inline_embeds_payload_in_cmd() -> None:
    """Cloud transport should support REST-style inline cmd tokens like `300007`."""
    transport = JudoTransport(
        host="cloud.device",
        port=80,
        timeout=10,
        username="user",
        password="pass",
        force_cloud=True,
    )
    auth = type(
        "AuthStub",
        (),
        {
            "ensure_token": AsyncMock(return_value="token-1"),
            "clear_token": lambda self: None,
        },
    )()

    with patch.object(transport, "authenticator", new=AsyncMock(return_value=auth)):
        with patch.object(
            transport, "request_cloud", new=AsyncMock(return_value={"status": "ok"})
        ) as request_cloud:
            await transport.write_cloud_command(
                0x30,
                "07",
                sn="123456",
                serialnumber="739891554",
                cmd_encoding="rest_inline",
            )

    request_cloud.assert_awaited_once()
    params = request_cloud.await_args.kwargs["params"]
    assert params["cmd"] == "300007"
    assert "data" not in params
    assert params["sn"] == "123456"
    assert params["serialnumber"] == "739891554"

    await transport.close()


@pytest.mark.asyncio
async def test_transport_request_cloud_preserves_raw_text_for_json_null() -> None:
    """Cloud transport should keep raw response text when the body is JSON null."""
    transport = JudoTransport(
        host="cloud.device",
        port=80,
        timeout=10,
        username="user",
        password="pass",
        force_cloud=True,
    )

    class _FakeResponse:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def raise_for_status(self) -> None:
            return None

        async def text(self) -> str:
            return "null"

        async def json(self, content_type=None):
            return None

    class _FakeSession:
        def request(self, method, url, params=None):
            return _FakeResponse()

    with patch.object(transport, "session", new=AsyncMock(return_value=_FakeSession())):
        result = await transport.request_cloud("GET", params={"group": "register"})

    assert result["value"] is None
    assert result["raw_text"] == "null"
    assert result["status_code"] == 200
    assert result["_source"] == "cloud"

    await transport.close()


@pytest.mark.asyncio
async def test_transport_write_cloud_command_preserves_sn_only_target() -> None:
    """Cloud transport should omit serialnumber when caller selects sn-only routing."""
    transport = JudoTransport(
        host="cloud.device",
        port=80,
        timeout=10,
        username="user",
        password="pass",
        force_cloud=True,
    )
    auth = type(
        "AuthStub",
        (),
        {
            "ensure_token": AsyncMock(return_value="token-1"),
            "clear_token": lambda self: None,
        },
    )()

    with patch.object(transport, "authenticator", new=AsyncMock(return_value=auth)):
        with patch.object(
            transport, "request_cloud", new=AsyncMock(return_value={"status": "ok"})
        ) as request_cloud:
            await transport.write_cloud_command(
                0x30,
                "0A",
                sn="123456",
                serialnumber=None,
                cmd_encoding="hex00",
            )

    params = request_cloud.await_args.kwargs["params"]
    assert params["sn"] == "123456"
    assert "serialnumber" not in params

    await transport.close()


@pytest.mark.asyncio
async def test_transport_write_cloud_command_preserves_serialnumber_only_target() -> None:
    """Cloud transport should omit sn when caller selects serialnumber-only routing."""
    transport = JudoTransport(
        host="cloud.device",
        port=80,
        timeout=10,
        username="user",
        password="pass",
        force_cloud=True,
    )
    auth = type(
        "AuthStub",
        (),
        {
            "ensure_token": AsyncMock(return_value="token-1"),
            "clear_token": lambda self: None,
        },
    )()

    with patch.object(transport, "authenticator", new=AsyncMock(return_value=auth)):
        with patch.object(
            transport, "request_cloud", new=AsyncMock(return_value={"status": "ok"})
        ) as request_cloud:
            await transport.write_cloud_command(
                0x30,
                "0A",
                sn=None,
                serialnumber="739891554",
                cmd_encoding="hex00",
            )

    params = request_cloud.await_args.kwargs["params"]
    assert params["serialnumber"] == "739891554"
    assert "sn" not in params

    await transport.close()


@pytest.mark.asyncio
async def test_read_snapshot_from_cloud_payload() -> None:
    """Snapshot should decode cloud command map into fields."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "status": "online",
                "data": [
                    {
                        "dt": "0x33",
                        "sv": "2.21k",
                        "hv": "1.0",
                        "lu": "2026-01-01T00:00:00",
                        "data": {
                            "28": {"st": "OK", "data": "EC221000"},
                            "29": {"st": "OK", "data": "2EDC0000"},
                            "51": {"st": "OK", "data": "0600"},
                            "56": {"st": "OK", "data": "f6541100"},
                        },
                    }
                ],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("12345")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["water_total_l"] == 1057516
    assert fields["soft_water_l"] == 56366
    assert fields["target_hardness"] == 6.0
    assert fields["salt_weight_g"] == 21750

    await client.close()


@pytest.mark.asyncio
async def test_cloud_discovery_accepts_dict_device_data_shape() -> None:
    """Cloud discovery should accept device.data as dict, not only list."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "123456",
                "devicetype": "0x67",
                "data": {
                    "dt": "0x67",
                    "sv": "2.21k",
                    "hv": "1.0",
                    "data": {"28": {"st": "OK", "data": "EC221000"}},
                },
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        devices = await client.discover_devices()

    assert len(devices) == 1
    assert devices[0].device_id == "123456"
    assert devices[0].device_type == "0x67"

    await client.close()


@pytest.mark.asyncio
async def test_cloud_discovery_prefers_sn_over_serialnumber() -> None:
    """Cloud discovery should prioritize app/device sn when available."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "739891554",
                "data": {
                    "sn": "123456",
                    "dt": "0x67",
                    "data": {"28": {"st": "OK", "data": "EC221000"}},
                },
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        devices = await client.discover_devices()
        snapshot = await client.read_snapshot("123456")

    assert len(devices) == 1
    assert devices[0].device_id == "123456"
    assert devices[0].serial_number == "123456"
    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["serial_number"] == "123456"

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_from_cloud_payload_with_root_devices_dict() -> None:
    """Snapshot decoding should accept payload.data.devices response shape."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": {
            "devices": [
                {
                    "serialNumber": "12345",
                    "deviceType": "0x33",
                    "data": {
                        "dt": "0x33",
                        "sv": "2.21k",
                        "hv": "1.0",
                        "data": {
                            "28": {"st": "OK", "data": "EC221000"},
                            "29": {"st": "OK", "data": "2EDC0000"},
                        },
                    },
                }
            ]
        },
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("12345")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["water_total_l"] == 1057516
    assert fields["soft_water_l"] == 56366

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_ignores_non_command_keys_in_cloud_payload() -> None:
    """Cloud payload keys like sn/dt should not break command decoding."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": {
                    "dt": "0x67",
                    "sn": "123456",
                    "sv": "2.21k",
                    "data": {"28": {"st": "OK", "data": "EC221000"}},
                },
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("12345")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["water_total_l"] == 1057516

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_skips_unknown_raw_command_fields() -> None:
    """Unknown cloud command ids should not create cmd_xx_raw entities."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": {
                    "dt": "0x67",
                    "data": {
                        "28": {"st": "OK", "data": "EC221000"},
                        "02": {"st": "OK", "data": "0A05"},
                        "03": {"st": "OK", "data": "40E20100"},
                    },
                },
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("12345")

    keys = {field.key for field in snapshot.fields}
    assert "water_total_l" in keys
    assert all(not key.startswith("cmd_") for key in keys)

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_merges_multiple_cloud_data_blocks() -> None:
    """Meaningful commands can live in later cloud data blocks and must be parsed."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": [
                    {"dt": "0x67", "sn": "123456", "02": {"st": "OK", "data": "0A05"}},
                    {
                        "dt": "0x67",
                        "data": {
                            "28": {"st": "OK", "data": "EC221000"},
                            "56": {"st": "OK", "data": "f6541100"},
                        },
                    },
                ],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        devices = await client.discover_devices()
        snapshot = await client.read_snapshot("123456")

    fields = {field.key: field.value for field in snapshot.fields}
    assert devices[0].serial_number == "123456"
    assert fields["water_total_l"] == 1057516
    assert fields["salt_weight_g"] == 21750
    assert all(not key.startswith("cmd_") for key in fields)

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_prefers_richer_duplicate_cloud_payload() -> None:
    """Duplicate command ids should keep the richer payload."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": {
                    "dt": "0x67",
                    "sn": "123456",
                    "data": {
                        "28": {"st": "OK", "data": "EC221000"},
                        "56": {"st": "OK", "data": "f6541100"},
                    },
                },
                # Duplicate command from another block with less information.
                "56": {"st": "OK", "data": "01"},
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("123456")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["salt_weight_g"] == 21750
    assert fields["salt_level_pct"] == 43.5

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_derives_salt_from_segmented_cloud_blob() -> None:
    """When cmd 56 is absent in cloud payload, derive salt from segmented blob."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "aabbccddeeff",
                "status": "online",
                "data": [
                    {
                        "da": "0x1",
                        "dt": "0x33",
                        "sv": "3.2n",
                        "hv": "5.10",
                        "data": {
                            "1": {"data": "6E0203", "st": "OK", "er": ""},
                            "3": {"data": "40E20100", "st": "OK", "er": ""},
                            "6": {"data": "62D91885", "st": "OK", "er": ""},
                            "8": {"data": "444F0400", "st": "OK", "er": ""},
                            "9": {"data": "EB900200", "st": "OK", "er": ""},
                            "93": {"data": "02010B64AC0A020011", "st": "OK", "er": ""},
                            "790": {
                                "data": "0:00630F3800001100080712008A026C00000000000000364BC50515023000B400",
                                "st": "OK",
                                "er": "",
                            },
                            "791": {
                                "data": "1:C000000000282D100C197800CB00000061000000000001000000910C01026102",
                                "st": "OK",
                                "er": "",
                            },
                            "792": {
                                "data": "2:003C78000000000048000000A00F840378000302A00F84030026AB0378000000",
                                "st": "OK",
                                "er": "",
                            },
                        },
                    }
                ],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("aabbccddeeff")

    fields = {field.key: field.value for field in snapshot.fields}
    units = {field.key: field.unit for field in snapshot.fields}
    assert fields["cloud_node_id"] == 123456
    assert fields["water_total_l"] == 282436
    assert fields["soft_water_l"] == 168171
    assert fields["salt_weight_g"] == 19254
    assert fields["salt_weight_kg"] == 19.25
    assert fields["salt_days_remaining"] == 17
    assert fields["salt_level_pct"] == 38.5
    assert fields["cloud_profile_5d_raw"] == "02010B64AC0A020011"
    assert units["salt_weight_kg"] == "kg"
    assert units["salt_days_remaining"] == "d"
    assert units["salt_level_pct"] == "%"

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_derives_target_hardness_from_cloud_metadata() -> None:
    """When cmd 51 is absent, derive target hardness from cloud hardness metadata."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "aabbccddeeff",
                "status": "online",
                "waterscene": "normal",
                "hardness_shower": 4,
                "hardness_watering": 10,
                "hardness_heater": 1,
                "hardness_washing": 1,
                "data": [
                    {
                        "da": "0x1",
                        "dt": "0x33",
                        "sv": "3.2n",
                        "hv": "5.10",
                        "data": {
                            "1": {"data": "6E0203", "st": "OK", "er": ""},
                            "3": {"data": "40E20100", "st": "OK", "er": ""},
                            "6": {"data": "62D91885", "st": "OK", "er": ""},
                            "8": {"data": "444F0400", "st": "OK", "er": ""},
                            "9": {"data": "EB900200", "st": "OK", "er": ""},
                        },
                    }
                ],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("aabbccddeeff")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["target_hardness"] == 4.0

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_prefers_segmented_blob_target_hardness_over_metadata() -> None:
    """When both are present, segmented blob target hardness should win over metadata."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "aabbccddeeff",
                "status": "online",
                "waterscene": "normal",
                "hardness_shower": 4,
                "hardness_watering": 10,
                "hardness_heater": 1,
                "hardness_washing": 1,
                "data": [
                    {
                        "da": "0x1",
                        "dt": "0x33",
                        "sv": "3.2n",
                        "hv": "5.10",
                        "data": {
                            "1": {"data": "6E0203", "st": "OK", "er": ""},
                            "790": {
                                "data": "0:00630F3800001100080712008A026C00000000000000364BC50515023000B400",
                                "st": "OK",
                                "er": "",
                            },
                            "791": {
                                "data": "1:C000000000282D100C197800CB00000061000000000001000000910C01026102",
                                "st": "OK",
                                "er": "",
                            },
                            "792": {
                                "data": "2:003C78000000000048000000A00F840378000302A00F84030026AB0378000000",
                                "st": "OK",
                                "er": "",
                            },
                        },
                    }
                ],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("aabbccddeeff")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["target_hardness"] == 8.0

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_prefers_cloud_installation_date_over_cmd_0e() -> None:
    """Cloud installation_date should override volatile 0x0E decoded values."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "aabbccddeeff",
                "installation_date": "2022-10-01T08:34:56",
                "status": "online",
                "data": [
                    {
                        "dt": "0x33",
                        "data": {
                            "1": {"data": "6E0203", "st": "OK", "er": ""},
                            # Observed cloud payload where key 14 is not stable commissioning date.
                            "14": {"data": "160A2205", "st": "OK", "er": ""},
                        },
                    }
                ],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("aabbccddeeff")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["commissioning_date"] == "2022-10-01T08:34:56"

    await client.close()


@pytest.mark.asyncio
async def test_cloud_selection_prefers_softener_over_isafe_noise() -> None:
    """When multiple cloud devices exist, prefer softener telemetry payload."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "111111",
                "data": {
                    "dt": "0x44",
                    "sn": "isafe-111111",
                    "data": {
                        "02": {"st": "OK", "data": "0A05"},
                        "03": {"st": "OK", "data": "40E20100"},
                        "5C": {"st": "OK", "data": "0000"},
                        "5D": {"st": "OK", "data": "02010B64AC0A020011"},
                        "5E": {"st": "OK", "data": "BE0A1900"},
                        "63": {"st": "OK", "data": "24"},
                    },
                },
            },
            {
                "serialnumber": "739891554",
                "data": {
                    "dt": "0x67",
                    "sn": "123456",
                    "sv": "2.21k",
                    "hv": "1.0",
                    "data": {
                        "28": {"st": "OK", "data": "EC221000"},
                        "29": {"st": "OK", "data": "2EDC0000"},
                        "51": {"st": "OK", "data": "0600"},
                        "56": {"st": "OK", "data": "f6541100"},
                    },
                },
            },
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        devices = await client.discover_devices()
        snapshot = await client.read_snapshot(devices[0].device_id)

    assert devices[0].device_id == "123456"
    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["target_hardness"] == 6.0
    assert fields["salt_weight_g"] == 21750

    await client.close()


@pytest.mark.asyncio
async def test_snapshot_falls_back_when_cached_preferred_device_is_wrong() -> None:
    """Snapshot decode should recover even when cached cloud device id is stale/wrong."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    client._cached_device = DeviceDescriptor(
        device_id="isafe-111111",
        family=DeviceFamily.ISAFE,
        device_type="0x44",
        serial_number="isafe-111111",
        model="Judo i_safe",
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "111111",
                "data": {
                    "dt": "0x44",
                    "sn": "isafe-111111",
                    "data": {
                        "03": {"st": "OK", "data": "40E20100"},
                        "5C": {"st": "OK", "data": "0000"},
                        "5D": {"st": "OK", "data": "02010B64AC0A020011"},
                    },
                },
            },
            {
                "serialnumber": "739891554",
                "data": {
                    "dt": "0x67",
                    "sn": "123456",
                    "data": {
                        "28": {"st": "OK", "data": "EC221000"},
                        "29": {"st": "OK", "data": "2EDC0000"},
                        "51": {"st": "OK", "data": "0600"},
                        "56": {"st": "OK", "data": "f6541100"},
                    },
                },
            },
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("isafe-111111")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["salt_weight_g"] == 21750
    assert fields["target_hardness"] == 6.0

    await client.close()


@pytest.mark.asyncio
async def test_read_command_cloud_falls_back_from_preferred_device() -> None:
    """Cloud read should scan other devices when preferred block has no command."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "111111",
                "data": {
                    "dt": "0x44",
                    "sn": "isafe-111111",
                    "data": {
                        "03": {"st": "OK", "data": "40E20100"},
                        "5C": {"st": "OK", "data": "0000"},
                    },
                },
            },
            {
                "serialnumber": "739891554",
                "data": {
                    "dt": "0x67",
                    "sn": "123456",
                    "data": {
                        "28": {"st": "OK", "data": "EC221000"},
                        "56": {"st": "OK", "data": "f6541100"},
                    },
                },
            },
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        result = await client.read_command(
            device_id="isafe-111111",
            command_id="56",
            transport=TransportMode.CLOUD,
        )

    fields = {field.key: field.value for field in result.fields}
    assert result.raw_hex == "F6541100"
    assert fields["salt_weight_g"] == 21750

    await client.close()


@pytest.mark.asyncio
async def test_read_command_cloud_supports_nested_payload_shape() -> None:
    """Cloud command extraction should handle nested result wrappers."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "739891554",
                "data": {
                    "dt": "0x67",
                    "sn": "123456",
                    "commands": {
                        "56": {"result": {"data": "f6541100"}},
                    },
                },
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        result = await client.read_command(
            device_id="123456",
            command_id="56",
            transport=TransportMode.CLOUD,
        )

    fields = {field.key: field.value for field in result.fields}
    assert result.raw_hex == "F6541100"
    assert fields["salt_weight_g"] == 21750

    await client.close()


@pytest.mark.asyncio
async def test_read_command_cloud_ff_falls_back_to_dt_when_missing() -> None:
    """FF read should derive device type from dt if FF command is absent."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "739891554",
                "data": {"dt": "0x67", "sn": "123456", "data": {"28": {"data": "EC221000"}}},
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        result = await client.read_command(
            device_id="123456",
            command_id="FF",
            transport=TransportMode.CLOUD,
        )

    fields = {field.key: field.value for field in result.fields}
    assert result.raw_hex == "67"
    assert fields["device_type_hex"] == "0x67"
    assert fields["device_type_dec"] == 103

    await client.close()


@pytest.mark.asyncio
async def test_write_command_cloud_success() -> None:
    """Write command should route to cloud when requested."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": [{"dt": "0x33", "data": {}}],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        with patch.object(
            client._transport,
            "write_cloud_command",
            new=AsyncMock(return_value={"status": "ok"}),
        ) as cloud_write:
            result = await client.write_command(
                device_id="12345",
                command_id="30",
                value=10,
                transport=TransportMode.CLOUD,
            )

    assert result.status == "ok"
    assert result.transport == TransportMode.CLOUD
    assert result.command_id == 0x30
    assert cloud_write.await_count == 9
    for index, args in enumerate(
        [
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
        ]
    ):
        assert cloud_write.await_args_list[index].args == args
    for call in cloud_write.await_args_list[:3]:
        assert call.kwargs["cmd_encoding"] == "hex"
    for call in cloud_write.await_args_list[3:6]:
        assert call.kwargs["cmd_encoding"] == "hex00"
    for call in cloud_write.await_args_list[6:]:
        assert call.kwargs["cmd_encoding"] == "rest_inline"

    await client.close()


@pytest.mark.asyncio
async def test_write_command_cloud_preserves_distinct_sn_and_serialnumber() -> None:
    """Cloud writes should fan out across distinct cloud target identifiers."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "739891554",
                "data": [{"dt": "0x33", "sn": "123456", "data": {}}],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        with patch.object(
            client._transport,
            "write_cloud_command",
            new=AsyncMock(return_value={"status": "ok"}),
        ) as cloud_write:
            result = await client.write_command(
                device_id="123456",
                command_id="30",
                value=10,
                transport=TransportMode.CLOUD,
            )

    assert result.status == "ok"
    assert result.transport == TransportMode.CLOUD
    assert result.command_id == 0x30
    assert cloud_write.await_count == 9
    for index, args in enumerate(
        [
            (0x30, "0A", "123456", "739891554", None),
            (0x30, "0A", "123456", None, None),
            (0x30, "0A", None, "739891554", None),
            (0x30, "0A", "123456", "739891554", None),
            (0x30, "0A", "123456", None, None),
            (0x30, "0A", None, "739891554", None),
            (0x30, "0A", "123456", "739891554", None),
            (0x30, "0A", "123456", None, None),
            (0x30, "0A", None, "739891554", None),
        ]
    ):
        assert cloud_write.await_args_list[index].args == args
    for call in cloud_write.await_args_list[:3]:
        assert call.kwargs["cmd_encoding"] == "hex"
    for call in cloud_write.await_args_list[3:6]:
        assert call.kwargs["cmd_encoding"] == "hex00"
    for call in cloud_write.await_args_list[6:]:
        assert call.kwargs["cmd_encoding"] == "rest_inline"

    await client.close()


@pytest.mark.asyncio
async def test_write_command_cloud_retries_target_hardness_without_ewuid() -> None:
    """Target hardness writes should also try cloud variants without ewuid."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "739891554",
                "ewuid": "aabbccddeeff",
                "data": [
                    {
                        "dt": "0x33",
                        "sn": "123456",
                        "ewuid": "aabbccddeeff",
                        "data": {},
                    }
                ],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        with patch.object(
            client._transport,
            "write_cloud_command",
            new=AsyncMock(return_value={"status": "ok"}),
        ) as cloud_write:
            result = await client.write_command(
                device_id="123456",
                command_id="30",
                value=10,
                transport=TransportMode.CLOUD,
            )

    assert result.status == "ok"
    assert result.transport == TransportMode.CLOUD
    assert result.command_id == 0x30
    assert cloud_write.await_count == 18
    for index, args in enumerate(
        [
            (0x30, "0A", "123456", "739891554", "aabbccddeeff"),
            (0x30, "0A", "123456", "739891554", None),
            (0x30, "0A", "123456", None, "aabbccddeeff"),
            (0x30, "0A", "123456", None, None),
            (0x30, "0A", None, "739891554", "aabbccddeeff"),
            (0x30, "0A", None, "739891554", None),
            (0x30, "0A", "123456", "739891554", "aabbccddeeff"),
            (0x30, "0A", "123456", "739891554", None),
            (0x30, "0A", "123456", None, "aabbccddeeff"),
            (0x30, "0A", "123456", None, None),
            (0x30, "0A", None, "739891554", "aabbccddeeff"),
            (0x30, "0A", None, "739891554", None),
            (0x30, "0A", "123456", "739891554", "aabbccddeeff"),
            (0x30, "0A", "123456", "739891554", None),
            (0x30, "0A", "123456", None, "aabbccddeeff"),
            (0x30, "0A", "123456", None, None),
            (0x30, "0A", None, "739891554", "aabbccddeeff"),
            (0x30, "0A", None, "739891554", None),
        ]
    ):
        assert cloud_write.await_args_list[index].args == args
    for call in cloud_write.await_args_list[:6]:
        assert call.kwargs["cmd_encoding"] == "hex"
    for call in cloud_write.await_args_list[6:12]:
        assert call.kwargs["cmd_encoding"] == "hex00"
    for call in cloud_write.await_args_list[12:]:
        assert call.kwargs["cmd_encoding"] == "rest_inline"

    await client.close()


@pytest.mark.asyncio
async def test_write_command_cloud_status_error_is_reported() -> None:
    """Semantic cloud write errors should not be treated as success."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": [{"dt": "0x33", "data": {}}],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        with patch.object(
            client._transport,
            "write_cloud_command",
            new=AsyncMock(return_value={"status": "error", "error": "write denied"}),
        ):
            result = await client.write_command(
                device_id="12345",
                command_id="30",
                value=10,
                transport=TransportMode.CLOUD,
            )

    assert result.status == "error"
    assert result.transport == TransportMode.CLOUD
    assert result.command_id == 0x30
    assert result.error == "write denied"

    await client.close()


@pytest.mark.asyncio
async def test_write_command_auto_falls_back_to_cloud_on_local_status_error() -> None:
    """AUTO writes should fall back to cloud when local write returns status error."""
    client = JudoClient(host="device.local")

    descriptor = DeviceDescriptor(
        device_id="12345",
        family=DeviceFamily.ISOFT,
        device_type="0x33",
        serial_number="12345",
        model="Judo i_soft",
    )

    with patch.object(
        client, "discover_devices", new=AsyncMock(return_value=[descriptor])
    ):
        with patch.object(
            client._transport,
            "write_local_command",
            new=AsyncMock(return_value={"status": "error", "error": "write denied"}),
        ) as local_write:
            with patch.object(
                client._transport,
                "write_cloud_command",
                new=AsyncMock(return_value={"status": "ok"}),
            ) as cloud_write:
                result = await client.write_command(
                    device_id="12345",
                    command_id="30",
                    value=10,
                    transport=TransportMode.AUTO,
                )

    assert result.status == "ok"
    assert result.transport == TransportMode.CLOUD
    assert result.command_id == 0x30
    local_write.assert_awaited_once()
    assert cloud_write.await_count == 9
    for index, args in enumerate(
        [
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
        ]
    ):
        assert cloud_write.await_args_list[index].args == args
    for call in cloud_write.await_args_list[:3]:
        assert call.kwargs["cmd_encoding"] == "hex"
    for call in cloud_write.await_args_list[3:6]:
        assert call.kwargs["cmd_encoding"] == "hex00"
    for call in cloud_write.await_args_list[6:]:
        assert call.kwargs["cmd_encoding"] == "rest_inline"

    await client.close()


@pytest.mark.asyncio
async def test_write_command_cloud_retries_with_decimal_cmd_on_indeterminate_ack() -> None:
    """Cloud write should retry with decimal cmd when ack has no status."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": [{"dt": "0x33", "data": {}}],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        with patch.object(
            client._transport,
            "write_cloud_command",
            new=AsyncMock(
                side_effect=[
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"value": None, "_source": "cloud"},
                    {"status": "ok"},
                    {"status": "ok"},
                    {"status": "ok"},
                ]
            ),
        ) as cloud_write:
            result = await client.write_command(
                device_id="12345",
                command_id="30",
                value=10,
                transport=TransportMode.CLOUD,
            )

    assert result.status == "ok"
    assert result.transport == TransportMode.CLOUD
    assert result.command_id == 0x30
    assert cloud_write.await_count == 12
    for call in cloud_write.await_args_list[:3]:
        assert call.kwargs["cmd_encoding"] == "hex"
    for call in cloud_write.await_args_list[3:6]:
        assert call.kwargs["cmd_encoding"] == "hex00"
    for call in cloud_write.await_args_list[6:9]:
        assert call.kwargs["cmd_encoding"] == "rest_inline"
    for call in cloud_write.await_args_list[9:]:
        assert call.kwargs["cmd_encoding"] == "dec"

    await client.close()


@pytest.mark.asyncio
async def test_write_command_cloud_does_not_retry_decimal_after_explicit_hex_success() -> None:
    """Explicit non-decimal success should not trigger an unnecessary decimal retry."""
    client = JudoClient(
        host="cloud.device",
        username="user",
        password="pass",
        force_cloud=True,
    )

    payload = {
        "status": "ok",
        "data": [
            {
                "serialnumber": "12345",
                "data": [{"dt": "0x33", "data": {}}],
            }
        ],
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        with patch.object(
            client._transport,
            "write_cloud_command",
            new=AsyncMock(return_value={"status": "ok"}),
        ) as cloud_write:
            result = await client.write_command(
                device_id="12345",
                command_id="30",
                value=10,
                transport=TransportMode.CLOUD,
            )

    assert result.status == "ok"
    assert result.transport == TransportMode.CLOUD
    assert result.command_id == 0x30
    assert cloud_write.await_count == 9
    for index, args in enumerate(
        [
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
            (0x30, "0A", "12345", "12345", None),
            (0x30, "0A", "12345", None, None),
            (0x30, "0A", None, "12345", None),
        ]
    ):
        assert cloud_write.await_args_list[index].args == args
    for call in cloud_write.await_args_list[:3]:
        assert call.kwargs["cmd_encoding"] == "hex"
    for call in cloud_write.await_args_list[3:6]:
        assert call.kwargs["cmd_encoding"] == "hex00"
    for call in cloud_write.await_args_list[6:]:
        assert call.kwargs["cmd_encoding"] == "rest_inline"

    await client.close()


@pytest.mark.asyncio
async def test_local_discovery_does_not_use_legacy_endpoint_fallback() -> None:
    """Local discovery should fail fast when /api/rest is unavailable."""
    client = JudoClient(host="device.local")

    with patch.object(
        client._transport,
        "read_local_command",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        with patch.object(
            client._transport,
            "request_local",
            new=AsyncMock(
                side_effect=AssertionError("legacy fallback must not be used")
            ),
        ):
            with pytest.raises(RuntimeError, match="/api/rest"):
                await client._discover_local_device()

    await client.close()


@pytest.mark.asyncio
async def test_read_snapshot_local_accepts_data_assignment_format() -> None:
    """Local data parsing should accept docs-style assignment responses."""
    client = JudoClient(host="device.local")

    command_map = {
        0xFF: {"raw_text": 'data="33"'},
        0x06: {"raw_text": "data=64d90100"},
        0x01: {"raw_text": "data=6b1502"},
        0x28: {"raw_text": "data=EC221000"},
        0x29: {"raw_text": "data=2EDC0000"},
        0x51: {"raw_text": 'data="0600"'},
        0x56: {"raw_text": "data=f6541100"},
    }

    async def _read_local(command_id: int) -> dict:
        if command_id in command_map:
            return command_map[command_id]
        raise JudoTransportError(f"unsupported command {command_id:02X}")

    with patch.object(
        client._transport, "read_local_command", new=AsyncMock(side_effect=_read_local)
    ):
        snapshot = await client.read_snapshot("121188")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["salt_weight_g"] == 21750
    assert fields["salt_level_pct"] == 43.5

    await client.close()


async def test_read_snapshot_real_isoft_safe_plus_cloud_payload() -> None:
    """Values verified against the Judo app for a real i-soft SAFE+ (0x33)."""
    client = JudoClient(
        host="cloud.device", username="user", password="pass", force_cloud=True
    )
    blob = (
        "0:00630F3840001000081212009402BB0000000000000059556A0515023000B400",
        "1:C000000010439E01091D7800B800000058003900000001006600910C2002D802",
        "2:003C78000000000047000000A00F840378000302A00F84030033AC0378000000",
    )
    payload = {
        "data": [
            {
                "serialnumber": "aabbccddeeff",
                "status": "online",
                "waterscene": "normal",
                "sv": "1.14",
                "waterscene_normal": 8,
                "hardness_shower": 4,
                "hardness_watering": 10,
                "hardness_heater": 1,
                "hardness_washing": 1,
                "data": [
                    {
                        "dt": "0x33",
                        "sv": "3.2n",
                        "hv": "5.10",
                        "data": {
                            "1": {"data": "6E0203", "st": "OK", "er": ""},
                            "3": {"data": "40E20100", "st": "OK", "er": ""},
                            "93": {"data": "02010B64AA10020011", "st": "OK", "er": ""},
                            "7": {"data": "630903000400", "st": "OK", "er": ""},
                            "8": {"data": "54300500", "st": "OK", "er": ""},
                            "9": {"data": "45160300", "st": "OK", "er": ""},
                            "94": {"data": "DE58E300", "st": "OK", "er": ""},
                            "790": {"data": blob[0], "st": "OK", "er": ""},
                            "791": {"data": blob[1], "st": "OK", "er": ""},
                            "792": {"data": blob[2], "st": "OK", "er": ""},
                        },
                    }
                ],
            }
        ]
    }

    with patch.object(
        client._transport, "read_cloud_device_data", new=AsyncMock(return_value=payload)
    ):
        snapshot = await client.read_snapshot("aabbccddeeff")

    fields = {field.key: field.value for field in snapshot.fields}
    assert fields["water_total_m3"] == 340.052  # app: 340.1 m³
    assert fields["cloud_node_id"] == 123456  # app: Gerätenummer 123456
    assert fields["firmware_version"] == "3.02n"  # app: 3.02
    assert fields["maintenance_days_remaining"] == 100  # app: 100 Tage
    assert fields["emergency_power_module"] is True  # app: Notstrommodul ja
    assert snapshot.device.model == "Judo i-soft SAFE+"
    assert fields["target_hardness"] == 8.0  # app: 8 °dH
    assert fields["regeneration_count"] == 728  # app: 728
    assert fields["maintenance_count"] == 3  # app: 3
    assert fields["salt_days_remaining"] == 227  # app: 32 weeks
    assert fields["salt_level_pct"] == 45.5  # app: ~50 %
    assert fields["battery_capacity_pct"] == 100  # app: 100 %
    assert fields["battery_runtime_min"] == 2  # app: 2 min
    assert fields["water_scene"] == "normal"  # app: Normal
    assert fields["connectivity_module_version"] == "1.14"  # app: 1.14
    assert fields["leakage_max_duration_min"] == 120  # app: 2 h
    assert fields["leakage_max_volume_l"] == 900  # app: 900 l
    assert fields["leakage_max_flow_lph"] == 4000  # app: 4000 l/h
    assert fields["vacation_mode_type"] == "U1"  # app: Urlaubsmodus 1
    assert fields["sleep_mode_duration_h"] == 2  # app: 2 h
    assert fields["vacation_mode_active"] is False
    assert fields["device_online"] is True
    assert fields["water_scene_shower_hardness"] == 4.0
    assert fields["water_scene_garden_hardness"] == 10.0
    assert fields["water_scene_heater_hardness"] == 1.0
    assert fields["water_scene_washing_hardness"] == 1.0

    await client.close()
