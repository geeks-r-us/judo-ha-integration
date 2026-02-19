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
| `sensor`        | Water hardness, consumption, salt level, flow rate, etc. |
| `binary_sensor` | System status, alarms, maintenance alerts                |

## Features

- Monitor water treatment system status
- Track water consumption and treatment statistics
- Real-time system monitoring and alerts
- Configuration through Home Assistant UI

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
2. Restart Home Assistant
3. Go to Configuration → Integrations
4. Click "+" and search for "Judo iSoft"
5. Follow the configuration steps

### HACS Installation

This integration can be installed through HACS (Home Assistant Community Store):

1. Add this repository to HACS as a custom repository
2. Search for "Judo iSoft" in HACS
3. Install the integration
4. Restart Home Assistant
5. Configure through Configuration → Integrations

## Configuration

The integration requires:
- Judo iSoft system IP address
- API credentials (if applicable)
- Polling interval (default: 60 seconds)

## Supported Entities

### Sensors
- Water hardness
- Water consumption
- System status
- Filter status
- Salt level
- Error codes

### Binary Sensors
- System online status
- Alarm status
- Maintenance required

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
