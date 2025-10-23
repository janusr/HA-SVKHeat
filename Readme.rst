SVK Heat Pump Integration for Home Assistant
============================================

.. image:: custom_components/svk_heatpump/logo.png
    :alt: SVK Heat Pump Logo
    :align: center

A custom Home Assistant integration for SVK heat pumps with LMC320 controllers, providing comprehensive monitoring and control capabilities through the local JSON API.

Features
--------

* **Real-time Monitoring**: Access to over 100 different parameters from your heat pump
* **Temperature Sensors**: Monitor all temperature points including supply, return, tank, ambient, and solar temperatures
* **Performance Metrics**: Track compressor speed, capacity, and runtime statistics
* **System Status**: Monitor heat pump state, alarms, and system health
* **Control Capabilities**: Adjust setpoints and operating modes (optional)
* **Solar Panel Support**: Monitor solar heating system integration
* **Diagnostics**: Comprehensive diagnostic information and troubleshooting tools
* **Local Polling**: No cloud dependencies - operates entirely on your local network

Supported Devices
-----------------

* SVK heat pumps with LMC320 controller
* Devices with firmware supporting the JSON API
* Compatible with both Digest and Basic authentication

Installation
------------

HACS Installation (Recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open HACS in Home Assistant
2. Go to Integrations
3. Click the three dots menu and select "Custom repositories"
4. Add the repository URL for this integration
5. Search for "SVK Heatpump" and install it
6. Restart Home Assistant
7. Follow the configuration steps below

Manual Installation
~~~~~~~~~~~~~~~~~~~

1. Download the latest release from the repository
2. Copy the `custom_components/svk_heatpump` directory to your Home Assistant `config/custom_components` directory
3. Restart Home Assistant
4. Follow the configuration steps below

Configuration
-------------

Adding the Integration
~~~~~~~~~~~~~~~~~~~~~~

1. In Home Assistant, go to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "SVK Heatpump" and select it
4. Enter the required information:

   * **Host**: IP address of your heat pump controller (e.g., 192.168.1.100)
   * **Username**: Controller username (default: admin)
   * **Password**: Controller password
   * **Allow Basic Auth (Legacy)**: Enable only if your device doesn't support Digest authentication
   * **ID List**: Custom list of entity IDs to monitor (optional, uses comprehensive default if empty)

5. Click **Submit** and wait for the connection to be validated
6. If successful, the integration will be added to your Home Assistant

Configuration Options
~~~~~~~~~~~~~~~~~~~~~

After adding the integration, you can configure additional options:

* **Scan Interval**: Data refresh interval in seconds (10-120, default: 30)
* **Enable Solar**: Include solar panel entities (default: enabled)
* **Enable Counters**: Include runtime counters and statistics (default: enabled)
* **Enable Writes**: Allow control of setpoints and modes (default: disabled)

.. note::
   The **Enable Writes** option allows you to control your heat pump from Home Assistant.
   Enable this only if you understand the implications of remote control.

Available Entities
------------------

Temperature Sensors
~~~~~~~~~~~~~~~~~~~

* Heating Supply Temp: Current temperature of the heating circuit supply
* Heating Return Temp: Current temperature of the heating circuit return
* Water Tank Temp: Current temperature of the domestic hot water tank
* Ambient Temp: Outdoor temperature measured by the heat pump
* Room Temp: Indoor temperature measured by the heat pump
* Heating Tank Temp: Temperature of the heating buffer tank
* Cold Side Supply Temp: Temperature on the cold side of the heat exchanger
* Cold Side Return Temp: Return temperature on the cold side
* Evaporator Temp: Temperature of the evaporator
* Solar Collector Temp: Temperature of the solar collector
* Solar Water Temp: Temperature of the solar water circuit

Performance Sensors
~~~~~~~~~~~~~~~~~~~

* Compressor Speed: Current compressor speed (V or %)
* Requested Capacity: Percentage of heating capacity requested
* Actual Capacity: Percentage of heating capacity actually delivered
* Cold Pump Speed: Speed of the cold side pump

System Status
~~~~~~~~~~~~~

* Heat Pump State: Current operating state (Off, Ready, Heating, Hot Water, etc.)
* Season Mode: Current season mode (Summer, Winter, Auto)
* Alarm Active: Indicates if any alarms are active
* System Active: Overall system activity status
* Online Status: Connection status to the heat pump

Control Entities (when Enable Writes is active)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Hot Water Set Point: Target temperature for domestic hot water (40-65°C)
* Room Set Point: Target room temperature (10-30°C)
* Season Mode: Change between Summer, Winter, and Auto modes

Diagnostic Entities
~~~~~~~~~~~~~~~~~~~

* Compressor Runtime: Total compressor operating hours
* Heater Runtime: Total auxiliary heater operating hours
* Pump Runtime: Total pump operating hours
* IP Address: Network IP of the heat pump controller
* Software Version: Firmware version of the controller
* Last Update: Timestamp of the last successful data update

Binary Sensors
~~~~~~~~~~~~~~

* Heater: Status of the auxiliary heater
* Hot Tap Water: Status of hot water heating
* Cold Pump: Status of the cold side pump
* Hot Side Pump: Status of the hot side pump
* Defrost Valve: Status of the defrost valve
* Solar Pump: Status of the solar pump
* Aux Pump: Status of the auxiliary pump
* Alarm: Active alarm status
* HP/LP/BP Switch: Status of pressure switches

Troubleshooting
---------------

Connection Issues
~~~~~~~~~~~~~~~~~

**Cannot connect to heat pump**

1. Verify the IP address is correct
2. Check that your heat pump is powered on and connected to the network
3. Ensure no firewall is blocking access to the heat pump
4. Try pinging the heat pump IP address from your Home Assistant host

**Authentication failed**

1. Verify your username and password are correct
2. Try enabling "Allow Basic Auth (Legacy)" if your device doesn't support Digest authentication
3. Check if your heat pump's web interface is accessible with the same credentials

Missing Entities
~~~~~~~~~~~~~~~~

**Some entities are not showing up**

1. Check the integration options to ensure the feature is enabled (e.g., "Enable Solar")
2. Verify your heat pump model supports the specific features
3. Some entities may not be available if the corresponding hardware is not installed

**Entities show as unavailable**

1. Check the Home Assistant log for error messages
2. Verify the heat pump is not in a service mode
3. Some temperature sensors may be unavailable if temperatures are below -50°C (sensor error condition)

Performance Issues
~~~~~~~~~~~~~~~~~~

**Frequent connection errors**

1. Increase the scan interval in the integration options
2. Check network stability between Home Assistant and the heat pump
3. Ensure the heat pump's web interface is responsive

**High CPU usage**

1. Reduce the scan interval
2. Limit the number of entities monitored using a custom ID list

Advanced Configuration
----------------------

Custom ID List
~~~~~~~~~~~~~~

For advanced users, you can specify exactly which entities to monitor by providing a custom ID list:

1. Go to the integration options
2. Enter a semicolon-separated list of entity IDs in the "ID List" field
3. Use the default list as a reference for available IDs

Example: ``299;255;256;257`` would monitor only capacity, water tank, heating supply, and room temperature.

Finding Entity IDs
~~~~~~~~~~~~~~~~~~

You can find entity IDs by:

1. Checking the Home Assistant developer tools
2. Viewing the integration diagnostics
3. Referencing the source code constants

Services
--------

The integration provides the following services when write controls are enabled:

* ``svk_heatpump.set_parameter``: Set a specific parameter value

Example usage in automation:

.. code-block:: yaml

  automation:
    - alias: Set hot water temperature at night
      trigger:
        platform: time
        at: "22:00:00"
      action:
        service: svk_heatpump.set_parameter
        data:
          entity_id: sensor.hot_water_set_point
          value: 45

Diagnostics
-----------

The integration includes comprehensive diagnostic tools to help troubleshoot issues:

1. Go to **Settings** > **Devices & Services**
2. Find the SVK Heatpump integration
3. Click the three dots menu and select "Download Diagnostics"
4. The diagnostics file contains detailed information about:
   * Connection status
   * API responses
   * Parsing statistics
   * Entity availability

Development
-----------

For developers interested in contributing to this integration:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with real hardware
5. Submit a pull request with a clear description of changes

License
-------

This integration is released under the MIT License. See the LICENSE file for details.

Copyright (c) 2024 SVK Heatpump Contributors

Support
-------

If you encounter issues with this integration:

1. Check the troubleshooting section above
2. Search existing issues in the repository
3. Create a new issue with detailed information about your problem
4. Include diagnostic information when possible

Changelog
---------

For information about recent changes, please refer to the changelog in the repository.