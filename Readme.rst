SVK Heat Pump Home Assistant Integration
=======================================

.. image:: custom_components/svk_heatpump/logo.png
    :alt: SVK Heat Pump Logo
    :align: center
    :width: 300px

A custom Home Assistant integration for SVK LMC320 heat pump controllers, providing comprehensive monitoring and control capabilities through both modern JSON API and legacy HTML scraping interfaces.

**Version:** 0.2.x

.. contents::
   :local:
   :depth: 2

Features
--------

* **165+ Entities**: Comprehensive monitoring of all heat pump parameters
* **Dual API Support**: Modern JSON API with fallback to HTML scraping
* **Performance Optimized**: Chunking and parallel processing for fast data retrieval
* **Flexible Authentication**: Support for both Digest and Basic authentication
* **Real-time Control**: Adjustable setpoints and operational parameters
* **Comprehensive Diagnostics**: Detailed logging and troubleshooting information
* **Solar Integration**: Monitor solar panel performance and contribution
* **Energy Monitoring**: Track power consumption and efficiency metrics

Compatibility
------------

* **Heat Pump Models**: SVK LMC320 series
* **Home Assistant**: 2023.1 or newer
* **Python**: 3.9 or newer
* **Installation**: HACS 1.28+ or manual installation

Installation
------------

Via HACS (Recommended)
~~~~~~~~~~~~~~~~~~~~~

1. In Home Assistant, go to **HACS** → **Integrations**
2. Click the three dots menu in the top right corner → **Custom repositories**
3. Add repository URL: ``https://github.com/janusr/HA-SVKHeat``
4. Set category to **Integration**
5. Click **Add**
6. Wait for HACS to download the repository information
7. Search for "SVK Heat Pump" in the integrations list
8. Click **Install** on the SVK Heat Pump integration
9. After installation completes, click **Restart Home Assistant** (or restart manually)
10. Go to **Settings** → **Devices & Services** → **Integrations**
11. Click **+ Add Integration** in the bottom right corner
12. Search for "SVK Heat Pump" and select it
13. Follow the configuration wizard with your heat pump details
14. Once configured, entities will appear automatically in your system

Manual Installation
~~~~~~~~~~~~~~~~~~

1. Copy the ``custom_components/svk_heatpump`` directory to your ``config/custom_components`` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Integrations**
4. Click **+ Add Integration** → **SVK Heat Pump**
5. Follow the configuration wizard

Configuration
-------------

Basic Setup
~~~~~~~~~~~~~

* **Host**: IP address or hostname of your heat pump (e.g., ``192.168.1.100``)
* **Username**: Administrator username (default: ``admin``)
* **Password**: Administrator password
* **Scan Interval**: Data refresh interval in seconds (default: ``30``)

Advanced Options
~~~~~~~~~~~~~~~

* **Enable Writes**: Allow control of heat pump parameters (default: ``False``)
  * When enabled, you can adjust setpoints and operational parameters
  * Requires careful consideration as changes affect heat pump operation

Modern Entity Management
~~~~~~~~~~~~~~~~~~~~~~~~

New installations use the Home Assistant UI for entity selection:

1. Go to **Settings** → **Devices & Services**
2. Find your SVK Heat Pump integration
3. Click **Configure** or **1 device** to access entity options
4. Enable/disable entities through the checkbox interface
5. Changes take effect immediately without restart

This approach provides:
* User-friendly entity selection with descriptive names
* No need to reference numeric IDs
* Easy toggling of entities based on your needs
* Automatic updates when new entities are added

API Implementation
-----------------

JSON API
~~~~~~~~~~~~~~~~~~

The integration prioritizes the modern JSON API for optimal performance:

* **Endpoint**: ``/cgi-bin/json_values.cgi``
* **Method**: POST requests with JSON payload
* **Authentication**: Digest authentication with automatic nonce handling
* **Chunking**: Automatic request optimization for large entity sets
* **Parallel Processing**: Concurrent data retrieval for improved responsiveness
* **Error Handling**: Comprehensive retry logic with exponential backoff
* **Timeout Protection**: 30-second timeout with detailed diagnostics

Performance Features
~~~~~~~~~~~~~~~~~~~

