#!/usr/bin/env python3
"""Script to analyze and compare IDs between ID_MAP and DEFAULT_IDS in const.py"""

import re

# Read the actual DEFAULT_IDS from the file
with open('custom_components/svk_heatpump/const.py', 'r') as f:
    content = f.read()
    
# Find the DEFAULT_IDS line using regex
match = re.search(r'DEFAULT_IDS = "([^"]+)"', content)
if match:
    DEFAULT_IDS = match.group(1)
else:
    print("ERROR: Could not find DEFAULT_IDS in const.py")
    exit(1)

# Parse DEFAULT_IDS into a set of integers
default_ids_set = set(int(id_str.strip()) for id_str in DEFAULT_IDS.split(";") if id_str.strip())

# Extract IDs from ID_MAP (lines 664-848)
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

# Get all IDs from ID_MAP
id_map_ids_set = set(ID_MAP.keys())

# Find discrepancies
missing_from_default_ids = id_map_ids_set - default_ids_set  # In ID_MAP but not in DEFAULT_IDS
extra_in_default_ids = default_ids_set - id_map_ids_set  # In DEFAULT_IDS but not in ID_MAP

print("=== ID ANALYSIS REPORT ===\n")

print(f"Total IDs in ID_MAP: {len(id_map_ids_set)}")
print(f"Total IDs in DEFAULT_IDS: {len(default_ids_set)}")
print(f"IDs in ID_MAP but missing from DEFAULT_IDS: {len(missing_from_default_ids)}")
print(f"IDs in DEFAULT_IDS but missing from ID_MAP: {len(extra_in_default_ids)}\n")

print("=== IMPORTANT MISSING IDs (Runtime & Diagnostic) ===")
# Focus on runtime entities and other important diagnostic entities
important_missing_ids = []
for id_num in sorted(missing_from_default_ids):
    entity_info = ID_MAP.get(id_num)
    if entity_info:
        entity_name = entity_info[0]
        # Check if it's a runtime entity or important diagnostic
        if ("runtime" in entity_name.lower() or 
            "count" in entity_name.lower() or
            entity_name in ["heatpump_runtime", "cold_pump_runtime", "heater_runtime", "pump_runtime"]):
            important_missing_ids.append((id_num, entity_name, entity_info[4]))

for id_num, name, orig_name in sorted(important_missing_ids):
    print(f"ID {id_num}: {name} ({orig_name})")

print("\n=== ALL MISSING IDS FROM DEFAULT_IDS ===")
for id_num in sorted(missing_from_default_ids):
    entity_info = ID_MAP.get(id_num)
    if entity_info:
        print(f"ID {id_num}: {entity_info[0]} ({entity_info[4]})")

print("\n=== EXTRA IDS IN DEFAULT_IDS (not in ID_MAP) ===")
for id_num in sorted(extra_in_default_ids):
    print(f"ID {id_num}")

print("\n=== UPDATED DEFAULT_IDS STRING ===")
# Create the updated DEFAULT_IDS string that includes all IDs from ID_MAP
all_ids = sorted(id_map_ids_set)
updated_default_ids = ";".join(str(id_num) for id_num in all_ids)
print(updated_default_ids)

print("\n=== VERIFICATION ===")
print(f"Original DEFAULT_IDS length: {len(DEFAULT_IDS)}")
print(f"Updated DEFAULT_IDS length: {len(updated_default_ids)}")
print(f"Number of added IDs: {len(missing_from_default_ids)}")