# SVK Heatpump Development Environment Setup

This guide provides step-by-step instructions for running the development container and accessing the Home Assistant solution with the SVK Heatpump component.

## Prerequisites

- Docker and Docker Compose installed
- Git for cloning the repository
- A web browser (Chrome, Firefox, Safari, or Edge)

## Step 1: Clone the Repository (if not already done)

```bash
git clone <repository-url>
cd SVK
```

## Step 2: Build and Start the Development Container

The project includes a dev container configuration for Home Assistant development.

```bash
# Build and start the dev container
docker-compose -f .devcontainer/docker-compose.yml up --build
```

Alternatively, if you're using VS Code with the Remote - Containers extension:

1. Open the project in VS Code
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Select "Remote-Containers: Reopen in Container"
4. Wait for the container to build and start

## Step 3: Start Home Assistant

Once the container is running, start Home Assistant with the following commands:

```bash
# Navigate to the config directory
cd config

# Start Home Assistant
hass --config . --debug
```

Alternatively, you can use the provided script:

```bash
./start_home_assistant.sh
```

## Step 4: Access Home Assistant Web Interface

1. Open your web browser
2. Navigate to `http://localhost:8123`
3. You'll see the Home Assistant setup screen

## Step 5: Configure Home Assistant

1. Create your Home Assistant user account
2. Set a name for your home
3. Skip the "Discover devices" step for now
4. Complete the initial setup

## Step 6: Add the SVK Heatpump Integration

1. In Home Assistant, click on "Settings" in the sidebar
2. Select "Devices & Services"
3. Click the "+ Add Integration" button
4. Search for "SVK Heatpump" or scroll to find it in the list
5. Click on the SVK Heatpump integration
6. Configure the integration with your heat pump details:
   - Host/IP address of your heat pump
   - Username and password for authentication
   - Optional: Enable write access (default: disabled)
   - Optional: Set fetch interval (default: 30 seconds)
7. Click "Submit" to add the integration

## Step 7: Verify the Component is Working

### Check Integration Status

1. Go to "Settings" > "Devices & Services"
2. Look for the SVK Heatpump integration in the list
3. Ensure it shows as "Configured" and "Available"

### View Sensor Data

1. Go to "Developer Tools" > "States"
2. Filter by "svk_heatpump" to see all entities
3. Verify that sensors are showing data from your heat pump

### Check Logs for Errors

1. Go to "Settings" > "System"
2. Click on "Logs"
3. Look for any errors related to "svk_heatpump"

### Test the Service

1. Go to "Developer Tools" > "Services"
2. Select "svk_heatpump.set_value" from the dropdown
3. Use the service to test write operations (if write access is enabled):
   ```yaml
   entity_id: sensor.svk_heatpump_<host>_<sensor_name>
   value: new_value
   ```
4. Click "Call Service" to execute

## Step 8: Access the Solution Website

Once Home Assistant is running with the SVK Heatpump integration:

1. The main interface is accessible at `http://localhost:8123`
2. You can create dashboards to display heat pump data:
   - Go to "Overview" to view the default dashboard
   - Click "Edit Dashboard" to add SVK Heatpump entities
   - Create cards for temperature sensors, status indicators, etc.

## Troubleshooting

### Container Won't Start

```bash
# Check container logs
docker-compose -f .devcontainer/docker-compose.yml logs

# Rebuild the container
docker-compose -f .devcontainer/docker-compose.yml up --build --force-recreate
```

### Integration Not Found

1. Verify the custom component is in the correct location:
   - Should be at `config/custom_components/svk_heatpump/`
2. Check Home Assistant logs for import errors
3. Restart Home Assistant after making changes

### Connection Issues

1. Verify the heat pump's IP address is accessible from the container
2. Check credentials are correct
3. Ensure the heat pump's web interface is accessible

### Performance Issues

1. Adjust the fetch interval in the integration settings
2. Disable unused sensors in the catalog.yaml file
3. Check network connectivity to the heat pump

## Development Tips

### Making Changes to the Component

1. Edit the files in `custom_components/svk_heatpump/`
2. Restart Home Assistant to apply changes:
   - In Developer Tools, go to "Configuration" > "Server Controls"
   - Click "Restart"

### Debug Mode

To run Home Assistant with debug output:

```bash
hass --config . --debug --log-file debug.log
```

### Testing Configuration Changes

1. Make changes to configuration files
2. Check configuration validity:
   ```bash
   hass --script check_config --config .
   ```
3. Restart Home Assistant if configuration is valid

## Additional Resources

- Home Assistant Documentation: https://developers.home-assistant.io/
- SVK Heatpump Component Documentation: See project README.md
- For issues, check the logs or create an issue in the project repository