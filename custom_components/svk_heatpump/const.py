"""Constants for SVK Heatpump integration."""
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = "svk_heatpump"
DEFAULT_TIMEOUT = 10
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_CHUNK_SIZE = 50  # Increased from 25 to reduce number of requests and improve performance
DEFAULT_ENABLE_CHUNKING = True
DEFAULT_EXCLUDED_IDS = ""

# Configuration keys
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLE_WRITES = "enable_writes"
CONF_ENABLE_SOLAR = "enable_solar"
CONF_ENABLE_COUNTERS = "enable_counters"
CONF_ID_LIST = "id_list"
CONF_CHUNK_SIZE = "chunk_size"
CONF_ENABLE_CHUNKING = "enable_chunking"
CONF_EXCLUDED_IDS = "excluded_ids"

# Page endpoints with dataset parameters
PAGES = {
    "display": "cgi-bin/dataset_display.cgi?dataset=/Operation/Display.dst",
    "user": "cgi-bin/dataset_display.cgi?dataset=/Operation/User.dst",
    "heating": "cgi-bin/dataset_display.cgi?dataset=/Operation/Heating.dst",
    "heatpump": "cgi-bin/dataset_display.cgi?dataset=/Operation/Heatpump.dst",
    "solar": "cgi-bin/dataset_display.cgi?dataset=/Operation/Solar.dst",
    "hotwater": "cgi-bin/dataset_display.cgi?dataset=/Operation/Hotwater.dst",
    # Additional datasets that might be useful
    "extended_display": "cgi-bin/dataset_display.cgi?dataset=/Settings/Extended%20Display.dst",
    "alarms": "cgi-bin/dataset_display.cgi?dataset=/Operation/Alarms.dst",
    "counters": "cgi-bin/dataset_display.cgi?dataset=/Operation/Counters.dst"
}

# Heat pump state mappings
HEATPUMP_STATES = {
    "Off": "off",
    "Ready": "ready",
    "Start up": "start_up",
    "Heating": "heating",
    "Hot water": "hot_water",
    "El heating": "el_heating",
    "Defrost": "defrost",
    "Drip delay": "drip_delay",
    "Total stop": "total_stop",
    "Pump exercise": "pump_exercise",
    "Forced running": "forced_running",
    "Manual": "manual"
}

# Reverse mapping for writes
HEATPUMP_STATES_REVERSE = {v: k for k, v in HEATPUMP_STATES.items()}

# Season mode mappings
SEASON_MODES = {
    "Summer": "summer",
    "Winter": "winter",
    "Auto": "auto"
}

# Reverse mapping for writes
SEASON_MODES_REVERSE = {v: k for k, v in SEASON_MODES.items()}

# Solar panel state mappings
SOLAR_STATES = {
    "Off": "off",
    "Running": "running",
    "Forced Stop": "forced_stop"
}

# Reverse mapping for writes
SOLAR_STATES_REVERSE = {v: k for k, v in SOLAR_STATES.items()}

