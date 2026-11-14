# Judo Client Architecture

This integration now includes an internal package under `custom_components/judo_isoft/judo_client/`.

## Goals

- Separate transport/auth/protocol decoding from Home Assistant entity code.
- Provide registry-based command decoding for multiple Judo product families.
- Support generic command execution via `judo_isoft.execute_command`.
- Keep a single internal stack based on command transport.

## Modules

- `judo_client/client.py`: high-level client (`discover_devices`, `read_snapshot`, `read_command`, `write_command`).
- `judo_client/transport.py`: local `/api/rest` and cloud interface transport.
- `judo_client/auth.py`: cloud token authentication.
- `judo_client/protocol/codec_primitives.py`: shared encode/decode primitives.
- `judo_client/protocol/catalog.py`: command catalog and device-family mapping.
- `judo_client/protocol/decoder.py`: registry engine with command normalization.
- `judo_client/protocol/families/common.py`: shared command blocks + composition helpers.
- `judo_client/protocol/families/*.py`: family-level command specs composed from shared blocks + overrides.
- `judo_client/ha_mapping.py`: decoded-field to HA metadata helpers.
- `command_helpers.py`: shared HA-side command normalization and capability filtering.
- `entity_base.py`: shared coordinator entity base for writable command entities.

## Supported Families in Catalog

- i-soft
- SOFTwell
- i-fill
- i-safe
- i-dos

## Runtime Model

- Integration always uses the internal `judo_client` stack.
- Local communication uses command endpoint `/api/rest`.
- Cloud communication uses the Judo interface command transport.
- Entities are generated dynamically from decoded fields.
- Writable command entities combine explicit controls with capability-driven generated buttons.

## Capability Metadata

Capabilities now include:

- `command_id`
- `name`
- `direction`
- `unit`
- `payload_length`
- `default_write_value`

This metadata is sourced from protocol `CommandSpec` entries and is used by HA platforms to:

- keep explicit controls canonical (`number`/`select`/explicit `button`)
- generate additional safe command buttons when capability metadata allows it
- keep value-bearing commands without safe defaults in the `execute_command` service path

## Generic Command Service

Service: `judo_isoft.execute_command`

Fields:

- `device_id` (optional)
- `command` (int or hex string)
- `value` (optional; required for writes)
- `transport` (`auto`, `local`, `cloud`)

## Generated Command Buttons

- Generated only from discovered writable capabilities (strict capability-driven behavior).
- Generated when either:
  - `payload_length == 0`, or
  - `default_write_value` is defined in protocol metadata.
- Explicit entities always win for overlapping command ids.
- Commands without safe default values remain available through `judo_isoft.execute_command`.
