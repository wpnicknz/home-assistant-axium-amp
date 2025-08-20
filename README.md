# Home Assistant Axium Amp Integration

This is a custom integration for controlling Axium multi-room amplifiers from Home Assistant using the Axium built-in web app, requiring only a network connection rather than direct serial. For more information about Axium amplifiers, please visit https://www.axium.co.nz/.

## Features
- Power control (on/off per zone)
- Volume control with normalization
- Source selection
- Sets up a Media Player for each zone
- Zone and source name discovery
- Real-time updates

## Installation

### HACS (recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations** → click the three dots (⋮) → **Custom repositories**.
3. Add this repo URL:  
   `https://github.com/wpnicknz/home-assistant-axium-amp`  
   Category: **Integration**.
4. In HACS search for **Axium Amp** and install.
5. Restart Home Assistant.

### Manual
1. Copy the `custom_components/axium` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration
1. Enter the IP Address of the Axium Amp
After setup, each zone will appear as a Media Player entity in Home Assistant.

## Notes
- Requires network access to your Axium amplifier.
- Tested on model Axium AX-800DAV only.
- Extended control such Bass, Treble, Power on volume is not provided
- This integration is community developed and is not affiliated with, endorsed by, or supported by Axium.  Please do not contact Axium for support related to this software.