* **Smart Chunking**: Automatically splits large requests into optimal chunks
  * Default chunk size: 25 entities per request
  * Reduces heat pump processing load
  * Minimizes network timeout risk

* **Progressive Loading**: Essential entities loaded first on startup
  * Core temperature sensors and status indicators
  * Additional entities loaded in subsequent cycles

* **Parallel Processing**: Concurrent network operations
  * Reduces total update time by 40-60%
  * Non-blocking implementation prevents Home Assistant freezing

Authentication
-------------

Digest Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Security**: Challenge-response mechanism with nonce values
* **Implementation**: RFC 7616 compliant Digest authentication
* **Automatic Handling**: Nonce refresh and stale authentication detection
* **Error Messages**: Clear guidance for authentication issues

Entities
--------

The integration provides 100+ entities organized into the following categories:

Temperature Sensors
~~~~~~~~~~~~~~~~~~

Core temperature monitoring for system optimization:

* **Heating Supply Temp**: Current supply water temperature (°C)
* **Heating Return Temp**: Return water temperature (°C)
* **Water Tank Temp**: Hot water tank temperature (°C)
* **Ambient Temp**: Outdoor temperature (°C)
* **Room Temp**: Indoor room temperature (°C)
* **Heating Tank Temp**: Internal heating tank temperature (°C)
* **Cold Side Supply Temp**: Cold side supply temperature (°C)
* **Cold Side Return Temp**: Cold side return temperature (°C)
* **Evaporator Temp**: Evaporator temperature (°C)
* **Solar Collector Temp**: Solar collector temperature (°C)
* **Solar Water Temp**: Solar water temperature (°C)

Setpoints & Control
~~~~~~~~~~~~~~~~~~

Adjustable parameters for system control (when writes enabled):

* **Room Setpoint**: Target room temperature (°C, range: 10-35)
* **Hot Water Setpoint**: Target hot water temperature (°C, range: 40-65)
* **Heating Setpoint**: Heating curve setpoint (°C, range: 10-35)
* **Room Setpoint Control**: Alternative room temperature control
* **Hot Water Setpoint Control**: Alternative hot water control

Performance Metrics
~~~~~~~~~~~~~~~~~~

Real-time performance and efficiency data:

* **Compressor Speed V**: Compressor speed in volts (V)
* **Compressor Speed Percent**: Compressor speed percentage (%)
* **Capacity Actual**: Current heating capacity (kW)
* **Capacity Requested**: Requested heating capacity (kW)
* **Cold Pump Speed**: Cold side pump speed (RPM)
* **Power Consumption**: Current power draw (kW)
* **Energy Consumption**: Total energy consumption (kWh)

System Status
~~~~~~~~~~~~~

Operational state and mode information:

* **Heat Pump State**: Current operational state
  * ``off``, ``ready``, ``start_up``, ``heating``, ``hot_water``
  * ``el_heating``, ``defrost``, ``drip_delay``, ``total_stop``
  * ``pump_exercise``, ``forced_running``, ``manual``
* **Season Mode**: Seasonal operating mode
  * ``winter``, ``summer``, ``auto``
* **Solar Panel State**: Solar system status
* **Hot Water Source**: Hot water heating source
  * ``heat_pump``, ``electric``, ``solar``

Runtime Counters
~~~~~~~~~~~~~~

Cumulative operational data for maintenance planning:

* **Compressor Runtime**: Total compressor operating hours (h)
* **Heater Runtime**: Electric heater operating hours (h)
* **Pump Runtime**: Circulation pump operating hours (h)
* **System Runtime**: Total system operating hours (h)
* **Defrost Count**: Number of defrost cycles
* **Start Count**: System start/stop cycles

Alarms & Diagnostics
~~~~~~~~~~~~~~~~~~~~

System health and maintenance information:

* **Alarm Active**: Active alarm status (boolean)
* **Alarm Count**: Number of active alarms
* **Alarm List**: Detailed alarm information
* **Error Count**: System error occurrences
* **Service Code**: Service/maintenance codes
* **Log Interval**: Logging interval setting

System Information
~~~~~~~~~~~~~~~~~

Device identification and configuration:

