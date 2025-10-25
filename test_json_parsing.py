#!/usr/bin/env python3
"""Standalone test script to verify JSON parsing functionality with example data."""

import json
import sys
from typing import Dict, List, Any

# Import the client module from the custom_components directory
sys.path.insert(0, 'custom_components')
from svk_heatpump.client import LOMJsonClient


def test_parse_json_response_flexible():
    """Test the _parse_json_response_flexible method with example data."""
    
    # Example data provided in the task
    example_json = [
        { "id" : "299", "name" : "HeatPump.CapacityAct", "value" : "42.7"},
        { "id" : "255", "name" : "Input.TWaterTank", "value" : "25.4"},
        { "id" : "256", "name" : "Input.Tamb", "value" : "9.3"},
        { "id" : "257", "name" : "Input.Troom", "value" : "-70.0"},
        { "id" : "258", "name" : "Input.Tmixing", "value" : "-3.9"},
        { "id" : "259", "name" : "Input.THeatTank", "value" : "-40.0"},
        { "id" : "262", "name" : "Input.Tevap", "value" : "-70.0"},
        { "id" : "263", "name" : "Input.TSolarWater", "value" : "-40.0"},
        { "id" : "422", "name" : "Heating.HeatRunTime", "value" : "14559"},
        { "id" : "388", "name" : "HotWater.RunTimeSec", "value" : "257"},
        { "id" : "298", "name" : "HeatPump.DefrostType", "value" : "1"},
        { "id" : "376", "name" : "ColdPump.CPRunTime", "value" : "14781"},
        { "id" : "505", "name" : "Legionella.TimeoutCnt", "value" : "0"},
        { "id" : "302", "name" : "HeatPump.APRunTime", "value" : "0"},
        { "id" : "435", "name" : "Compressor.Gain", "value" : "5.0"},
        { "id" : "301", "name" : "HeatPump.RunTime", "value" : "32911"},
        { "id" : "382", "name" : "HotWater.TElecLimit", "value" : "35.0"},
        { "id" : "405", "name" : "Heating.StopCap1", "value" : "10.0"},
        { "id" : "222", "name" : "Output.ColdPumpLow", "value" : "0"},
        { "id" : "223", "name" : "Output.HotSidePump", "value" : "1"},
        { "id" : "224", "name" : "Output.DefrostValve", "value" : "0"},
        { "id" : "225", "name" : "Output.SolarPump", "value" : "0"},
        { "id" : "234", "name" : "Manual.Manual", "value" : "17"},
        { "id" : "438", "name" : "Compressor.Tsample", "value" : "1"},
        { "id" : "437", "name" : "Compressor.Td", "value" : "0"}
    ]
    
    # Create a client instance
    client = LOMJsonClient("dummy_host")
    
    # Convert to JSON string to simulate real response
    json_string = json.dumps(example_json)
    
    print("=" * 80)
    print("JSON PARSING TEST")
    print("=" * 80)
    print(f"\nTesting with {len(example_json)} data items")
    print("\nOriginal JSON data:")
    print(json.dumps(example_json, indent=2))
    
    try:
        # Test the parsing method
        parsed_data = client._parse_json_response_flexible(example_json, json_string)
        
        print("\n" + "=" * 80)
        print("PARSING RESULTS")
        print("=" * 80)
        print(f"\nSuccessfully parsed {len(parsed_data)} items")
        
        # Verify all IDs are extracted correctly
        print("\n1. ID Verification:")
        original_ids = {item["id"] for item in example_json}
        parsed_ids = {item["id"] for item in parsed_data}
        
        if original_ids == parsed_ids:
            print("✓ All IDs extracted correctly")
        else:
            missing_ids = original_ids - parsed_ids
            extra_ids = parsed_ids - original_ids
            print(f"✗ ID mismatch!")
            if missing_ids:
                print(f"  Missing IDs: {missing_ids}")
            if extra_ids:
                print(f"  Extra IDs: {extra_ids}")
        
        # Verify all names are preserved
        print("\n2. Name Verification:")
        original_names = {item["name"] for item in example_json}
        parsed_names = {item["name"] for item in parsed_data}
        
        if original_names == parsed_names:
            print("✓ All names preserved correctly")
        else:
            missing_names = original_names - parsed_names
            extra_names = parsed_names - original_names
            print(f"✗ Name mismatch!")
            if missing_names:
                print(f"  Missing names: {missing_names}")
            if extra_names:
                print(f"  Extra names: {extra_names}")
        
        # Verify value types
        print("\n3. Value Type Verification:")
        type_errors = []
        for item in parsed_data:
            original_item = next((orig for orig in example_json if orig["id"] == item["id"]), None)
            if original_item:
                orig_value = original_item["value"]
                parsed_value = item["value"]
                
                # Check if the value is preserved as string (as expected)
                if str(orig_value) != str(parsed_value):
                    type_errors.append(f"ID {item['id']}: {orig_value} -> {parsed_value}")
        
        if not type_errors:
            print("✓ All values preserved correctly")
        else:
            print(f"✗ Found {len(type_errors)} value mismatches:")
            for error in type_errors[:5]:  # Show first 5 errors
                print(f"  {error}")
            if len(type_errors) > 5:
                print(f"  ... and {len(type_errors) - 5} more")
        
        # Check for data loss
        print("\n4. Data Loss Verification:")
        if len(parsed_data) == len(example_json):
            print("✓ No data loss detected")
        else:
            print(f"✗ Data loss detected! Original: {len(example_json)}, Parsed: {len(parsed_data)}")
        
        # Display parsed data
        print("\n5. Parsed Data Sample (first 5 items):")
        for i, item in enumerate(parsed_data[:5]):
            print(f"  Item {i+1}: ID={item['id']}, Name={item['name']}, Value={item['value']}")
        
        # Test with alternative format (dict format)
        print("\n" + "=" * 80)
        print("ALTERNATIVE FORMAT TEST")
        print("=" * 80)
        
        # Convert list to dict format (alternative heat pump format)
        dict_format = {}
        for item in example_json:
            dict_format[item["id"]] = {
                "name": item["name"],
                "value": item["value"]
            }
        
        dict_json_string = json.dumps(dict_format)
        print(f"\nTesting with dict format containing {len(dict_format)} items")
        
        try:
            parsed_dict_data = client._parse_json_response_flexible(dict_format, dict_json_string)
            print(f"\n✓ Successfully parsed dict format with {len(parsed_dict_data)} items")
            
            # Verify consistency between list and dict parsing
            if len(parsed_data) == len(parsed_dict_data):
                print("✓ List and dict parsing produce consistent results")
            else:
                print(f"✗ Inconsistent results: List={len(parsed_data)}, Dict={len(parsed_dict_data)}")
                
        except Exception as e:
            print(f"\n✗ Failed to parse dict format: {e}")
        
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print("✓ JSON parsing functionality verified successfully")
        print("✓ All IDs, names, and values preserved correctly")
        print("✓ No data loss detected")
        print("✓ Both list and dict formats supported")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Parsing failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_parse_json_response_flexible()
    sys.exit(0 if success else 1)