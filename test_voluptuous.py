#!/usr/bin/env python3
"""Test script to reproduce voluptuous serialization issue."""

import voluptuous as vol
from voluptuous_serialize import convert

# Test current schema from config_flow.py
def test_current_schema():
    """Test the current schema that's causing issues."""
    
    # This is the schema from async_step_user
    user_schema = vol.Schema({
        vol.Required("host"): vol.All(str, vol.Match(r'^[a-zA-Z0-9\.\-\:]+$')),
        vol.Required("username"): str,
        vol.Required("password"): str,
    })
    
    # This is the schema from async_step_options
    options_schema = vol.Schema({
        vol.Optional("write_access", default=False): bool,
        vol.Optional("fetch_interval", default=30): vol.All(int, vol.Range(min=10, max=300)),
    })
    
    try:
        print("Testing user schema serialization...")
        result = convert(user_schema)
        print("User schema serialization successful:", result)
    except Exception as e:
        print(f"User schema serialization failed: {e}")
    
    try:
        print("Testing options schema serialization...")
        result = convert(options_schema)
        print("Options schema serialization successful:", result)
    except Exception as e:
        print(f"Options schema serialization failed: {e}")

def test_fixed_schema():
    """Test a fixed version of the schema."""
    
    # Fixed schema using proper voluptuous validators
    fixed_user_schema = vol.Schema({
        vol.Required("host"): vol.All(vol.Coerce(str), vol.Match(r'^[a-zA-Z0-9\.\-\:]+$')),
        vol.Required("username"): vol.Coerce(str),
        vol.Required("password"): vol.Coerce(str),
    })
    
    fixed_options_schema = vol.Schema({
        vol.Optional("write_access", default=False): vol.Boolean(),
        vol.Optional("fetch_interval", default=30): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
    })
    
    try:
        print("Testing fixed user schema serialization...")
        result = convert(fixed_user_schema)
        print("Fixed user schema serialization successful:", result)
    except Exception as e:
        print(f"Fixed user schema serialization failed: {e}")
    
    try:
        print("Testing fixed options schema serialization...")
        result = convert(fixed_options_schema)
        print("Fixed options schema serialization successful:", result)
    except Exception as e:
        print(f"Fixed options schema serialization failed: {e}")

if __name__ == "__main__":
    print("=== Testing Current Schema ===")
    test_current_schema()
    
    print("\n=== Testing Fixed Schema ===")
    test_fixed_schema()