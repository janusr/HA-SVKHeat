# SVK Heatpump

![SVK Heatpump Logo](custom_components/svk_heatpump/logo.png)

Home Assistant custom component for SVK Heatpump monitoring and control.

## Features

- Monitor SVK heat pump status and sensors
- Control heat pump settings (when write access is enabled)
- Real-time data updates with configurable polling intervals
- Full Home Assistant integration with configuration flow

## Installation

This custom component can be installed via HACS (Home Assistant Community Store) or manually.

### HACS Installation

1. Add this repository to HACS as a custom repository
2. Install the integration through HACS
3. Restart Home Assistant
4. Add the integration through Settings -> Integrations

### Manual Installation

1. Copy the `custom_components/svk_heatpump` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration through Settings -> Integrations

## Configuration

The integration requires the following configuration during initial setup:

- **Host/IP**: The IP address or hostname of your SVK heat pump
- **Username**: Username for accessing the heat pump
- **Password**: Password for accessing the heat pump
- **Write Access**: Enable if you want to allow control of the heat pump (default: disabled)
- **Fetch Interval**: Polling interval in seconds (default: 30 seconds)

Additional advanced options are available after setup through the Configure button:
- **Chunk Size** (5-100): Number of entities to fetch in each API request (default: 25)
- **API Mode** ("json" or "html"): Communication protocol to use (default: "json")
- **Request Timeout** (5-60 seconds): Maximum time to wait for API responses (default: 30)

## Change settings after setup

After the initial setup, you can modify the integration settings through two different methods:

### Configure (Options)

Use the **Configure** button to modify tunable parameters without re-entering credentials:

1. Go to **Settings → Integrations → SVK Heatpump**
2. Click the **Configure** button (three dots menu)
3. Adjust the desired options
4. Click **Submit** to save changes

The following settings can be changed through the Configure option:

- **Scan Interval** (seconds): How often to fetch data from the heat pump (default: 30)
- **Enable Writes**: Allow control of the heat pump (default: False)
- **Chunk Size** (5-100): Number of entities to fetch in each API request (default: 25)
- **API Mode** ("json" or "html"): Communication protocol to use (default: "json")
- **Request Timeout** (5-60 seconds): Maximum time to wait for API responses (default: 30)

![Configure Options](images/configure-options.png)
*Configure options dialog showing tunable parameters*

### Reconfigure

Use the **Reconfigure** button to update connection settings:

1. Go to **Settings → Integrations → SVK Heatpump**
2. Click the **Reconfigure** button (three dots menu)
3. Update your connection details:
   - Host/IP address
   - Username
   - Password
4. Click **Submit** to save changes

The reconfigure option is useful when:
- Your heat pump's IP address changes
- You need to update credentials
- Moving to a different heat pump unit

![Reconfigure Dialog](images/reconfigure-dialog.png)
*Reconfigure dialog showing connection settings*

### Backward Compatibility

All existing installations will continue to work with their current settings. The new options use sensible defaults that match the previous behavior:

- Existing integrations will maintain their current scan interval and write access settings
- New tunable options (chunk_size, api_mode, request_timeout) will use default values
- No manual intervention is required for existing installations

## Changelog

### Version 0.5.0

- **NEW**: Options Flow for post-setup configuration changes
- **NEW**: Reconfigure flow for updating connection settings
- **NEW**: Advanced tunable parameters:
  - Chunk size control (5-100 entities per request)
  - API mode selection (JSON or HTML)
  - Request timeout configuration (5-60 seconds)
- **IMPROVED**: Better separation between initial setup and runtime configuration
- **IMPROVED**: Backward compatibility maintained for existing installations

## Requirements

- Home Assistant 2023.1 or newer
- Python 3.12 or newer
- httpx>=0.27.0

## License

MIT License

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the documentation at https://github.com/your-repo/svk-heatpump