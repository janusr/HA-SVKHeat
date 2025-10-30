from typing import Any, Dict, Optional, List
import warnings

# Entity definitions
ENTITIES = {
    "display_heatpump_state": {
        "name": "HeatPump.State",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 297,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_input_theatsupply": {
        "name": "Input.THeatSupply",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 253,
        "access_type": "read",
    },
    "display_input_theatreturn": {
        "name": "Input.THeatReturn",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 254,
        "access_type": "read",
    },
    "display_input_twatertank": {
        "name": "Input.TWaterTank",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 255,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_input_tamb": {
        "name": "Input.Tamb",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 256,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_input_troom": {
        "name": "Input.Troom",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 257,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_input_theattank": {
        "name": "Input.THeatTank",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 259,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_input_tcoldsupply": {
        "name": "Input.TColdSupply",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 260,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_input_tcoldreturn": {
        "name": "Input.TColdReturn",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 261,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_input_tevap": {
        "name": "Input.Tevap",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 262,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_heating_setpointact": {
        "name": "Heating.SetPointAct",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 530,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_hotwater_setpointact": {
        "name": "HotWater.SetPointAct",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 386,
        "access_type": "read",
    },
    "display_solarpanel_state": {
        "name": "SolarPanel.State",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 364,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_input_tsolarpanel": {
        "name": "Input.TSolarPanel",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 264,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_input_tsolarwater": {
        "name": "Input.TSolarWater",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "temperature",
        "unit": "°C",
        "id": 263,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "display_heatpump_seasonstate": {
        "name": "HeatPump.SeasonState",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 296,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_coldpump_state": {
        "name": "ColdPump.State",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 374,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_legionella_state": {
        "name": "Legionella.State",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 503,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_heatpump_capacityreq": {
        "name": "HeatPump.CapacityReq",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "percentage",
        "unit": "%",
        "id": 300,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "read",
    },
    "display_compressor_output": {
        "name": "Compressor.Output",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 433,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "read",
    },
    "display_heatpump_capacityact": {
        "name": "HeatPump.CapacityAct",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "percentage",
        "unit": "%",
        "id": 299,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "read",
    },
    "display_hotwater_source": {
        "name": "HotWater.Source",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "number",
        "id": 532,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_heating_source": {
        "name": "Heating.Source",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "number",
        "id": 531,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_heater": {
        "name": "Output.Heater",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 219,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_hottapwater": {
        "name": "Output.HotTapWater",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 220,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_coldpump": {
        "name": "Output.ColdPump",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 221,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_coldpumplow": {
        "name": "Output.ColdPumpLow",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 222,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_hotsidepump": {
        "name": "Output.HotSidePump",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 223,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_defrostvalve": {
        "name": "Output.DefrostValve",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 224,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_solarpump": {
        "name": "Output.SolarPump",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 225,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_auxpump": {
        "name": "Output.AuxPump",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 227,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_alarm": {
        "name": "Output.Alarm",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 228,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_output_coldpumpvolt": {
        "name": "Output.ColdPumpVolt",
        "platform": "sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "voltage",
        "unit": "V",
        "id": 232,
        "access_type": "read",
    },
    "display_manual_coldpumpvolt": {
        "name": "Manual.ColdPumpVolt",
        "platform": "number",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "voltage",
        "unit": "V",
        "min_value": 0,
        "max_value": 10,
        "step": 0.1,
        "id": 250,
        "access_type": "readwrite",
    },
    "display_input_hpswitch": {
        "name": "Input.HPSwitch",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 265,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_input_lpswitch": {
        "name": "Input.LPSwitch",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 266,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_input_bpswitch": {
        "name": "Input.BPSwitch",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 267,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_input_dfstart": {
        "name": "Input.DFStart",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 268,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "display_input_fcswitch": {
        "name": "Input.FCSwitch",
        "platform": "binary_sensor",
        "category": "Operation",
        "group": "Display",
        "page": "display",
        "data_type": "boolean",
        "id": 269,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "heating_heating_source": {
        "name": "Heating.Source",
        "platform": "select",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "enum",
        "id": 403,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heating_heating_setpointmin": {
        "name": "Heating.SetPointMin",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 10,
        "max_value": 40,
        "step": 1,
        "id": 410,
        "access_type": "readwrite",
    },
    "heating_heating_setpointmax": {
        "name": "Heating.SetPointMax",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 20,
        "max_value": 60,
        "step": 1,
        "id": 411,
        "access_type": "readwrite",
    },
    "heating_heating_setpmincool": {
        "name": "Heating.SetPMinCool",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 5,
        "max_value": 25,
        "step": 1,
        "id": 409,
        "access_type": "readwrite",
    },
    "heating_heating_setpointact": {
        "name": "Heating.SetPointAct",
        "platform": "sensor",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "id": 420,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
    "heating_heating_neutralzone": {
        "name": "Heating.NeutralZone",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 5,
        "step": 0.1,
        "id": 419,
        "access_type": "readwrite",
    },
    "heating_heating_stopcap1": {
        "name": "Heating.StopCap1",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "percentage",
        "unit": "%",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 405,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heating_heating_stopcap2": {
        "name": "Heating.StopCap2",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "percentage",
        "unit": "%",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 406,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heating_heating_startdifcap": {
        "name": "Heating.StartDifCap",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "percentage",
        "unit": "%",
        "min_value": 0,
        "max_value": 50,
        "step": 1,
        "id": 407,
        "access_type": "readwrite",
    },
    "heating_compressor_minvoltage": {
        "name": "Compressor.MinVoltage",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "voltage",
        "unit": "V",
        "min_value": 180,
        "max_value": 250,
        "step": 1,
        "id": 430,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heating_compressor_maxvoltage": {
        "name": "Compressor.MaxVoltage",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "voltage",
        "unit": "V",
        "min_value": 200,
        "max_value": 280,
        "step": 1,
        "id": 429,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heating_compressor_ustart": {
        "name": "Compressor.UStart",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "voltage",
        "unit": "V",
        "min_value": 180,
        "max_value": 250,
        "step": 1,
        "id": 428,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heating_compressor_gain": {
        "name": "Compressor.Gain",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "number",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 435,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heating_compressor_tn": {
        "name": "Compressor.Tn",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "time",
        "unit": "s",
        "min_value": 0,
        "max_value": 1000,
        "step": 1,
        "id": 436,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heating_heating_tevapmin": {
        "name": "Heating.TEvapMin",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 0,
        "step": 1,
        "id": 413,
        "access_type": "readwrite",
    },
    "heating_heating_minheattime": {
        "name": "Heating.MinHeatTime",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "time",
        "unit": "min",
        "min_value": 0,
        "max_value": 60,
        "step": 1,
        "id": 421,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_type": {
        "name": "HeatSPCtrl.Type",
        "platform": "select",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "enum",
        "id": 184,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curve": {
        "name": "HeatSPCtrl.Curve",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "number",
        "min_value": 0,
        "max_value": 10,
        "step": 1,
        "id": 192,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curpnt1": {
        "name": "HeatSPCtrl.CurPnt1",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 40,
        "step": 1,
        "id": 185,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curpnt2": {
        "name": "HeatSPCtrl.CurPnt2",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 40,
        "step": 1,
        "id": 186,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curpnt3": {
        "name": "HeatSPCtrl.CurPnt3",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 40,
        "step": 1,
        "id": 187,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curpnt4": {
        "name": "HeatSPCtrl.CurPnt4",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 40,
        "step": 1,
        "id": 188,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curpnt5": {
        "name": "HeatSPCtrl.CurPnt5",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 40,
        "step": 1,
        "id": 189,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curpnt6": {
        "name": "HeatSPCtrl.CurPnt6",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 40,
        "step": 1,
        "id": 190,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_curpnt7": {
        "name": "HeatSPCtrl.CurPnt7",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 40,
        "step": 1,
        "id": 191,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_ambcmpmax": {
        "name": "HeatSPCtrl.AmbCmpMax",
        "platform": "number",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 40,
        "step": 1,
        "id": 197,
        "access_type": "readwrite",
    },
    "heating_heatspctrl_toffset": {
        "name": "HeatSPCtrl.ToffSet",
        "platform": "switch",
        "category": "Settings",
        "group": "Heating",
        "page": "settings_heating",
        "data_type": "boolean",
        "id": 434,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_parameters_hpstops": {
        "name": "Parameters.HPStopS",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "time",
        "unit": "s",
        "min_value": 0,
        "max_value": 300,
        "step": 1,
        "id": 284,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_parameters_totalstops": {
        "name": "Parameters.TotalStopS",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "time",
        "unit": "s",
        "min_value": 0,
        "max_value": 600,
        "step": 1,
        "id": 285,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_parameters_hpstopt": {
        "name": "Parameters.HPStopT",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 50,
        "step": 1,
        "id": 281,
        "access_type": "readwrite",
    },
    "heatpump_parameters_totalstopt": {
        "name": "Parameters.TotalStopT",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 50,
        "step": 1,
        "id": 283,
        "access_type": "readwrite",
    },
    "heatpump_parameters_hpambstopt": {
        "name": "Parameters.HPAmbStopT",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 50,
        "step": 1,
        "id": 282,
        "access_type": "readwrite",
    },
    "heatpump_heating_ctrlmode": {
        "name": "Heating.CtrlMode",
        "platform": "select",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "enum",
        "id": 404,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_cprcontrol_cprmode": {
        "name": "CprControl.CprMode",
        "platform": "select",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "enum",
        "id": 453,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_compressor_mincprstop": {
        "name": "Compressor.MinCprStop",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "time",
        "unit": "s",
        "min_value": 0,
        "max_value": 300,
        "step": 1,
        "id": 427,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "heatpump_heating_elecdelay": {
        "name": "Heating.ElecDelay",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "time",
        "unit": "min",
        "min_value": 0,
        "max_value": 60,
        "step": 1,
        "id": 408,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_parameters_pumpexinter": {
        "name": "Parameters.PumpExInter",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "time",
        "unit": "s",
        "min_value": 0,
        "max_value": 300,
        "step": 1,
        "id": 286,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_parameters_startuptime": {
        "name": "Parameters.StartUpTime",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "time",
        "unit": "min",
        "min_value": 0,
        "max_value": 60,
        "step": 1,
        "id": 280,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_coldpump_stopdelay": {
        "name": "ColdPump.StopDelay",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "time",
        "unit": "s",
        "min_value": 0,
        "max_value": 300,
        "step": 1,
        "id": 368,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_coldpump_mode": {
        "name": "ColdPump.Mode",
        "platform": "select",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "enum",
        "id": 367,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "heatpump_coldpump_hspeedcap": {
        "name": "ColdPump.HSpeedCap",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "percentage",
        "unit": "%",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 369,
        "access_type": "readwrite",
    },
    "heatpump_coldpump_hspeednz": {
        "name": "ColdPump.HSpeedNZ",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "percentage",
        "unit": "%",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 370,
        "access_type": "readwrite",
    },
    "heatpump_coldpump_hspeedvolt": {
        "name": "ColdPump.HSpeedVolt",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "voltage",
        "unit": "V",
        "min_value": 0,
        "max_value": 10,
        "step": 0.1,
        "id": 371,
        "access_type": "readwrite",
    },
    "heatpump_coldpump_lspeedvolt": {
        "name": "ColdPump.LSpeedVolt",
        "platform": "number",
        "category": "Settings",
        "group": "Heatpump",
        "page": "settings_heatpump",
        "data_type": "voltage",
        "unit": "V",
        "min_value": 0,
        "max_value": 10,
        "step": 0.1,
        "id": 372,
        "access_type": "readwrite",
    },
    "hotwater_hotwater_source": {
        "name": "HotWater.Source",
        "platform": "select",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "enum",
        "id": 380,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "hotwater_hotwater_setpoint": {
        "name": "HotWater.SetPoint",
        "platform": "number",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 40,
        "max_value": 65,
        "step": 1,
        "id": 383,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "readwrite",
    },
    "hotwater_hotwater_neutralzone": {
        "name": "HotWater.NeutralZone",
        "platform": "switch",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "boolean",
        "id": 384,
        "access_type": "readwrite",
    },
    "hotwater_hotwater_capacity": {
        "name": "HotWater.Capacity",
        "platform": "number",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "percentage",
        "unit": "%",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 385,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "hotwater_hotwater_teleclimit": {
        "name": "HotWater.TElecLimit",
        "platform": "number",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 382,
        "access_type": "readwrite",
    },
    "hotwater_legionella_waittime": {
        "name": "Legionella.WaitTime",
        "platform": "number",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "time",
        "unit": "days",
        "min_value": 1,
        "max_value": 30,
        "step": 1,
        "id": 500,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "hotwater_legionella_treattemp": {
        "name": "Legionella.TreatTemp",
        "platform": "number",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 60,
        "max_value": 75,
        "step": 1,
        "id": 501,
        "access_type": "readwrite",
    },
    "hotwater_legionella_timeout1": {
        "name": "Legionella.Timeout1",
        "platform": "number",
        "category": "Settings",
        "group": "Hot water",
        "page": "settings_hotwater",
        "data_type": "time",
        "unit": "h",
        "min_value": 1,
        "max_value": 24,
        "step": 1,
        "id": 504,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_info_appversion": {
        "name": "Info.AppVersion",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "string",
        "id": 37,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "service_com_ipadr": {
        "name": "Com.IpAdr",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "string",
        "id": 53,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "service_com_macadr": {
        "name": "Com.MacAdr",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "string",
        "id": 52,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "service_parameters_displaymode": {
        "name": "Parameters.DisplayMode",
        "platform": "select",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "enum",
        "id": 291,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_parameters_mainswitch": {
        "name": "Parameters.MainSwitch",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 277,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_compressor1": {
        "name": "Manual.Compressor1",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 235,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_re6": {
        "name": "Manual.RE6",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 243,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_heater": {
        "name": "Manual.Heater",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 236,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_hottapwater": {
        "name": "Manual.HotTapWater",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 237,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_coldpump": {
        "name": "Manual.ColdPump",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 238,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_coldpumplow": {
        "name": "Manual.ColdPumpLow",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 239,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_hotsidepump": {
        "name": "Manual.HotSidePump",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 240,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_defrostvalve": {
        "name": "Manual.DefrostValve",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 241,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_solarpump": {
        "name": "Manual.SolarPump",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 242,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_auxpump": {
        "name": "Manual.AuxPump",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 244,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_manual_alarm": {
        "name": "Manual.Alarm",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 245,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "service_heatpump_runtime": {
        "name": "HeatPump.RunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 301,
        "device_class": None,
        "state_class": "total_increasing",
        "access_type": "read",
    },
    "service_compressor_compruntime": {
        "name": "Compressor.CompRunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 447,
        "access_type": "read",
    },
    "service_heating_elecruntime": {
        "name": "Heating.ElecRunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 423,
        "access_type": "read",
    },
    "service_hotwater_runtime": {
        "name": "HotWater.RunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 387,
        "device_class": None,
        "state_class": "total_increasing",
        "access_type": "read",
    },
    "service_coldpump_cpruntime": {
        "name": "ColdPump.CPRunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 376,
        "device_class": None,
        "state_class": "total_increasing",
        "access_type": "read",
    },
    "service_heatpump_hspruntime": {
        "name": "HeatPump.HSPRunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 303,
        "device_class": None,
        "state_class": "total_increasing",
        "access_type": "read",
    },
    "service_solarpanel_runtime": {
        "name": "SolarPanel.RunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 362,
        "device_class": None,
        "state_class": "total_increasing",
        "access_type": "read",
    },
    "service_heatpump_apruntime": {
        "name": "HeatPump.APRunTime",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "time",
        "unit": "h",
        "id": 302,
        "device_class": None,
        "state_class": "total_increasing",
        "access_type": "read",
    },
    "service_defrost_defrhgcount": {
        "name": "Defrost.DefrHGCount",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "number",
        "id": 525,
        "access_type": "read",
    },
    "service_defrost_defraircnt": {
        "name": "Defrost.DefrAirCnt",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "number",
        "id": 526,
        "device_class": None,
        "state_class": "total_increasing",
        "access_type": "read",
    },
    "service_concrete_mode": {
        "name": "Concrete.Mode",
        "platform": "switch",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "boolean",
        "id": 390,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "solar_solarpanel_state": {
        "name": "SolarPanel.State",
        "platform": "binary_sensor",
        "category": "Settings",
        "group": "Solar panel",
        "page": "settings_solar",
        "data_type": "boolean",
        "id": 535,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "solar_solarpanel_sensorselect": {
        "name": "SolarPanel.SensorSelect",
        "platform": "select",
        "category": "Settings",
        "group": "Solar panel",
        "page": "settings_solar",
        "data_type": "enum",
        "id": 351,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "solar_solarpanel_tstartdiff": {
        "name": "SolarPanel.TStartDiff",
        "platform": "number",
        "category": "Settings",
        "group": "Solar panel",
        "page": "settings_solar",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 20,
        "step": 1,
        "id": 352,
        "access_type": "readwrite",
    },
    "solar_solarpanel_tstopdiff": {
        "name": "SolarPanel.TStopDiff",
        "platform": "number",
        "category": "Settings",
        "group": "Solar panel",
        "page": "settings_solar",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 20,
        "step": 1,
        "id": 353,
        "access_type": "readwrite",
    },
    "solar_solarpanel_tempmax": {
        "name": "SolarPanel.TempMax",
        "platform": "number",
        "category": "Settings",
        "group": "Solar panel",
        "page": "settings_solar",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 40,
        "max_value": 80,
        "step": 1,
        "id": 354,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "readwrite",
    },
    "solar_solarpanel_watermt": {
        "name": "SolarPanel.WaterMT",
        "platform": "number",
        "category": "Settings",
        "group": "Solar panel",
        "page": "settings_solar",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 20,
        "max_value": 80,
        "step": 1,
        "id": 356,
        "access_type": "readwrite",
    },
    "solar_solarpanel_starttemp": {
        "name": "SolarPanel.StartTemp",
        "platform": "number",
        "category": "Settings",
        "group": "Solar panel",
        "page": "settings_solar",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 10,
        "max_value": 50,
        "step": 1,
        "id": 361,
        "access_type": "readwrite",
    },
    "user_user_language": {
        "name": "User.Language",
        "platform": "select",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "enum",
        "id": 137,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "user_heatspctrl_troomset": {
        "name": "HeatSPCtrl.TroomSet",
        "platform": "number",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 10,
        "max_value": 30,
        "step": 0.5,
        "id": 193,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "readwrite",
    },
    "user_hotwater_setpoint": {
        "name": "HotWater.SetPoint",
        "platform": "number",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 40,
        "max_value": 65,
        "step": 1,
        "id": 536,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "readwrite",
    },
    "user_heatspctrl_toffset": {
        "name": "HeatSPCtrl.ToffSet",
        "platform": "switch",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "boolean",
        "id": 196,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "readwrite",
    },
    "user_parameters_seasonmode": {
        "name": "Parameters.SeasonMode",
        "platform": "switch",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "boolean",
        "id": 278,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "system_systemview": {
        "name": "System View",
        "platform": "sensor",
        "category": "Configuration",
        "group": "System",
        "page": "systemview",
        "data_type": "temperature",
        "unit": "°C",
        "id": 1670,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "read",
    },
}

AVAILABLE_ENTITIES = {
    "defrost_defrost_mode": {
        "name": "Defrost.Mode",
        "platform": "select",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "enum",
        "id": 509,
        "access_type": "readwrite",
    },
    "defrost_defrost_tfrosting": {
        "name": "Defrost.TFrosting",
        "platform": "sensor",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "access_type": "read",
    },
    "defrost_defrost_trelfrost": {
        "name": "Defrost.TRelFrost",
        "platform": "sensor",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "id": 516,
        "access_type": "read",
    },
    "defrost_defrost_relfrostcmp": {
        "name": "Defrost.RelFrostCmp",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "number",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 517,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "defrost_defrost_defrtimein": {
        "name": "Defrost.DefrTimeIn",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "time",
        "unit": "min",
        "min_value": 0,
        "max_value": 60,
        "step": 1,
        "id": 520,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "defrost_defrost_mininterval": {
        "name": "Defrost.MinInterval",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "time",
        "unit": "min",
        "min_value": 0,
        "max_value": 240,
        "step": 1,
        "id": 522,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "defrost_defrost_stoptemp": {
        "name": "Defrost.StopTemp",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 20,
        "step": 1,
        "id": 524,
        "state_class": "measurement",
        "device_class": "temperature",
        "access_type": "readwrite",
    },
    "defrost_defrost_maxtime": {
        "name": "Defrost.MaxTime",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "time",
        "unit": "min",
        "min_value": 0,
        "max_value": 10,
        "step": 1,
        "id": 521,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "defrost_defrost_defrostcap": {
        "name": "Defrost.DefrostCap",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "percentage",
        "unit": "%",
        "min_value": 0,
        "max_value": 100,
        "step": 1,
        "id": 529,
        "device_class": None,
        "state_class": "measurement",
        "access_type": "readwrite",
    },
    "defrost_defrost_ticemelt": {
        "name": "Defrost.TIceMelt",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -5,
        "max_value": 5,
        "step": 1,
        "id": 514,
        "access_type": "readwrite",
    },
    "defrost_defrost_tmeltfast": {
        "name": "Defrost.TMeltFast",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 15,
        "step": 1,
        "id": 515,
        "access_type": "readwrite",
    },
    "defrost_defrost_tfrosting": {
        "name": "Defrost.TFrosting",
        "platform": "sensor",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "id": 513,
        "access_type": "read",
    },
    "defrost_defrost_fftambmin": {
        "name": "Defrost.FFTambMin",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -20,
        "max_value": 0,
        "step": 1,
        "id": 510,
        "access_type": "readwrite",
    },
    "defrost_defrost_fftambmax": {
        "name": "Defrost.FFTambMax",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 20,
        "step": 1,
        "id": 511,
        "access_type": "readwrite",
    },
    "defrost_defrost_fftevapstop": {
        "name": "Defrost.FFTevapStop",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": -5,
        "max_value": 10,
        "step": 1,
        "id": 512,
        "access_type": "readwrite",
    },
    "defrost_defrost_tairdfrtemp": {
        "name": "Defrost.TAirDfrTemp",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "temperature",
        "unit": "°C",
        "min_value": 0,
        "max_value": 50,
        "step": 1,
        "id": 518,
        "access_type": "readwrite",
    },
    "defrost_defrost_dripdowndel1": {
        "name": "Defrost.DripDownDel1",
        "platform": "number",
        "category": "Settings",
        "group": "Defrost",
        "page": "settings_defrost",
        "data_type": "time",
        "unit": "s",
        "min_value": 0,
        "max_value": 60,
        "step": 1,
        "id": 523,
        "device_class": None,
        "state_class": None,
        "access_type": "readwrite",
    },
    "user_time_year": {
        "name": "Time.Year",
        "platform": "sensor",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "number",
        "id": 113,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "service_misc_lup200swver": {
        "name": "Misc.LUP200SWVer",
        "platform": "sensor",
        "category": "Settings",
        "group": "Service",
        "page": "settings_service",
        "data_type": "string",
        "id": 555,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "user_time_month": {
        "name": "Time.Month",
        "platform": "sensor",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "number",
        "id": 112,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "user_time_day": {
        "name": "Time.Day",
        "platform": "sensor",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "number",
        "id": 110,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "user_time_hour": {
        "name": "Time.Hour",
        "platform": "sensor",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "number",
        "id": 109,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    },
    "user_time_minute": {
        "name": "Time.Minute",
        "platform": "sensor",
        "category": "Operation",
        "group": "User",
        "page": "user",
        "data_type": "number",
        "id": 108,
        "device_class": None,
        "state_class": None,
        "access_type": "read",
    }
}

# Moved from const.py - Temperature sensor definitions
TEMP_SENSORS = {
    "heating_supply_temp": {
        "name": "Heating Supply Temp",
        "label": "Heating supply",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "heating_return_temp": {
        "name": "Heating Return Temp",
        "label": "Heating return",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "water_tank_temp": {
        "name": "Water Tank Temp",
        "label": "Water tank",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "ambient_temp": {
        "name": "Ambient Temp",
        "label": "Ambient",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "room_temp": {
        "name": "Room Temp",
        "label": "Room",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "heating_tank_temp": {
        "name": "Heating Tank Temp",
        "label": "Heating tank",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "cold_side_supply_temp": {
        "name": "Cold Side Supply Temp",
        "label": "Cold side supply",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "cold_side_return_temp": {
        "name": "Cold Side Return Temp",
        "label": "Cold side return",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "evaporator_temp": {
        "name": "Evaporator Temp",
        "label": "Evaporator",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "solar_collector_temp": {
        "name": "Solar Collector Temp",
        "label": "Solar collector",
        "page": "solar",
        "category": "Settings",
        "group": "Solar panel",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "solar_water_temp": {
        "name": "Solar Water Temp",
        "label": "Solar water",
        "page": "solar",
        "category": "Settings",
        "group": "Solar panel",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
}

# Moved from const.py - Setpoint sensor definitions
SETPOINT_SENSORS = {
    "heating_setpoint": {
        "name": "Heating Set Point",
        "label": "Heating set point",
        "page": "user",
        "category": "Operation",
        "group": "User",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
    "hot_water_setpoint": {
        "name": "Hot Water Set Point",
        "label": "Hot water set point",
        "page": "user",
        "category": "Operation",
        "group": "User",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
    },
}

# Moved from const.py - Performance sensor definitions
PERFORMANCE_SENSORS = {
    "compressor_speed_v": {
        "name": "Compressor Speed",
        "label": "Compressor speed",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "V",
        "state_class": "measurement",
    },
    "compressor_speed_percent": {
        "name": "Compressor Speed",
        "label": "Compressor speed %",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "%",
        "state_class": "measurement",
    },
    "cold_pump_speed": {
        "name": "Cold Pump Speed",
        "label": "Cold pump speed",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "V",
        "state_class": "measurement",
    },
    "requested_capacity": {
        "name": "Requested Heating Capacity",
        "label": "Requested capacity",
        "page": "heating",
        "category": "Settings",
        "group": "Heating",
        "unit": "%",
        "state_class": "measurement",
    },
    "actual_capacity": {
        "name": "Actual Capacity",
        "label": "Actual capacity",
        "page": "heating",
        "category": "Settings",
        "group": "Heating",
        "unit": "%",
        "state_class": "measurement",
    },
}

# Moved from const.py - Counter sensor definitions (diagnostic)
COUNTER_SENSORS = {
    "compressor_runtime": {
        "name": "Compressor Runtime",
        "label": "Compressor runtime",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "heater_runtime": {
        "name": "Heater Runtime",
        "label": "Heater runtime",
        "page": "heating",
        "category": "Settings",
        "group": "Heating",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "pump_runtime": {
        "name": "Pump Runtime",
        "label": "Pump runtime",
        "page": "heating",
        "category": "Settings",
        "group": "Heating",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "heatpump_runtime": {
        "name": "Heat Pump Runtime",
        "label": "Heat pump runtime",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "hot_water_runtime": {
        "name": "Hot Water Runtime",
        "label": "Hot water runtime",
        "page": "hotwater",
        "category": "Settings",
        "group": "Hot water",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "cold_pump_runtime": {
        "name": "Cold Pump Runtime",
        "label": "Cold pump runtime",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "heatpump_ap_runtime": {
        "name": "Heat Pump AP Runtime",
        "label": "Heat pump AP runtime",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "heatpump_hsp_runtime": {
        "name": "Heat Pump HSP Runtime",
        "label": "Heat pump HSP runtime",
        "page": "heatpump",
        "category": "Settings",
        "group": "Heatpump",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "heating_electric_runtime": {
        "name": "Heating Electric Runtime",
        "label": "Heating electric runtime",
        "page": "heating",
        "category": "Settings",
        "group": "Heating",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "solar_panel_runtime": {
        "name": "Solar Panel Runtime",
        "label": "Solar panel runtime",
        "page": "solar",
        "category": "Settings",
        "group": "Solar panel",
        "unit": "h",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
}

# Moved from const.py - System information sensors (diagnostic)
SYSTEM_SENSORS = {
    "ip_address": {
        "name": "IP Address",
        "label": "IP address",
        "page": "display",
        "category": "Configuration",
        "group": "System",
        "entity_category": "diagnostic",
    },
    "mac_address": {
        "name": "MAC Address",
        "label": "MAC address",
        "page": "display",
        "category": "Configuration",
        "group": "System",
        "entity_category": "diagnostic",
    },
    "app_version": {
        "name": "App Version",
        "label": "App version",
        "page": "display",
        "category": "Configuration",
        "group": "System",
        "entity_category": "diagnostic",
    },
    "lup200_software_version": {
        "name": "LUP200 Software Version",
        "label": "LUP200 software version",
        "page": "display",
        "category": "Configuration",
        "group": "System",
        "entity_category": "diagnostic",
    },
    "software_version": {
        "name": "Software Version",
        "label": "Software version",
        "page": "display",
        "category": "Configuration",
        "group": "System",
        "entity_category": "diagnostic",
    },
    "log_interval": {
        "name": "Log Interval",
        "label": "Log interval",
        "page": "display",
        "category": "Configuration",
        "group": "System",
        "entity_category": "diagnostic",
    },
}

# Moved from const.py - System counter sensors (diagnostic)
SYSTEM_COUNTER_SENSORS = {
    "defrost_hot_gas_count": {
        "name": "Defrost Hot Gas Count",
        "label": "Defrost hot gas count",
        "page": "settings_service",
        "category": "Settings",
        "group": "Service",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
    "defrost_air_count": {
        "name": "Defrost Air Count",
        "label": "Defrost air count",
        "page": "settings_service",
        "category": "Settings",
        "group": "Service",
        "entity_category": "diagnostic",
        "state_class": "total_increasing",
    },
}

# Moved from const.py - Binary sensor definitions
BINARY_SENSORS = {
    "alarm_active": {
        "name": "Alarm Active",
        "label": "Alarm active",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "device_class": "problem",
    }
}

# Moved from const.py - Select entity definitions
SELECT_ENTITIES_LEGACY = {
    "heatpump_state": {
        "name": "Heat Pump State",
        "label": "Heat pump state",
        "page": "display",
        "category": "Operation",
        "group": "Display",
        "options": ["Off", "Ready", "Start up", "Heating", "Hot water", "El heating", "Defrost", "Drip delay", "Total stop", "Pump exercise", "Forced running", "Manual"],
        "mappings": {"Off": "off", "Ready": "ready", "Start up": "start_up", "Heating": "heating", "Hot water": "hot_water", "El heating": "el_heating", "Defrost": "defrost", "Drip delay": "drip_delay", "Total stop": "total_stop", "Pump exercise": "pump_exercise", "Forced running": "forced_running", "Manual": "manual"},
    },
    "solar_panel_state": {
        "name": "Solar Panel State",
        "label": "Solar panel state",
        "page": "solar",
        "category": "Settings",
        "group": "Solar panel",
        "options": ["Off", "Running", "Forced Stop"],
        "mappings": {"Off": "off", "Running": "running", "Forced Stop": "forced_stop"},
    },
    "season_mode": {
        "name": "Season Mode",
        "label": "Season mode",
        "page": "user",
        "category": "Operation",
        "group": "User",
        "options": ["Summer", "Winter", "Auto"],
        "mappings": {"Summer": "summer", "Winter": "winter", "Auto": "auto"},
        "writable": True,
    },
}

# Moved from const.py - Number entity definitions (writable)
NUMBER_ENTITIES_LEGACY = {
    "hot_water_setpoint": {
        "name": "Hot Water Set Point",
        "label": "Hot water set point",
        "page": "user",
        "category": "Operation",
        "group": "User",
        "min_value": 40,
        "max_value": 65,
        "step": 1,
        "unit": "°C",
        "device_class": "temperature",
    },
    "room_setpoint": {
        "name": "Room Set Point",
        "label": "Room set point",
        "page": "user",
        "category": "Operation",
        "group": "User",
        "min_value": 10,
        "max_value": 30,
        "step": 1,
        "unit": "°C",
        "device_class": "temperature",
    },
}

# ID_MAP has been successfully removed - all entity information is now directly available in the ENTITIES dictionary

# Function to generate default IDs from ENTITIES
def get_default_ids() -> str:
    """Generate default IDs from ENTITIES.
    
    Returns:
        str: Semicolon-separated string of entity IDs from ENTITIES
    """
    # Extract all entity IDs from ENTITIES, sort them for consistency
    all_ids = set()
    for entity_key, entity_data in ENTITIES.items():
        if "id" in entity_data:
            all_ids.add(entity_data["id"])
    
    return ";".join(str(id) for id in sorted(all_ids))







def get_id_map() -> dict[int, tuple[str, str, Any, Any, str]]:
    """Generate ID mapping from ENTITIES dictionary.
    
    Returns:
        Dictionary mapping entity IDs to (entity_key, unit, device_class, state_class, original_name)
    """
    id_map = {}
    for entity_key, entity_data in ENTITIES.items():
        if "id" in entity_data and entity_data["id"] is not None:
            entity_id = entity_data["id"]
            id_map[entity_id] = (
                entity_key,
                entity_data.get("unit", ""),
                entity_data.get("device_class"),
                entity_data.get("state_class"),
                entity_data.get("name", ""),
            )
    return id_map



# Moved from const.py - DEFAULT_ENABLED_ENTITIES
DEFAULT_ENABLED_ENTITIES = [
    # Operation/Display: Essential temperature sensors and heat pump state
    253,  # heating_supply_temp
    255,  # water_tank_temp
    257,  # room_temp
    297,  # heatpump_state
    # Operation/User: Key user-configurable parameters
    193,  # room_setpoint
    383,  # hot_water_setpoint
    278,  # season_mode
    137,  # user_language
    # Settings/Heatpump: Critical heat pump settings
    299,  # capacity_actual
    447,  # compressor_runtime
    433,  # compressor_output
    # Settings/Heating: Essential heating parameters
    420,  # heating_setpoint_actual
    403,  # heating_source
    404,  # heating_control_mode
    # Settings/Hot water: Key hot water settings
    380,  # hot_water_source
    386,  # hot_water_setpoint_actual
    220,  # hot_tap_water_output
    # Settings/Solar panel: Basic solar panel status
    364,  # solar_panel_state
    263,  # solar_water_temp
    # Settings/Service: Essential diagnostic entities
    228,  # alarm_output
    301,  # heatpump_runtime
    # Settings/Extended Display: Key extended display entities
    296,  # heatpump_season_state
    300,  # capacity_requested
]

# Moved from const.py - BINARY_OUTPUT_IDS
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


# Helper functions moved from const.py
def get_entity_info(entity_id: int):
    """Get entity information from ENTITIES.

    Args:
        entity_id (int): The entity ID to look up

    Returns:
        tuple: (entity_key, unit, device_class, state_class, original_name) or None if not found
    """
    # Find entity by ID in ENTITIES
    for entity_key, entity_data in ENTITIES.items():
        if "id" in entity_data and entity_data["id"] == entity_id:
            # Extract information from ENTITIES dictionary
            unit = entity_data.get("unit", "")
            device_class = entity_data.get("device_class", "")
            state_class = entity_data.get("state_class", "")
            original_name = entity_data.get("name", "")
            return (entity_key, unit, device_class, state_class, original_name)
    return None


def is_binary_output(entity_id):
    """Check if an ID is a binary output (should be exposed as binary_sensor).

    Args:
        entity_id (int): The entity ID to check

    Returns:
        bool: True if ID is a binary output, False otherwise
    """
    return entity_id in BINARY_OUTPUT_IDS


def get_original_name(entity_id: int):
    """Get original name for an entity ID for diagnostics.

    Args:
        entity_id (int): The entity ID to look up

    Returns:
        str: The original name or None if not found
    """
    # Find entity by ID in ENTITIES
    for entity_key, entity_data in ENTITIES.items():
        if "id" in entity_data and entity_data["id"] == entity_id:
            return entity_data.get("name")
    return None


def get_binary_output_name(entity_id: int):
    """Get display name for a binary output ID.

    Args:
        entity_id (int): The binary output ID to look up

    Returns:
        str: The display name or None if not found
    """
    return BINARY_OUTPUT_IDS.get(entity_id)


def get_entity_group_info(entity_id: int):
    """Get group information for a JSON API entity.

    Args:
        entity_id (int): The entity ID to look up

    Returns:
        dict: Dictionary with category and group information, or None if not found
    """
    # Find entity by ID in ENTITIES
    for entity_key, entity_data in ENTITIES.items():
        if "id" in entity_data and entity_data["id"] == entity_id:
            return {
                "category": entity_data.get("category"),
                "group": entity_data.get("group"),
            }
    return None


def get_entity_ids_by_group(category, group):
    """Get all entity IDs that belong to a specific category and group.

    Args:
        category (str): The category (Operation, Settings, Configuration)
        group (str): The group within category

    Returns:
        list[int]: List of entity IDs that belong to specified group
    """
    result = []

    for entity_key, entity_data in ENTITIES.items():
        if (
            entity_data.get("category") == category
            and entity_data.get("group") == group
            and "id" in entity_data
        ):
            result.append(entity_data["id"])

    return result


def get_all_entities() -> dict[str, dict[str, Any]]:
    """Return all entity definitions."""
    return ENTITIES


# ID_MAP has been successfully removed - all entity information is now directly available in ENTITIES

def get_entity_by_id(entity_id: int) -> Optional[Dict[str, Any]]:
    """Get entity definition by ID.

    Args:
        entity_id (int): The entity ID to look up

    Returns:
        dict: Entity definition or None if not found
    """
    # Find entity by ID in ENTITIES
    for entity_key, entity_data in ENTITIES.items():
        if "id" in entity_data and entity_data["id"] == entity_id:
            return entity_data
    return None


# ============================================================================
# UNIFIED ENTITIES ARCHITECTURE - Platform Filtering Functions
# ============================================================================

def get_sensor_entities() -> List[str]:
    """Return all sensor entity keys from ENTITIES."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("platform") == "sensor"]


def get_binary_sensor_entities() -> List[str]:
    """Return all binary sensor entity keys from ENTITIES."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("platform") == "binary_sensor"]


def get_number_entities() -> List[str]:
    """Return all number entity keys from ENTITIES."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("platform") == "number"]


def get_select_entities() -> List[str]:
    """Return all select entity keys from ENTITIES."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("platform") == "select"]


def get_switch_entities() -> List[str]:
    """Return all switch entity keys from ENTITIES."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("platform") == "switch"]


# ============================================================================
# ADVANCED FILTERING FUNCTIONS
# ============================================================================

def get_entities_by_platform(platform: str) -> List[str]:
    """Generic function to get entities by platform type."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("platform") == platform]


def get_entities_by_category(category: str) -> List[str]:
    """Return all entity keys for a specific category."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("category") == category]


def get_entities_by_group(category: str, group: str) -> List[str]:
    """Return all entity keys for a specific category and group."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("category") == category and entity.get("group") == group]


def get_writable_entities() -> List[str]:
    """Return all writable entity keys."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("access_type") == "readwrite"]


def get_entities_by_data_type(data_type: str) -> List[str]:
    """Return all entity keys for a specific data type."""
    return [key for key, entity in ENTITIES.items()
            if entity.get("data_type") == data_type]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_entity_platform(entity_key: str) -> Optional[str]:
    """Get platform type for an entity."""
    return ENTITIES.get(entity_key, {}).get("platform")


def is_entity_writable(entity_key: str) -> bool:
    """Check if an entity is writable."""
    return ENTITIES.get(entity_key, {}).get("access_type") == "readwrite"


def get_entity_config(entity_key: str) -> Dict[str, Any]:
    """Get full entity configuration."""
    return ENTITIES.get(entity_key, {})


def validate_entity_structure(entities: Dict[str, Dict[str, Any]]) -> bool:
    """Validate that all entities have required fields."""
    required_fields = ["name", "platform", "category", "group", "data_type"]
    for key, entity in entities.items():
        missing = [field for field in required_fields if field not in entity]
        if missing:
            import logging
            _LOGGER = logging.getLogger(__name__)
            _LOGGER.error("Entity %s missing required fields: %s", key, missing)
            return False
    return True


def get_entity_statistics() -> Dict[str, Any]:
    """Return statistics about entities by platform/category."""
    stats = {
        "by_platform": {},
        "by_category": {},
        "total": len(ENTITIES),
        "writable": len(get_writable_entities())
    }
    
    for entity in ENTITIES.values():
        platform = entity.get("platform", "unknown")
        category = entity.get("category", "unknown")
        
        stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1
        stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
    
    return stats


# ============================================================================
# BACKWARD COMPATIBILITY
# ============================================================================

def _get_legacy_platform_lists() -> Dict[str, List[str]]:
    """Generate legacy platform lists for backward compatibility."""
    return {
        "SENSOR_ENTITIES": get_sensor_entities(),
        "BINARY_SENSOR_ENTITIES": get_binary_sensor_entities(),
        "NUMBER_ENTITIES": get_number_entities(),
        "SELECT_ENTITIES": get_select_entities(),
        "SWITCH_ENTITIES": get_switch_entities(),
    }


def __getattr__(name: str) -> List[str]:
    """Provide backward compatibility with deprecation warnings."""
    if name in ["SENSOR_ENTITIES", "BINARY_SENSOR_ENTITIES", "NUMBER_ENTITIES",
                "SELECT_ENTITIES", "SWITCH_ENTITIES"]:
        warnings.warn(
            f"{name} is deprecated. Use get_{name.lower()}_entities() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        legacy_lists = _get_legacy_platform_lists()
        return legacy_lists[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
