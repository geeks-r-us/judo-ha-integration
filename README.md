# Judo iSoft Water Treatment Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

A Home Assistant custom integration for Judo iSoft water treatment systems.

**This component will set up the following platforms.**

| Platform        | Description                                               |
| --------------- | --------------------------------------------------------- |
| `sensor`        | Consumption, hardness, salt, service and leakage settings |
| `binary_sensor` | Online, vacation mode, emergency power module, flags      |
| `button`        | Explicit and capability-generated command actions         |
| `number`        | Writable target hardness                                  |
| `select`        | Writable hardness unit                                    |

## Features

- Monitor water consumption, salt, service intervals and leakage protection settings
- Energy dashboard ready: total water sensor with the `water` device class
- Local REST or myJUDO cloud connection
- Requires Home Assistant 2024.11.0 or newer
- Configuration through Home Assistant UI
- Internal `judo_client` stack with command-level decoding
- Shared protocol command catalog with family composition blocks and overrides
- Dynamic entities generated from decoded command fields
- Generic service `judo_isoft.execute_command` for protocol read/write operations
- Capability metadata (`payload_length`, `default_write_value`) for safe write UX
- Generated command buttons for writable commands with safe payload behavior

## Installation

### 🐳 Development with Devcontainer (Recommended)

Get started instantly with a complete Home Assistant development environment:

```bash
git clone https://github.com/your-username/judo-ha-integration.git
cd judo-ha-integration
code .  # VS Code will prompt to open in devcontainer
```

**Features:**
- ✅ Complete Home Assistant instance
- ✅ Mock Judo iSoft device for testing
- ✅ Pre-configured development tools
- ✅ Hot reloading and debugging
- ✅ Access HA at http://localhost:8123

📖 **[Full Devcontainer Guide](docs/DEVCONTAINER.md)**

### Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`)
2. If you do not have a `custom_components` directory (folder) there, you need to create it
3. In the `custom_components` directory (folder) create a new folder called `judo_isoft`
4. Download _all_ the files from the `custom_components/judo_isoft/` directory (folder) in this repository
5. Place the files you downloaded in the new directory (folder) you created
6. Restart Home Assistant
7. Go to Settings → Devices & services → Add integration
8. Search for "Judo iSoft"
9. Follow the configuration steps

### HACS Installation

This integration can be installed through HACS (Home Assistant Community Store):

1. Add this repository to HACS as a custom repository
2. Search for "Judo iSoft" in HACS
3. Install the integration
4. Restart Home Assistant
5. Configure through Configuration → Integrations

## Configuration

1. Settings → Devices & services → Add integration → "Judo iSoft"
2. **Cloud (default for the eWAC connectivity module):** leave host empty or `cloud.device`, enter your myJUDO user name and password
3. **Local:** IP address and port of a device that exposes the `/api/rest` interface
4. Polling interval is configurable in the integration options (30-300 s, default 60 s)

## Supported Entities

### Sensors

Created dynamically from the decoded device data, so the exact list depends on the model and
connection. For an i-soft SAFE+ via the cloud you get, for example:

| Group | Sensors |
| --- | --- |
| Water | Total water (L and m³), soft water (L and m³). The litre sensors have the `water` device class and can be used in the Energy dashboard. |
| Hardness | Target hardness, hardness per water scene (shower, garden, heating fill, washing, normal), active water scene |
| Salt | Salt weight (g/kg), salt range (days), estimated salt level (%) |
| Service | Regeneration count, maintenance count, days/hours until next maintenance |
| Leakage protection | Max. draw duration (min), max. draw volume (L), max. flow (L/h), vacation mode type, sleep mode duration (h) |
| Device | Firmware, device number, connectivity module version, battery capacity (%), battery runtime (min) |

There is **no live flow rate, pressure or temperature**: the i-soft does not report them.
For a flow estimate create a *Derivative* helper on the total water sensor.

### Binary Sensors

- **Online** - device reachable (cloud status, or successful local read); off when an update fails
- **Vacation mode active**
- **Emergency power module** - present
- Alarm / maintenance / regeneration flags where the device reports them

### Number, Select, Button

- **Target hardness** (number), **hardness unit** (select)
- Buttons for writable commands, e.g. start regeneration

### Services

`judo_isoft.execute_command` - read or write any protocol command (`command`, optional `value`, `device_id`, `transport`).

> Some values are inferred from a single device and are not covered by the official command list.
> See [docs/VERIFICATION.md](docs/VERIFICATION.md) for what is confirmed against the Judo app.

### Water consumption per day

Add a *Utility Meter* helper (Settings → Devices & services → Helpers) with the total water sensor
as source and a daily cycle. For the Energy dashboard use the total water (L) sensor directly.

## Development

### Setup Development Environment

```bash
git clone https://github.com/your-username/judo-ha-integration.git
cd judo-ha-integration
pip install -r requirements-dev.txt
```

### Running Tests

```bash
python -m pytest tests/
```

## Contributing

Contributions are welcome! Please read the contributing guidelines and submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, please use the GitHub issue tracker.

<!---->

[commits-shield]: https://img.shields.io/github/commit-activity/y/geeks-r-us/judo-ha-integration.svg?style=for-the-badge
[commits]: https://github.com/geeks-r-us/judo-ha-integration/commits/main
[hacs]: https://hacs.xyz
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/geeks-r-us/judo-ha-integration.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-geeks--r--us-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/geeks-r-us/judo-ha-integration.svg?style=for-the-badge
[releases]: https://github.com/geeks-r-us/judo-ha-integration/releases
[user_profile]: https://github.com/geeks-r-us