# Temperature sensor definitions
TEMP_SENSORS = {
    "heating_supply_temp": {
        "name": "Heating Supply Temp",
        "label": "Heating supply",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "heating_return_temp": {
        "name": "Heating Return Temp",
        "label": "Heating return",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "water_tank_temp": {
        "name": "Water Tank Temp",
        "label": "Water tank",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "ambient_temp": {
        "name": "Ambient Temp",
        "label": "Ambient",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "room_temp": {
        "name": "Room Temp",
        "label": "Room",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "heating_tank_temp": {
        "name": "Heating Tank Temp",
        "label": "Heating tank",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "cold_side_supply_temp": {
        "name": "Cold Side Supply Temp",
        "label": "Cold side supply",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "cold_side_return_temp": {
        "name": "Cold Side Return Temp",
        "label": "Cold side return",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "evaporator_temp": {
        "name": "Evaporator Temp",
        "label": "Evaporator",
        "page": "display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "solar_collector_temp": {
        "name": "Solar Collector Temp",
        "label": "Solar collector",
        "page": "solar",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "solar_water_temp": {
        "name": "Solar Water Temp",
        "label": "Solar water",
        "page": "solar",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    }
}

# Setpoint sensor definitions
SETPOINT_SENSORS = {
    "heating_setpoint": {
        "name": "Heating Set Point",
        "label": "Heating set point",
        "page": "user",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    },
    "hot_water_setpoint": {
        "name": "Hot Water Set Point",
        "label": "Hot water set point",
        "page": "user",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement"
    }
}

# Performance sensor definitions
PERFORMANCE_SENSORS = {
    "compressor_speed_v": {
        "name": "Compressor Speed",
        "label": "Compressor speed",
        "page": "heatpump",
        "unit": "V",
        "state_class": "measurement"
    },
    "compressor_speed_percent": {
        "name": "Compressor Speed",
        "label": "Compressor speed %",
        "page": "heatpump",
        "unit": "%",
        "state_class": "measurement"
    },
    "cold_pump_speed": {
        "name": "Cold Pump Speed",
        "label": "Cold pump speed",
        "page": "heatpump",
        "unit": "V",
        "state_class": "measurement"
    },
    "requested_capacity": {
        "name": "Requested Heating Capacity",
        "label": "Requested capacity",
        "page": "heating",
        "unit": "%",
        "state_class": "measurement"
    },
    "actual_capacity": {
        "name": "Actual Capacity",
        "label": "Actual capacity",
        "page": "heating",
        "unit": "%",
        "state_class": "measurement"
    }
}

# Counter sensor definitions (diagnostic)
COUNTER_SENSORS = {
    "compressor_runtime": {
        "name": "Compressor Runtime",
        "label": "Compressor runtime",
        "page": "heatpump",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing"
    },
    "heater_runtime": {
        "name": "Heater Runtime",
        "label": "Heater runtime",
        "page": "heating",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing"
    },
    "pump_runtime": {
        "name": "Pump Runtime",
        "label": "Pump runtime",
        "page": "heating",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing"
    }
}

# System information sensors (diagnostic)
SYSTEM_SENSORS = {
    "ip_address": {
        "name": "IP Address",
        "label": "IP address",
        "page": "display",
        "entity_category": "diagnostic"
    },
    "software_version": {
        "name": "Software Version",
        "label": "Software version",
        "page": "display",
        "entity_category": "diagnostic"
    },
    "log_interval": {
        "name": "Log Interval",
        "label": "Log interval",
        "page": "display",
        "entity_category": "diagnostic"
    }
}

# Binary sensor definitions
BINARY_SENSORS = {
    "alarm_active": {
        "name": "Alarm Active",
        "label": "Alarm active",
        "page": "display",
        "device_class": "problem"
    }
}

# Select entity definitions
SELECT_ENTITIES = {
    "heatpump_state": {
        "name": "Heat Pump State",
        "label": "Heat pump state",
        "page": "display",
        "options": list(HEATPUMP_STATES.keys()),
        "mappings": HEATPUMP_STATES
    },
    "solar_panel_state": {
        "name": "Solar Panel State",
        "label": "Solar panel state",
        "page": "solar",
        "options": list(SOLAR_STATES.keys()),
        "mappings": SOLAR_STATES
    },
    "season_mode": {
        "name": "Season Mode",
        "label": "Season mode",
        "page": "user",
        "options": list(SEASON_MODES.keys()),
        "mappings": SEASON_MODES,
        "writable": True
    }
}

# Number entity definitions (writable)
NUMBER_ENTITIES = {
    "hot_water_setpoint": {
        "name": "Hot Water Set Point",
        "label": "Hot water set point",
        "page": "user",
        "min_value": 40,
        "max_value": 65,
        "step": 1,
        "unit": "°C",
        "device_class": "temperature"
    },
    "room_setpoint": {
        "name": "Room Set Point",
        "label": "Room set point",
        "page": "user",
        "min_value": 10,
        "max_value": 30,
        "step": 1,
        "unit": "°C",
        "device_class": "temperature"
    }
}

# Alarm severity levels
ALARM_SEVERITIES = {
    "Warning": "warning",
    "Critical": "critical"
}

# Default alarm codes and descriptions
ALARM_CODES = {
    # Sensor faults (100-121)
    "100": "Temperature sensor fault",
    "101": "Temperature sensor fault",
    "102": "Temperature sensor fault",
    "103": "Temperature sensor fault",
    "104": "Temperature sensor fault",
    "105": "Temperature sensor fault",
    "106": "Temperature sensor fault",
    "107": "Temperature sensor fault",
    "108": "Temperature sensor fault",
    "109": "Temperature sensor fault",
    "110": "Temperature sensor fault",
    "111": "Temperature sensor fault",
    "112": "Temperature sensor fault",
    "113": "Temperature sensor fault",
    "114": "Temperature sensor fault",
    "115": "Temperature sensor fault",
    "116": "Temperature sensor fault",
    "117": "Temperature sensor fault",
    "118": "Temperature sensor fault",
    "119": "Temperature sensor fault",
    "120": "Temperature sensor fault",
    "121": "Temperature sensor fault",
    
    # Pressostat & FC alarms (600-609)
    "600": "Low pressure",
    "601": "Low pressure",
    "602": "High pressure",
    "603": "High pressure",
    "604": "Pressostat fault",
    "605": "Pressostat fault",
    "606": "Flow switch fault",
    "607": "Flow switch fault",
    "608": "FC alarm",
    "609": "FC alarm"
}

# JSON API Constants

# Complete list of all available entity IDs
# This list contains all entities that can be accessed from the heat pump
DEFAULT_IDS = "297;253;254;255;256;257;259;260;261;262;263;264;420;386;364;403;410;411;409;419;405;406;407;430;429;428;435;436;413;421;184;192;185;186;187;188;189;190;191;197;196;284;285;281;283;282;404;453;427;408;286;280;368;367;369;370;371;372;380;383;384;385;382;500;501;504;137;193;278;113;112;110;109;108;265;266;267;268;269;296;374;503;300;433;299;219;220;221;227;228;232;509;513;516;517;520;522;524;521;529;514;515;510;511;512;518;523;37;555;53;52;291;277;235;243;236;237;238;239;240;241;242;244;245;250;447;423;387;303;362;525;526;390"

# Default enabled entities list
# This list contains the essential entities that should be enabled by default
# These entities provide the core functionality and monitoring capabilities
# Users can enable additional entities through the UI as needed
DEFAULT_ENABLED_ENTITIES = [
    # Core temperature sensors
    253,  # heating_supply_temp
    254,  # heating_return_temp
    255,  # water_tank_temp
    256,  # ambient_temp
    257,  # room_temp
    
    # Heat pump state and status
    297,  # heatpump_state
    296,  # heatpump_season_state
    299,  # capacity_actual
    300,  # capacity_requested
    
    # Essential setpoints
    193,  # room_setpoint
    383,  # hot_water_setpoint
    386,  # hot_water_setpoint_actual
    420,  # heating_setpoint_actual
    
    # Operating mode
    278,  # season_mode
    
    # Important binary outputs
    220,  # hot_tap_water_output
    228,  # alarm_output
    
    # Solar panel state (if available)
    364,  # solar_panel_state
    
    # Hot water source
    380,  # hot_water_source
    
    # Runtime counters (useful for monitoring)
    447,  # compressor_runtime
    301,  # heatpump_runtime
    387,  # hot_water_runtime
]

# Binary output IDs (exposed as binary_sensors)
BINARY_OUTPUT_IDS = {
    219: "Heater",
    220: "Hot Tap Water",
    221: "Cold Pump",
    222: "Cold Pump Low",
    223: "Hot Side Pump",
    224: "Defrost Valve",
    225: "Solar Pump",
    227: "Aux Pump",
    228: "Alarm",
    232: "Cold Pump Volt",
    265: "HP Switch",
    266: "LP Switch",
    267: "BP Switch",
    268: "DF Start",
    269: "FC Switch",
}

ID_MAP = {
    # Temperature sensors
    253: ("heating_supply_temp", "°C", "temperature", "measurement", "Input.THeatSupply"),
    254: ("heating_return_temp", "°C", "temperature", "measurement", "Input.THeatReturn"),
    255: ("water_tank_temp", "°C", "temperature", "measurement", "Input.TWaterTank"),
    256: ("ambient_temp", "°C", "temperature", "measurement", "Input.Tamb"),
    257: ("room_temp", "°C", "temperature", "measurement", "Input.Troom"),
    259: ("heating_tank_temp", "°C", "temperature", "measurement", "Input.THeatTank"),
    260: ("cold_supply_temp", "°C", "temperature", "measurement", "Input.TColdSupply"),
    261: ("cold_return_temp", "°C", "temperature", "measurement", "Input.TColdReturn"),
    262: ("evaporator_temp", "°C", "temperature", "measurement", "Input.Tevap"),
    263: ("solar_water_temp", "°C", "temperature", "measurement", "Input.TSolarWater"),
    264: ("solar_panel_temp", "°C", "temperature", "measurement", "Input.TSolarPanel"),
    
    # Temperature setpoints and limits
    193: ("room_setpoint", "°C", "temperature", "measurement", "HeatSPCtrl.TroomSet"),
    383: ("hot_water_setpoint", "°C", "temperature", "measurement", "HotWater.SetPoint"),
    386: ("hot_water_setpoint_actual", "°C", "temperature", "measurement", "HotWater.SetPointAct"),
    382: ("hot_water_electric_limit_temp", "°C", "temperature", "measurement", "HotWater.TElecLimit"),
    384: ("hot_water_neutral_zone", "°C", "temperature", "measurement", "HotWater.NeutralZone"),
    385: ("hot_water_capacity", "%", None, "measurement", "HotWater.Capacity"),
    410: ("heating_setpoint_min", "°C", "temperature", "measurement", "Heating.SetPointMin"),
    411: ("heating_setpoint_max", "°C", "temperature", "measurement", "Heating.SetPointMax"),
    409: ("heating_setpoint_min_cool", "°C", "temperature", "measurement", "Heating.SetPMinCool"),
    420: ("heating_setpoint_actual", "°C", "temperature", "measurement", "Heating.SetPointAct"),
    419: ("heating_neutral_zone", "°C", "temperature", "measurement", "Heating.NeutralZone"),
    196: ("heating_offset", "°C", "temperature", "measurement", "HeatSPCtrl.ToffSet"),
    352: ("solar_start_temp_diff", "°C", "temperature", "measurement", "SolarPanel.TStartDiff"),
    353: ("solar_stop_temp_diff", "°C", "temperature", "measurement", "SolarPanel.TStopDiff"),
    354: ("solar_temp_max", "°C", "temperature", "measurement", "SolarPanel.TempMax"),
    356: ("solar_water_max_temp", "°C", "temperature", "measurement", "SolarPanel.WaterMT"),
    361: ("solar_start_temp", "°C", "temperature", "measurement", "SolarPanel.StartTemp"),
    
    # Defrost temperature settings
    513: ("defrost_frosting_temp", "°C", "temperature", "measurement", "Defrost.TFrosting"),
    516: ("defrost_relative_frost_temp", "°C", "temperature", "measurement", "Defrost.TRelFrost"),
    514: ("defrost_ice_melt_temp", "°C", "temperature", "measurement", "Defrost.TIceMelt"),
    515: ("defrost_melt_fast_temp", "°C", "temperature", "measurement", "Defrost.TMeltFast"),
    510: ("defrost_ff_ambient_min", "°C", "temperature", "measurement", "Defrost.FFTambMin"),
    511: ("defrost_ff_ambient_max", "°C", "temperature", "measurement", "Defrost.FFTambMax"),
    512: ("defrost_ff_evap_stop", "°C", "temperature", "measurement", "Defrost.FFTevapStop"),
    518: ("defrost_air_defrost_temp", "°C", "temperature", "measurement", "Defrost.TAirDfrTemp"),
    524: ("defrost_stop_temp", "°C", "temperature", "measurement", "Defrost.StopTemp"),
    
    # Capacity and performance metrics
    299: ("capacity_actual", "%", None, "measurement", "HeatPump.CapacityAct"),
    300: ("capacity_requested", "%", None, "measurement", "HeatPump.CapacityReq"),
    433: ("compressor_output", None, None, "measurement", "Compressor.Output"),
    405: ("heating_stop_capacity_1", "%", None, "measurement", "Heating.StopCap1"),
    406: ("heating_stop_capacity_2", "%", None, "measurement", "Heating.StopCap2"),
    407: ("heating_start_diff_capacity", "%", None, "measurement", "Heating.StartDifCap"),
    529: ("defrost_capacity", "%", None, "measurement", "Defrost.DefrostCap"),
    
    # Compressor parameters
    435: ("compressor_gain", None, None, "measurement", "Compressor.Gain"),
    436: ("compressor_tn", None, None, "measurement", "Compressor.Tn"),
    430: ("compressor_min_voltage", "V", None, "measurement", "Compressor.MinVoltage"),
    429: ("compressor_max_voltage", "V", None, "measurement", "Compressor.MaxVoltage"),
    428: ("compressor_start_voltage", "V", None, "measurement", "Compressor.UStart"),
    427: ("compressor_min_stop", None, None, "measurement", "Compressor.MinCprStop"),
    447: ("compressor_runtime", "h", None, "total_increasing", "Compressor.CompRunTime"),
    
    # Runtime counters (diagnostic)
    301: ("heatpump_runtime", "h", None, "total_increasing", "HeatPump.RunTime"),
    302: ("heatpump_ap_runtime", "h", None, "total_increasing", "HeatPump.APRunTime"),
    303: ("heatpump_hsp_runtime", "h", None, "total_increasing", "HeatPump.HSPRunTime"),
    376: ("cold_pump_runtime", "h", None, "total_increasing", "ColdPump.CPRunTime"),
    387: ("hot_water_runtime", "h", None, "total_increasing", "HotWater.RunTime"),
    423: ("heating_electric_runtime", "h", None, "total_increasing", "Heating.ElecRunTime"),
    362: ("solar_panel_runtime", "h", None, "total_increasing", "SolarPanel.RunTime"),
    
    # System states and modes
    297: ("heatpump_state", None, None, None, "HeatPump.State"),
    296: ("heatpump_season_state", None, None, None, "HeatPump.SeasonState"),
    364: ("solar_panel_state", None, None, None, "SolarPanel.State"),
    374: ("cold_pump_state", None, None, None, "ColdPump.State"),
    503: ("legionella_state", None, None, None, "Legionella.State"),
    278: ("season_mode", None, None, None, "Parameters.SeasonMode"),
    403: ("heating_source", None, None, None, "Heating.Source"),
    380: ("hot_water_source", None, None, None, "HotWater.Source"),
    404: ("heating_control_mode", None, None, None, "Heating.CtrlMode"),
    453: ("compressor_control_mode", None, None, None, "CprControl.CprMode"),
    367: ("cold_pump_mode", None, None, None, "ColdPump.Mode"),
    509: ("defrost_mode", None, None, None, "Defrost.Mode"),
    390: ("concrete_mode", None, None, None, "Concrete.Mode"),
    
    # Binary outputs and switches
    219: ("heater_output", None, None, None, "Output.Heater"),
    220: ("hot_tap_water_output", None, None, None, "Output.HotTapWater"),
    221: ("cold_pump_output", None, None, None, "Output.ColdPump"),
    222: ("cold_pump_low_output", None, None, None, "Output.ColdPumpLow"),
    223: ("hot_side_pump_output", None, None, None, "Output.HotSidePump"),
    224: ("defrost_valve_output", None, None, None, "Output.DefrostValve"),
    225: ("solar_pump_output", None, None, None, "Output.SolarPump"),
    227: ("aux_pump_output", None, None, None, "Output.AuxPump"),
    228: ("alarm_output", None, None, None, "Output.Alarm"),
    232: ("cold_pump_voltage_output", None, None, None, "Output.ColdPumpVolt"),
    265: ("hp_switch_status", None, None, None, "Input.HPSwitch"),
    266: ("lp_switch_status", None, None, None, "Input.LPSwitch"),
    267: ("bp_switch_status", None, None, None, "Input.BPSwitch"),
    268: ("df_start_status", None, None, None, "Input.DFStart"),
    269: ("fc_switch_status", None, None, None, "Input.FCSwitch"),
    
    # Cold pump parameters
    368: ("cold_pump_stop_delay", None, None, None, "ColdPump.StopDelay"),
    369: ("cold_pump_high_speed_capacity", "%", None, "measurement", "ColdPump.HSpeedCap"),
    370: ("cold_pump_high_speed_neutral_zone", "%", None, "measurement", "ColdPump.HSpeedNZ"),
    371: ("cold_pump_high_speed_voltage", "V", None, "measurement", "ColdPump.HSpeedVolt"),
    372: ("cold_pump_low_speed_voltage", "V", None, "measurement", "ColdPump.LSpeedVolt"),
    
    # Heating curve parameters
    184: ("heat_sp_ctrl_type", None, None, None, "HeatSPCtrl.Type"),
    192: ("heat_sp_ctrl_curve", None, None, None, "HeatSPCtrl.Curve"),
    185: ("heat_sp_ctrl_curve_point_1", "°C", "temperature", "measurement", "HeatSPCtrl.CurPnt1"),
    186: ("heat_sp_ctrl_curve_point_2", "°C", "temperature", "measurement", "HeatSPCtrl.CurPnt2"),
    187: ("heat_sp_ctrl_curve_point_3", "°C", "temperature", "measurement", "HeatSPCtrl.CurPnt3"),
    188: ("heat_sp_ctrl_curve_point_4", "°C", "temperature", "measurement", "HeatSPCtrl.CurPnt4"),
    189: ("heat_sp_ctrl_curve_point_5", "°C", "temperature", "measurement", "HeatSPCtrl.CurPnt5"),
    190: ("heat_sp_ctrl_curve_point_6", "°C", "temperature", "measurement", "HeatSPCtrl.CurPnt6"),
    191: ("heat_sp_ctrl_curve_point_7", "°C", "temperature", "measurement", "HeatSPCtrl.CurPnt7"),
    197: ("heat_sp_ctrl_ambient_cmp_max", "°C", "temperature", "measurement", "HeatSPCtrl.AmbCmpMax"),
    
    # System parameters
    284: ("hp_stop_seconds", None, None, None, "Parameters.HPStopS"),
    285: ("total_stop_seconds", None, None, None, "Parameters.TotalStopS"),
    281: ("hp_stop_temperature", "°C", "temperature", "measurement", "Parameters.HPStopT"),
    283: ("total_stop_temperature", "°C", "temperature", "measurement", "Parameters.TotalStopT"),
    282: ("hp_ambient_stop_temperature", "°C", "temperature", "measurement", "Parameters.HPAmbStopT"),
    286: ("pump_exercise_interval", None, None, None, "Parameters.PumpExInter"),
    280: ("startup_time", None, None, None, "Parameters.StartUpTime"),
    408: ("heating_electric_delay", None, None, None, "Heating.ElecDelay"),
    413: ("heating_evaporator_min_temp", "°C", "temperature", "measurement", "Heating.TEvapMin"),
    421: ("heating_min_heat_time", None, None, None, "Heating.MinHeatTime"),
    
    # Defrost parameters
    517: ("defrost_relative_frost_compressor", None, None, None, "Defrost.RelFrostCmp"),
    520: ("defrost_time_in", None, None, None, "Defrost.DefrTimeIn"),
    522: ("defrost_min_interval", None, None, None, "Defrost.MinInterval"),
    521: ("defrost_max_time", None, None, None, "Defrost.MaxTime"),
    523: ("defrost_drip_down_delay_1", None, None, None, "Defrost.DripDownDel1"),
    
    # Legionella parameters
    500: ("legionella_wait_time", None, None, None, "Legionella.WaitTime"),
    501: ("legionella_treatment_temp", "°C", "temperature", "measurement", "Legionella.TreatTemp"),
    504: ("legionella_timeout_1", None, None, None, "Legionella.Timeout1"),
    
    # Solar panel parameters
    351: ("solar_panel_sensor_select", None, None, None, "SolarPanel.SensorSelect"),
    
    # Manual controls (service)
    235: ("manual_compressor_1", None, None, None, "Manual.Compressor1"),
    236: ("manual_heater", None, None, None, "Manual.Heater"),
    237: ("manual_hot_tap_water", None, None, None, "Manual.HotTapWater"),
    238: ("manual_cold_pump", None, None, None, "Manual.ColdPump"),
    239: ("manual_cold_pump_low", None, None, None, "Manual.ColdPumpLow"),
    240: ("manual_hot_side_pump", None, None, None, "Manual.HotSidePump"),
    241: ("manual_defrost_valve", None, None, None, "Manual.DefrostValve"),
    242: ("manual_solar_pump", None, None, None, "Manual.SolarPump"),
    243: ("manual_re6", None, None, None, "Manual.RE6"),
    244: ("manual_aux_pump", None, None, None, "Manual.AuxPump"),
    245: ("manual_alarm", None, None, None, "Manual.Alarm"),
    250: ("manual_cold_pump_voltage", None, None, None, "Manual.ColdPumpVolt"),
    
    # Service counters
    525: ("defrost_hot_gas_count", None, None, "total_increasing", "Defrost.DefrHGCount"),
    526: ("defrost_air_count", None, None, "total_increasing", "Defrost.DefrAirCnt"),
    
    # System information (diagnostic)
    37: ("app_version", None, None, None, "Info.AppVersion"),
    53: ("ip_address", None, None, None, "Com.IpAdr"),
    52: ("mac_address", None, None, None, "Com.MacAdr"),
    555: ("lup200_software_version", None, None, None, "Misc.LUP200SWVer"),
    
    # Configuration parameters
    137: ("user_language", None, None, None, "User.Language"),
    291: ("display_mode", None, None, None, "Parameters.DisplayMode"),
    277: ("main_switch", None, None, None, "Parameters.MainSwitch"),
    
    # Time settings
    113: ("time_year", None, None, None, "Time.Year"),
    112: ("time_month", None, None, None, "Time.Month"),
    110: ("time_day", None, None, None, "Time.Day"),
    109: ("time_hour", None, None, None, "Time.Hour"),
    108: ("time_minute", None, None, None, "Time.Minute"),
}

# JSON API Helper Functions
def parse_id_list(id_list_str):
    """Parse a semicolon or comma-separated ID list string into a list of integers.
    
    Args:
        id_list_str (str): Semicolon or comma-separated ID list string
        
    Returns:
        list[int]: List of integer IDs
        
    Raises:
        ValueError: If the ID list format is invalid
    """
    if not id_list_str:
        return []
    
    try:
        # Support both semicolon and comma separators
        separator = ";" if ";" in id_list_str else ","
        return [int(id_str.strip()) for id_str in id_list_str.split(separator) if id_str.strip()]
    except (ValueError, AttributeError) as err:
        raise ValueError(f"Invalid ID list format: {id_list_str}") from err


def get_entity_info(entity_id):
    """Get entity information from ID_MAP.
    
    Args:
        entity_id (int): The entity ID to look up
        
    Returns:
        tuple: (entity_key, unit, device_class, state_class, original_name) or None if not found
    """
    return ID_MAP.get(entity_id)


def is_binary_output(entity_id):
    """Check if an ID is a binary output (should be exposed as binary_sensor).
    
    Args:
        entity_id (int): The entity ID to check
        
    Returns:
        bool: True if the ID is a binary output, False otherwise
    """
    return entity_id in BINARY_OUTPUT_IDS


def get_original_name(entity_id):
    """Get the original name for an entity ID for diagnostics.
    
    Args:
        entity_id (int): The entity ID to look up
        
    Returns:
        str: The original name or None if not found
    """
    entity_info = ID_MAP.get(entity_id)
    if entity_info and len(entity_info) >= 5:
        return entity_info[4]
    return None


def get_binary_output_name(entity_id):
    """Get the display name for a binary output ID.
    
    Args:
        entity_id (int): The binary output ID to look up
        
    Returns:
        str: The display name or None if not found
    """
    return BINARY_OUTPUT_IDS.get(entity_id)


def validate_id_list(id_list_str):
    """Validate that all IDs in the list are valid integers and exist in ID_MAP.
    
    Args:
        id_list_str (str): Semicolon-separated ID list string
        
    Returns:
        bool: True if all IDs are valid, False otherwise
    """
    if not id_list_str:
        return True
    
    try:
        ids = parse_id_list(id_list_str)
        return all(entity_id in ID_MAP for entity_id in ids)
    except ValueError:
        return False


def parse_items(items_list):
    """Parse a list of JSON items with id, name, and value fields.
    
    Args:
        items_list (list): List of dictionaries with 'id', 'name', and 'value' fields
        
    Returns:
        dict[int]: Dictionary mapping integer IDs to (name, parsed_value) tuples
        
    Note:
        This function is more resilient to missing fields and will not raise exceptions
        for invalid items. It will log warnings for problematic items but continue processing.
    """
    result = {}
    
    if not items_list:
        _LOGGER.debug("Empty items list provided to parse_items")
        return result
    
    _LOGGER.debug("Parsing %d items from JSON response", len(items_list))
    
    for item in items_list:
        try:
            # Validate item structure
            if not isinstance(item, dict):
                _LOGGER.warning("Skipping invalid item (not a dict): %s", item)
                continue
                
            # More flexible field validation - allow missing 'name' field
            if 'id' not in item or 'value' not in item:
                _LOGGER.warning("Skipping item missing required fields (id/value): %s", item)
                continue
            
            # Extract and validate ID
            try:
                entity_id = int(item['id'])
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid ID '%s' in item: %s", item.get('id'), item)
                continue
            
            # Extract name or create default if missing
            if 'name' in item and item['name']:
                name = str(item['name'])
            else:
                name = f"entity_{entity_id}"
                _LOGGER.debug("Generated default name '%s' for item ID %s", name, entity_id)
            
            # Parse value with proper type conversion
            raw_value = item['value']
            
            # Parse value with proper error handling - don't fall back to raw values
            # This prevents type mismatches in the data pipeline
            try:
                parsed_value = _parse_value(raw_value)
                if parsed_value is None:
                    _LOGGER.warning("VALUE PARSING RETURNED NULL: id=%s, raw_value=%s - entity will be excluded from results",
                                   entity_id, raw_value)
                    # Skip adding this entity to results when parsing returns None
                    continue
            except Exception as err:
                _LOGGER.error("VALUE PARSING FAILED: id=%s, raw_value=%s, error=%s - entity will be excluded from results",
                              entity_id, raw_value, err)
                # Skip adding this entity to results when parsing fails
                continue
            
            # Only add entities with successfully parsed values to results
            result[entity_id] = (name, parsed_value)
            _LOGGER.debug("Successfully parsed item ID %s: %s = %s", entity_id, name, parsed_value)
            
            # Add enhanced logging for debugging parsing successes
            _LOGGER.info("SUCCESSFULLY PARSED: ID=%s, Name=%s, RawValue=%s -> ParsedValue=%s (type: %s)",
                         entity_id, name, raw_value, parsed_value, type(parsed_value).__name__)
            
        except Exception as err:
            _LOGGER.warning("Error parsing item %s: %s", item, err)
            # Continue processing other items instead of failing completely
            continue
    
    _LOGGER.info("PARSING SUMMARY: Successfully parsed %d items with valid values out of %d total items",
                 len(result), len(items_list))
    _LOGGER.debug("Final parsed entities: %s", list(result.keys()))
    return result


def _parse_value(value):
    """Parse a value string to the appropriate type.
    
    Args:
        value: The value to parse (typically a string)
        
    Returns:
        The parsed value (float, int, or string, or None for empty values)
    """
    if value is None or value == "":
        return None
    
    # Handle boolean values directly
    if isinstance(value, bool):
        return value
    
    # Convert to string for processing
    if not isinstance(value, str):
        value = str(value)
    
    value = value.strip()
    
    if not value:
        return None
    
    # Check if it's a float (contains decimal point)
    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass
    
    # Check if it's a boolean-like value (0/1)
    if value == "0":
        return False
    elif value == "1":
        return True
    
    # Check if it's an integer (all digits, possibly with sign)
    if value.lstrip("-+").isdigit():
        try:
            return int(value)
        except ValueError:
            pass
    
    # Return as string if no conversion worked
    return value