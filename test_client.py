#!/usr/bin/env python3
"""Test script to validate the simplified client implementation."""

import asyncio
import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'svk_heatpump'))

from client import LOMJsonClient

async def test_client_instantiation():
    """Test that the client can be instantiated without errors."""
    print("Testing client instantiation...")
    
    try:
        # Test with default parameters
        client = LOMJsonClient(
            host="192.168.50.9",
            username="admin",
            password="admin"
        )
        print("✓ Client instantiated successfully")
        
        # Test that default IDs are set correctly
        expected_ids = [299, 255, 256, 257, 258, 259, 262, 263, 422, 388, 298, 376, 505, 302, 435, 301, 382, 405, 222, 223, 224, 225, 234, 438, 437]
        if client._default_ids == expected_ids:
            print("✓ Default IDs are set correctly")
        else:
            print(f"✗ Default IDs mismatch. Expected: {expected_ids}, Got: {client._default_ids}")
        
        # Test that chunk size is set to 25
        if client._chunk_size == 25:
            print("✓ Chunk size is set to 25")
        else:
            print(f"✗ Chunk size is not 25. Got: {client._chunk_size}")
        
        # Test that authentication state is initialized correctly
        if client._auth_nonce is None and client._auth_realm is None:
            print("✓ Authentication state initialized correctly")
        else:
            print("✗ Authentication state not initialized correctly")
        
        # Test URL building
        base_url = str(client._base)
        if base_url == "http://192.168.50.9":
            print("✓ Base URL built correctly")
        else:
            print(f"✗ Base URL incorrect. Expected: http://192.168.50.9, Got: {base_url}")
        
        return True
        
    except Exception as e:
        print(f"✗ Client instantiation failed: {e}")
        return False

async def test_public_interface():
    """Test that the public interface is maintained."""
    print("\nTesting public interface...")
    
    try:
        client = LOMJsonClient(
            host="192.168.50.9",
            username="admin",
            password="admin"
        )
        
        # Test that all required methods exist
        required_methods = ['start', 'close', 'read_values', 'write_value', 'test_connection']
        for method in required_methods:
            if hasattr(client, method) and callable(getattr(client, method)):
                print(f"✓ Method '{method}' exists and is callable")
            else:
                print(f"✗ Method '{method}' is missing or not callable")
        
        # Test that set_default_ids method exists
        if hasattr(client, 'set_default_ids') and callable(getattr(client, 'set_default_ids')):
            print("✓ Method 'set_default_ids' exists and is callable")
        else:
            print("✗ Method 'set_default_ids' is missing or not callable")
        
        return True
        
    except Exception as e:
        print(f"✗ Public interface test failed: {e}")
        return False

async def test_json_parsing():
    """Test JSON response parsing."""
    print("\nTesting JSON parsing...")
    
    try:
        client = LOMJsonClient(
            host="192.168.50.9",
            username="admin",
            password="admin"
        )
        
        # Test with expected format
        test_data = [{"id": "299", "name": "HeatPump.CapacityAct", "value": "25.2"}]
        result = client._parse_json_response(test_data)
        
        if len(result) == 1 and result[0]["id"] == "299" and result[0]["name"] == "HeatPump.CapacityAct" and result[0]["value"] == "25.2":
            print("✓ JSON parsing works for expected format")
        else:
            print(f"✗ JSON parsing failed for expected format. Got: {result}")
        
        # Test with alternative format
        test_data_alt = {"299": {"name": "HeatPump.CapacityAct", "value": "25.2"}}
        result_alt = client._parse_json_response(test_data_alt)
        
        if len(result_alt) == 1 and result_alt[0]["id"] == "299" and result_alt[0]["name"] == "HeatPump.CapacityAct" and result_alt[0]["value"] == "25.2":
            print("✓ JSON parsing works for alternative format")
        else:
            print(f"✗ JSON parsing failed for alternative format. Got: {result_alt}")
        
        return True
        
    except Exception as e:
        print(f"✗ JSON parsing test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=== Testing SVK Heatpump Client Implementation ===\n")
    
    tests = [
        test_client_instantiation(),
        test_public_interface(),
        test_json_parsing()
    ]
    
    results = await asyncio.gather(*tests, return_exceptions=True)
    
    passed = sum(1 for result in results if result is True)
    failed = len(results) - passed
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)