* **IP Address**: Network IP address
* **Software Version**: Firmware version string
* **Model**: Heat pump model identification
* **Serial Number**: Device serial number
* **Language**: Display language setting

Configuration Entities
~~~~~~~~~~~~~~~~~~~~

Advanced configuration options (when writes enabled):

* **Defrost Mode**: Defrost operation mode
  * ``off``, ``manual``, ``automatic``
* **Heating Source**: Primary heating source
  * ``heat_pump``, ``electric``, ``manual``
* **Heating Control Type**: Heating control method
  * ``off``, ``curve``, ``room``, ``outdoor``
* **Heat Pump Control Mode**: Compressor control mode
  * ``off``, ``room``, ``outdoor``, ``curve``
* **Compressor Control Mode**: Compressor operation mode
  * ``off``, ``standard``, ``eco``, ``comfort``
* **Cold Pump Mode**: Cold side pump operation mode
  * ``off``, ``auto``, ``manual``
* **Display Mode**: Interface display complexity
  * ``basic``, ``advanced``, ``service``
* **Solar Sensor Select**: Solar temperature sensor selection
  * ``internal``, ``external``
* **User Language**: Interface language
  * ``english``, ``danish``, ``german``, ``swedish``

Control Switches
~~~~~~~~~~~~~~

Binary controls for system operation (when writes enabled):

* **Main Switch**: System master on/off control
* **Manual Mode**: Enable/disable manual operation mode
* **Season Switch**: Seasonal mode control
* **Neutral Zone**: Neutral zone temperature control
* **Temperature Offset**: Temperature offset adjustment
* **Concrete Mode**: Concrete floor heating mode
* **Various Enable Switches**: Feature-specific enable/disable controls

Entity Reference Table
~~~~~~~~~~~~~~~~~~~~~~

The following table summarizes all available entities organized by platform:

