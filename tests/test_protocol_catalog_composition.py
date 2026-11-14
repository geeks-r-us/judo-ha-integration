"""Tests for family catalog composition with shared command blocks."""

from __future__ import annotations

import pytest

from custom_components.judo_isoft.judo_client.models import CommandDirection
from custom_components.judo_isoft.judo_client.protocol.families import (
    get_idos_specs,
    get_ifill_specs,
    get_isafe_specs,
    get_isoft_specs,
    get_softwell_specs,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations():
    """Override global autouse fixture for pure unit tests."""
    yield


def _by_command_id(specs):
    return {spec.command_id: spec for spec in specs}


def test_each_family_spec_list_has_unique_command_ids() -> None:
    """Composed family specs should not emit duplicate command ids."""
    for get_specs in (
        get_isoft_specs,
        get_softwell_specs,
        get_isafe_specs,
        get_ifill_specs,
        get_idos_specs,
    ):
        specs = get_specs()
        command_ids = [spec.command_id for spec in specs]
        assert len(command_ids) == len(set(command_ids))


def test_isoft_overrides_keep_decoders_and_defaults() -> None:
    """i-soft shared specs should preserve decoder overrides/default values."""
    by_id = _by_command_id(get_isoft_specs())
    assert by_id[0x01].decoder is not None
    assert by_id[0x28].decoder is not None
    assert by_id[0x29].decoder is not None
    assert by_id[0x35].default_write_value == 0
    assert by_id[0x36].direction == CommandDirection.WRITE
    assert by_id[0x37].direction == CommandDirection.READ_WRITE
    assert by_id[0x38].direction == CommandDirection.WRITE
    assert by_id[0x3E].direction == CommandDirection.READ_WRITE
    assert by_id[0x3F].direction == CommandDirection.READ_WRITE
    assert by_id[0x40].direction == CommandDirection.READ_WRITE


def test_other_families_keep_expected_direction_and_metadata() -> None:
    """Composed specs for remaining families should keep key command semantics."""
    softwell = _by_command_id(get_softwell_specs())
    assert softwell[0x29].decoder is not None
    assert softwell[0x35].default_write_value == 0
    assert softwell[0x30].direction == CommandDirection.WRITE

    isafe = _by_command_id(get_isafe_specs())
    assert isafe[0x28].decoder is not None
    assert isafe[0x3E].direction == CommandDirection.WRITE
    assert isafe[0x3F].direction == CommandDirection.WRITE
    assert isafe[0x40].direction == CommandDirection.WRITE

    ifill = _by_command_id(get_ifill_specs())
    assert ifill[0x28].decoder is not None
    assert ifill[0x51].direction == CommandDirection.WRITE
    assert ifill[0x52].direction == CommandDirection.WRITE

    idos = _by_command_id(get_idos_specs())
    assert idos[0x43].decoder is not None
    assert idos[0x52].default_write_value == "0002"
    assert idos[0x52].direction == CommandDirection.WRITE
