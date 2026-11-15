# Judo iSoft Water Treatment Integration

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

_Integration to integrate with [Judo iSoft][judo_isoft] water treatment systems._

**This integration will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Water consumption, hardness (per water scene), salt, service and leakage protection settings, device info.
`binary_sensor` | Online, vacation mode active, emergency power module, device flags.
`number` / `select` / `button` | Target hardness, hardness unit, command buttons.

## Features

- **Monitoring** of your Judo iSoft water treatment system: consumption, salt, service intervals, leakage protection settings
- **Water scenes** - hardness per scene and the active scene
- **Energy dashboard ready** - total water sensor with the `water` device class
- **Easy configuration** through the Home Assistant UI
- **Local or cloud** - local REST if your device supports it, otherwise the myJUDO cloud account

Requires Home Assistant **2024.11.0** or newer.

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

1. Go to Settings → Devices & services → Add integration
2. Search for "Judo iSoft Water Treatment"
3. **Cloud:** leave host empty (or `cloud.device`) and enter your myJUDO user name and password
   **Local:** enter the IP address and port of the device (needs a module with the local `/api/rest` interface)
4. Optional: set the polling interval in the integration options (30-300 s, default 60 s)

> The eWAC connectivity module with firmware 1.14 has no local REST interface; use the cloud mode there.

## Entities

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
| Messages | Last message (text), last message time, number of unconfirmed messages (cloud only) |

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

### Events

New device messages (cloud only) fire the event `judo_isoft_message` with `message_id`, `type`
(`w` notice, `e` error), `code`, `text`, `timestamp`, `confirmed` and `param`. The messages that
already exist when Home Assistant starts are not replayed.

```yaml
trigger:
  - platform: event
    event_type: judo_isoft_message
    event_data:
      code: 27   # maintenance due
```

### Services

`judo_isoft.execute_command` - read or write any protocol command (`command`, optional `value`, `device_id`, `transport`).

> Some values are inferred from a single device and are not covered by the official command list.
> See [docs/VERIFICATION.md](docs/VERIFICATION.md) for what is confirmed against the Judo app.

### Water consumption per day

Add a *Utility Meter* helper (Settings → Devices & services → Helpers) with the total water sensor
as source and a daily cycle. For the Energy dashboard use the total water (L) sensor directly.

## Automation Examples

Entity IDs depend on the device name; pick yours in the automation editor.

### Low Salt Alert
```yaml
automation:
  - alias: "Low Salt Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.judo_wasseraufbereitung_gmbh_judo_i_soft_salt_level_estimated
        below: 20
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "Judo iSoft - Low Salt"
          message: "Salt level is {{ states('sensor.judo_wasseraufbereitung_gmbh_judo_i_soft_salt_level_estimated') }}%. Please refill."
```

### Maintenance Due
```yaml
automation:
  - alias: "Maintenance Due"
    trigger:
      - platform: numeric_state
        entity_id: sensor.judo_wasseraufbereitung_gmbh_judo_i_soft_safe_maintenance_days_remaining
        below: 30
    action:
      - service: persistent_notification.create
        data:
          title: "Judo iSoft Maintenance"
          message: "Next maintenance in {{ states('sensor.judo_wasseraufbereitung_gmbh_judo_i_soft_safe_maintenance_days_remaining') }} days."
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