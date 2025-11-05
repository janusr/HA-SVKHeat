# SVK Heatpump

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

The integration requires the following configuration:

- **Host/IP**: The IP address or hostname of your SVK heat pump
- **Username**: Username for accessing the heat pump
- **Password**: Password for accessing the heat pump
- **Write Access**: Enable if you want to allow control of the heat pump (default: disabled)
- **Fetch Interval**: Polling interval in seconds (default: 30 seconds)

## Requirements

- Home Assistant 2023.1 or newer
- Python 3.12 or newer
- httpx>=0.27.0

## Development

This project uses a development container with all necessary tools pre-configured. See `.devcontainer/devcontainer.json` for details.

### Development Setup

1. Clone this repository
2. Open in VS Code with the Dev Containers extension
3. The container will be built automatically with all dependencies

### Testing

Run tests with:
```bash
pytest
```

### Code Quality

Code formatting and linting tools are configured:
- Black for code formatting
- Ruff for linting
- MyPy for type checking

## License

MIT License

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check the documentation at https://github.com/your-repo/svk-heatpump