+------------------+---------------------------------------------+------------------+----------+
| Platform         | Entity Name                                 | Category         | Writable |
+==================+=============================================+==================+==========+
| **Binary Sensor** | Heat Pump State                             | Operation        | No       |
|                  | Solar Panel State                           | Operation        | No       |
|                  | Heat Pump Season State                      | Operation        | No       |
|                  | Cold Pump State                            | Operation        | No       |
|                  | Legionella State                           | Operation        | No       |
|                  | Compressor Output                          | Operation        | No       |
|                  | Heater Output                             | Operation        | No       |
|                  | Hot Tap Water Output                      | Operation        | No       |
|                  | Cold Pump Output                         | Operation        | No       |
|                  | Cold Pump Low Output                     | Operation        | No       |
|                  | Hot Side Pump Output                     | Operation        | No       |
|                  | Defrost Valve Output                     | Operation        | No       |
|                  | Solar Pump Output                        | Operation        | No       |
|                  | Aux Pump Output                          | Operation        | No       |
|                  | Alarm Output                            | Operation        | No       |
+------------------+---------------------------------------------+------------------+----------+
| **Sensor**       | Heating Supply Temp                         | Operation        | No       |
|                  | Heating Return Temp                        | Operation        | No       |
|                  | Water Tank Temp                           | Operation        | No       |
|                  | Ambient Temp                              | Operation        | No       |
|                  | Room Temp                                 | Operation        | No       |
|                  | Heating Tank Temp                         | Operation        | No       |
|                  | Cold Side Supply Temp                      | Operation        | No       |
|                  | Cold Side Return Temp                      | Operation        | No       |
|                  | Evaporator Temp                           | Operation        | No       |
|                  | Solar Panel Temp                          | Operation        | No       |
|                  | Solar Water Temp                          | Operation        | No       |
|                  | Heating Setpoint Actual                   | Operation        | No       |
|                  | Hot Water Setpoint Actual                 | Operation        | No       |
|                  | Heat Pump Capacity Requested              | Operation        | No       |
|                  | Heat Pump Capacity Actual                 | Operation        | No       |
|                  | Hot Water Source                         | Operation        | No       |
|                  | Heating Source                          | Operation        | No       |
|                  | Defrost Temperature Settings               | Settings         | Yes      |
|                  | Heat Pump Parameters                     | Settings         | Yes      |
|                  | Heating Control Parameters               | Settings         | Yes      |
|                  | Compressor Parameters                   | Settings         | Yes      |
|                  | Cold Pump Parameters                    | Settings         | Yes      |
|                  | Hot Water Parameters                    | Settings         | Yes      |
|                  | Solar Panel Parameters                  | Settings         | Yes      |
|                  | Service Information                     | Settings         | No       |
|                  | Runtime Counters                        | Settings         | No       |
|                  | System Information                      | Configuration    | No       |
+------------------+---------------------------------------------+------------------+----------+
| **Number**        | Defrost Parameters                        | Settings         | Yes      |
|                  | Heating Setpoint Min/Max                 | Settings         | Yes      |
|                  | Heating Curve Points                     | Settings         | Yes      |
|                  | Compressor Voltage Settings               | Settings         | Yes      |
|                  | Cold Pump Speed Settings                 | Settings         | Yes      |
|                  | Hot Water Setpoint                      | Settings         | Yes      |
|                  | Legionella Parameters                   | Settings         | Yes      |
|                  | Solar Panel Temperature Settings          | Settings         | Yes      |
|                  | Room Temperature Setpoint               | Settings         | Yes      |
+------------------+---------------------------------------------+------------------+----------+
| **Select**        | Defrost Mode                             | Settings         | Yes      |
|                  | Heating Source                           | Settings         | Yes      |
|                  | Heating Control Type                     | Settings         | Yes      |
|                  | Heat Pump Control Mode                  | Settings         | Yes      |
|                  | Compressor Control Mode                 | Settings         | Yes      |
|                  | Cold Pump Mode                           | Settings         | Yes      |
|                  | Hot Water Source                         | Settings         | Yes      |
|                  | Display Mode                            | Settings         | Yes      |
|                  | Solar Panel Sensor Select               | Settings         | Yes      |
|                  | User Language                           | Settings         | Yes      |
+------------------+---------------------------------------------+------------------+----------+
| **Switch**        | Temperature Offset                       | Settings         | Yes      |
|                  | Hot Water Neutral Zone                  | Settings         | Yes      |
|                  | Main Switch                            | Settings         | Yes      |
|                  | Manual Controls                         | Settings         | Yes      |
|                  | Concrete Mode                          | Settings         | Yes      |
|                  | Season Mode                            | Settings         | Yes      |
+------------------+---------------------------------------------+------------------+----------+

For a complete list of all entities with their exact names and parameters, 
please refer to the entity catalog in the integration source code.

Services
--------

The integration provides the following services for automation:

**svk_heatpump.set_parameter**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set a specific parameter on the heat pump:

.. code-block:: yaml

  service: svk_heatpump.set_parameter
  target:
    entity_id: sensor.svk_heatpump_hot_water_setpoint
  data:
    value: 55

**Parameters:**

* ``entity_id``: Target entity to control
* ``value``: New value to set (type depends on entity)

**Examples:**

Set hot water temperature to 60°C:

.. code-block:: yaml

  service: svk_heatpump.set_parameter
  target:
    entity_id: number.svk_heatpump_hot_water_setpoint
  data:
    value: 60

Set room temperature to 22°C:

.. code-block:: yaml

  service: svk_heatpump.set_parameter
  target:
    entity_id: number.svk_heatpump_room_setpoint
  data:
    value: 22

Change heating source to heat pump:

.. code-block:: yaml

  service: svk_heatpump.set_parameter
  target:
    entity_id: select.svk_heatpump_heating_source
  data:
    value: "heat_pump"

Enable manual operation:

.. code-block:: yaml

  service: svk_heatpump.set_parameter
  target:
    entity_id: switch.svk_heatpump_manual_mode
  data:
    value: true

**svk_heatpump.restart_integration**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Restart the integration and force data refresh:

.. code-block:: yaml

  service: svk_heatpump.restart_integration
  target:
    entity_id: sensor.svk_heatpump_system_status

**Use Cases:**

* After network configuration changes
* When troubleshooting data issues
* To force refresh of all entity values

**svk_heatpump.toggle_writes**
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Enable or disable write controls:

.. code-block:: yaml

  service: svk_heatpump.toggle_writes
  data:
    enable: true

