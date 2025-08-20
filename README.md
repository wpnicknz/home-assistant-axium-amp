# Home Assistant Axium Amp Integration

This is a custom integration for controlling Axium multi-room amplifiers from Home Assistant.

## Features
- Power control (on/off per zone)
- Volume control with normalization
- Source selection with friendly names
- Media Card support
- Zone name discovery via Axium HTTP
- Long-polling for near real-time updates

## Installation
1. Copy the `custom_components/axium` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration through the UI (Configuration → Devices & Services → Add Integration → Axium).

## Configuration
1. Enter the IP Address of the Axium Amp
After setup, each zone will appear as a Media Player entity in Home Assistant.

## Notes
- Requires network access to your Axium amplifier.
- Tested on model Axium AX-800DAV only.
