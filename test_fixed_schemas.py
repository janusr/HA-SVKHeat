#!/usr/bin/env python3
"""Test script to validate the fixed schemas work with voluptuous_serialize."""

import voluptuous as vol
from voluptuous_serialize import convert

def test_fixed_schemas():
    """Test the fixed schemas that should work with voluptuous_serialize."""
    
    # Fixed user schema (without vol.Match)
    fixed_user_schema = vol.Schema({
        vol.Required("host"): vol.Coerce(str),
        vol.Required("username"): vol.Coerce(str),
        vol.Required("password"): vol.Coerce(str),
    })
    
    # Fixed options schema (with vol.Coerce instead of bool)
    fixed_options_schema = vol.Schema({
        vol.Optional("write_access", default=False): vol.Coerce(bool),
        vol.Optional("fetch_interval", default=30): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
    })
    
    schemas_to_test = [
        ("Fixed user schema", fixed_user_schema),
        ("Fixed options schema", fixed_options_schema),
    ]
    
    for name, schema in schemas_to_test:
        try:
            result = convert(schema)
            print(f"✓ {name}: SUCCESS")
            print(f"  Serialized result: {result}")
        except Exception as e:
            print(f"✗ {name}: FAILED - {e}")

if __name__ == "__main__":
    print("=== Testing Fixed Schemas ===")
    test_fixed_schemas()