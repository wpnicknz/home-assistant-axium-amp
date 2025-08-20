# Home Assistant Axium Amp Integration

This is a custom integration for controlling Axium multi-room amplifiers from Home Assistant over the Axium built-in HTTP/CGI web app. For more information about Axium amplifiers, please visit https://www.axium.co.nz/.
**Note:** This integration is **community developed** and is **not affiliated with, endorsed by, or supported by Axium**.  Please do not contact Axium for support related to this software.


## Features
- Power control (on/off per zone)
- Volume control with normalization
- Source selection with friendly names
- Media Card support
- Zone name discovery via Axium HTTP
- Long-polling for real-time updates

## Installation

### HACS (recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations** → click the three dots (⋮) → **Custom repositories**.
3. Add this repo URL:  
   `https://github.com/wpnicknz/home-assistant-axium-amp`  
   Category: **Integration**.
4. Search for **Axium Amp** in HACS and install.
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