**Use Cases:**

* Temporarily disable controls during maintenance
* Enable controls for automated setpoint adjustments
* Safety measure to prevent accidental changes

**Automation Examples:**

Schedule hot water heating for morning:

.. code-block:: yaml

  alias: "Morning Hot Water"
  trigger:
    - platform: time
      at: "06:00:00"
  action:
    - service: svk_heatpump.set_parameter
      target:
        entity_id: number.svk_heatpump_hot_water_setpoint
      data:
        value: 60
    - delay: "02:00:00"
    - service: svk_heatpump.set_parameter
      target:
        entity_id: number.svk_heatpump_hot_water_setpoint
      data:
        value: 45

Adjust heating based on outdoor temperature:

.. code-block:: yaml

  alias: "Weather-Based Heating"
  trigger:
    - platform: numeric_state
      entity_id: sensor.svk_heatpump_ambient_temp
      below: 5
  action:
    - service: svk_heatpump.set_parameter
      target:
        entity_id: select.svk_heatpump_heating_source
      data:
        value: "heat_pump"
    - service: svk_heatpump.set_parameter
      target:
        entity_id: number.svk_heatpump_heating_setpoint_actual
      data:
        value: 22

Troubleshooting
---------------

JSON API Issues
~~~~~~~~~~~~~~

**No Data Received**
~~~~~~~~~~~~~~~~~

* **Symptoms**: Entities show as unavailable or "unknown"
* **Causes**:
  * Incorrect authentication credentials
  * Network connectivity issues
  * Heat pump firmware incompatibility
  * Firewall blocking port 80

* **Solutions**:
  1. Verify IP address and network connectivity
  2. Check username and password in heat pump web interface
  3. Test authentication with curl: ``curl --digest -u admin:password http://192.168.1.100/cgi-bin/LomJson.cgi``
  4. Check Home Assistant logs for authentication errors
  5. Verify heat pump firmware supports JSON API

**Timeout Errors**
~~~~~~~~~~~~~~~~

* **Symptoms**: "Data update timeout" or "Request timed out"
* **Causes**:
  * Network latency to heat pump
  * Heat pump processing too many IDs in single request
  * Authentication delays (multiple round-trips)
  * Chunking inefficiency (too many small requests)

* **Solutions**:
  1. Increase scan interval in integration configuration
  2. Check network performance between Home Assistant and heat pump
  3. Reduce number of enabled entities if necessary
  4. Check heat pump CPU utilization (high load may cause timeouts)

**Authentication Errors**
~~~~~~~~~~~~~~~~~~~~

* **"Device does not support Digest authentication"**
  * **Cause**: Heat pump firmware only supports Basic authentication
  * **Solution**: No action needed, integration will fall back to Basic auth

* **"Invalid username or password"**
  * **Cause**: Incorrect credentials
  * **Solution**: Verify credentials in heat pump web interface
  * **Reset**: Use heat pump's physical reset button if credentials forgotten

* **"Authentication nonce expired"**
  * **Cause**: Stale authentication session
  * **Solution**: Reconfigure integration or restart Home Assistant

HTML Scraping Issues
~~~~~~~~~~~~~~~~~~

**Page Parse Errors**
~~~~~~~~~~~~~~~~~~~

* **Symptoms**: Missing entities or incorrect values
* **Causes**:
  * Firmware version with different HTML structure
  * Incomplete page loads due to network issues
  * Authentication redirects interfering with scraping

* **Solutions**:
  1. Check if firmware update is available for JSON API support
  2. Verify all pages load correctly in browser
  3. Check Home Assistant logs for parsing warnings
  4. Consider reducing enabled entities to essential ones

**Missing Entities**
~~~~~~~~~~~~~~~~~~

* **Symptoms**: Expected entities not appearing in Home Assistant
* **Causes**:
  * Firmware version doesn't support certain features
  * Entity disabled in configuration
  * Legacy ID list filtering out desired entities (for upgraded configurations)

* **Solutions**:
  1. Check heat pump model and supported features
  2. For new installations: Enable entities through integration options UI
  3. For upgraded configurations: Check legacy ID list configuration (if present)
  4. Enable all entities in integration options
  5. Check entity availability in Developer Tools
  3. Enable all entities in integration options
  4. Check entity availability in Developer Tools

