#!/usr/bin/env python3
"""Test script to verify the enhanced JSON parsing logic."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.svk_heatpump.client import LOMJsonClient, SVKInvalidDataFormatError
import logging

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_flexible_parsing():
    """Test the flexible JSON parsing with different formats."""
    client = LOMJsonClient("test.host")
    
    # Test case 1: Standard list format
    print("=== Test 1: Standard list format ===")
    list_data = [
        {"id": "297", "name": "heatpump_state", "value": "ready"},
        {"id": "253", "name": "heating_supply_temp", "value": "45.5"},
        {"id": "254", "name": "heating_return_temp", "value": "40.2"}
    ]
    try:
        result = client._parse_json_response_flexible(list_data)
        print(f"✓ Successfully parsed list format: {len(result)} items")
        print(f"  Sample: {result[0]}")
    except Exception as e:
        print(f"✗ Failed to parse list format: {e}")
    
    # Test case 2: Dict format (alternative)
    print("\n=== Test 2: Dict format ===")
    dict_data = {
        "297": "ready",
        "253": "45.5",
        "254": "40.2"
    }
    try:
        result = client._parse_json_response_flexible(dict_data)
        print(f"✓ Successfully parsed dict format: {len(result)} items")
        print(f"  Sample: {result[0]}")
    except Exception as e:
        print(f"✗ Failed to parse dict format: {e}")
    
    # Test case 3: Nested format
    print("\n=== Test 3: Nested format ===")
    nested_data = {
        "data": [
            {"id": "297", "name": "heatpump_state", "value": "ready"},
            {"id": "253", "name": "heating_supply_temp", "value": "45.5"}
        ]
    }
    try:
        result = client._parse_json_response_flexible(nested_data)
        print(f"✓ Successfully parsed nested format: {len(result)} items")
        print(f"  Sample: {result[0]}")
    except Exception as e:
        print(f"✗ Failed to parse nested format: {e}")
    
    # Test case 4: Single item format
    print("\n=== Test 4: Single item format ===")
    single_item = {"id": "297", "name": "heatpump_state", "value": "ready"}
    try:
        result = client._parse_json_response_flexible(single_item)
        print(f"✓ Successfully parsed single item format: {len(result)} items")
        print(f"  Sample: {result[0]}")
    except Exception as e:
        print(f"✗ Failed to parse single item format: {e}")
    
    # Test case 5: Invalid format
    print("\n=== Test 5: Invalid format ===")
    invalid_data = {"error": "Invalid request", "code": 400}
    try:
        result = client._parse_json_response_flexible(invalid_data)
        print(f"✗ Should have failed but got: {len(result)} items")
    except SVKInvalidDataFormatError as e:
        print(f"✓ Correctly detected invalid format: {e.message}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    # Test case 6: HTML error detection
    print("\n=== Test 6: HTML error detection ===")
    html_error = """<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>401 Authorization Required</title>
</head><body>
<h1>Authorization Required</h1>
<p>This server could not verify that you are authorized to access the document requested.</p>
</body></html>"""
    try:
        error_title = client._detect_html_error_page(html_error)
        print(f"✓ Successfully detected HTML error: {error_title}")
    except Exception as e:
        print(f"✗ Failed to detect HTML error: {e}")
    
    print("\n=== All tests completed ===")

if __name__ == "__main__":
    test_flexible_parsing()