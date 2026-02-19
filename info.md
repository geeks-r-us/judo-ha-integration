# Judo iSoft Water Treatment Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

_Integration to integrate with [Judo iSoft][judo_isoft] water treatment systems._

**This integration will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show info from Judo iSoft water treatment system (water hardness, consumption, salt level, flow rate, system pressure, filter status).
`binary_sensor` | Show status from Judo iSoft water treatment system (online, alarm, maintenance required, regeneration active).

## Features

- **Real-time monitoring** of your Judo iSoft water treatment system
- **Water quality sensors** - hardness, consumption, flow rate, pressure
- **System status indicators** - online status, alarms, maintenance alerts
- **Salt and filter monitoring** - track salt levels and filter replacement needs
- **Regeneration cycle tracking** - monitor when the system is regenerating
- **Easy configuration** through the Home Assistant UI
- **Local polling** - no cloud dependency, works entirely local

## Installation

### HACS (Recommended)

1. In the HACS UI, click on "Integrations"
2. Click the "+" button in the bottom right corner
3. Search for "Judo iSoft Water Treatment"
4. Install the integration
5. Restart Home Assistant

### Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`)
2. If you do not have a `custom_components` directory (folder) there, you need to create it
3. In the `custom_components` directory (folder) create a new folder called `judo_isoft`
4. Download _all_ the files from the `custom_components/judo_isoft/` directory (folder) in this repository
5. Place the files you downloaded in the new directory (folder) you created
6. Restart Home Assistant

## Configuration

1. In the Home Assistant UI go to "Configuration" -> "Integrations"
2. Click the "+" button and search for "Judo iSoft Water Treatment"
3. Enter the IP address of your Judo iSoft system
4. Configure the polling interval (optional, defaults to 60 seconds)
5. Click "Submit"

## Entities

### Sensors

- **Water Hardness** - Current water hardness in °dH
- **Water Consumption** - Total water consumption in liters
- **Salt Level** - Current salt level in %
- **Flow Rate** - Current water flow rate in L/min
- **System Pressure** - Current system pressure in bar
- **Filter Remaining** - Days until filter replacement needed

### Binary Sensors

- **Online** - System connectivity status
- **Alarm** - System alarm status
- **Maintenance Required** - Maintenance alert status
- **Regeneration Active** - Regeneration cycle status

## Automation Examples

### Low Salt Alert
```yaml
automation:
  - alias: "Low Salt Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.judo_isoft_salt_level
        below: 20
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Judo iSoft - Low Salt"
          message: "Salt level is {{ states('sensor.judo_isoft_salt_level') }}%. Please refill."
```

### Maintenance Required
```yaml
automation:
  - alias: "Maintenance Required"
    trigger:
      - platform: state
        entity_id: binary_sensor.judo_isoft_maintenance_required
        to: "on"
    action:
      - service: persistent_notification.create
        data:
          title: "Judo iSoft Maintenance"
          message: "Your water treatment system requires maintenance."
```

## Support

For issues and feature requests, please use the [GitHub issue tracker][issues].

## Contributing

Contributions are welcome! Please read the [contributing guidelines][contributing] before submitting pull requests.

[commits-shield]: https://img.shields.io/github/commit-activity/y/geeks-r-us/judo-ha-integration.svg?style=for-the-badge
[commits]: https://github.com/geeks-r-us/judo-ha-integration/commits/main
[license]: https://github.com/geeks-r-us/judo-ha-integration/blob/main/LICENSE
[license-shield]: https://img.shields.io/github/license/geeks-r-us/judo-ha-integration.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/geeks-r-us/judo-ha-integration.svg?style=for-the-badge
[releases]: https://github.com/geeks-r-us/judo-ha-integration/releases
[judo_isoft]: https://www.judo.eu/
[issues]: https://github.com/geeks-r-us/judo-ha-integration/issues
[contributing]: https://github.com/geeks-r-us/judo-ha-integration/blob/main/CONTRIBUTING.md