Performance Optimization
---------------------

Network Configuration
~~~~~~~~~~~~~~~~~~~

* **Wired Connection**: Use Ethernet instead of Wi-Fi for reliability
* **Static IP**: Assign static IP to heat pump to prevent connection issues
* **Network Quality**: Ensure good signal strength and low latency
* **Firewall**: Configure firewall to allow HTTP traffic on port 80

Integration Settings
~~~~~~~~~~~~~~~~~~

* **Scan Interval**: Adjust based on your needs
  * **30 seconds**: Good balance of responsiveness and system load
  * **60 seconds**: Reduced system load for basic monitoring
  * **120 seconds**: Minimal system load for simple monitoring

* **Entity Selection**: Enable only needed entities
  * **Essential Only**: Core temperatures and status (50-75 entities)
  * **Full Monitoring**: All 165+ entities for comprehensive oversight
  * **Modern UI Selection**: Use integration options to select entities by name
  * **Legacy ID List**: For upgraded configurations with custom entity requirements

* **Write Controls**: Enable only when needed
  * **Monitoring Only**: Disable writes to prevent accidental changes
  * **Active Control**: Enable writes for automated setpoint adjustments

Development
-----------

Contributing
~~~~~~~~~~~

1. Fork the repository
2. Create a feature branch: ``git checkout -b feature-name``
3. Make your changes
4. Add tests if applicable
5. Ensure code follows PEP 8 style guidelines
6. Commit your changes: ``git commit -m "Add feature"``
7. Push to your fork: ``git push origin feature-name``
8. Create a Pull Request

Code Style
~~~~~~~~~~

* **Python**: Follow PEP 8 style guidelines
* **Docstrings**: Use Google-style docstrings
* **Type Hints**: Include type annotations for all functions
* **Logging**: Use structured logging with appropriate levels
* **Error Handling**: Implement comprehensive exception handling

Testing
~~~~~~

* **Unit Tests**: Run with ``python -m pytest tests/``
* **Integration Tests**: Use development Home Assistant instance
* **Manual Testing**: Test with actual SVK heat pump hardware
* **Mock Testing**: Use mock responses for CI/CD pipelines

Real Device Testing
~~~~~~~~~~~~~~~~~~~

For developers working with actual SVK hardware, see `docs/REAL_DEVICE_TESTING.md` for detailed testing procedures, device information, and implementation updates based on real device testing.

Project Structure
~~~~~~~~~~~~~

::

  custom_components/svk_heatpump/
  ├── __init__.py              # Integration initialization
  ├── manifest.json            # Integration metadata
  ├── config_flow.py          # Configuration flow
  ├── coordinator.py           # Data coordination and caching
  ├── client.py               # API client implementation
  ├── const.py                # Constants and entity definitions
  ├── sensor.py               # Sensor platform implementation
  ├── number.py               # Number platform implementation
  ├── select.py               # Select platform implementation
  ├── switch.py               # Switch platform implementation
  ├── binary_sensor.py        # Binary sensor platform
  ├── diagnostics.py          # Diagnostic data collection
  ├── entity_base.py          # Base entity classes
  ├── catalog.py              # Entity catalog and definitions
  ├── compat.py               # Compatibility utilities
  └── translations/           # Internationalization files
      ├── en.json
      └── da.json

License
-------

This project is licensed under the MIT License - see the LICENSE file for details.

Support
-------

* **Documentation**: https://github.com/janusr/HA-SVKHeat/wiki
* **Issues**: https://github.com/janusr/HA-SVKHeat/issues
* **Discussions**: https://github.com/janusr/HA-SVKHeat/discussions

Changelog
---------

Version 0.0.1
~~~~~~~~~~~~~

* Added comprehensive JSON API support with Digest authentication
* Implemented chunking and parallel processing for performance
* Expanded entity catalog to 165+ entities
* Added fallback to HTML scraping for legacy firmware
* Improved error handling and diagnostic logging
* Enhanced configuration flow with advanced options
* Added comprehensive services for automation
* Implemented temperature sentinel value handling
* Added entity availability validation