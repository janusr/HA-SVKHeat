#!/usr/bin/env python3
"""Detailed test script to identify the specific voluptuous serialization issue."""

import voluptuous as vol
from voluptuous_serialize import convert

def test_individual_validators():
    """Test individual validators to isolate the issue."""
    
    # Test basic validators
    validators_to_test = [
        ("str", str),
        ("int", int),
        ("bool", bool),
        ("vol.Boolean()", vol.Boolean()),
        ("vol.Coerce(str)", vol.Coerce(str)),
        ("vol.Coerce(int)", vol.Coerce(int)),
        ("vol.Coerce(bool)", vol.Coerce(bool)),
        ("vol.Match(r'^test$')", vol.Match(r'^test$')),
        ("vol.Range(min=1, max=10)", vol.Range(min=1, max=10)),
        ("vol.All(str)", vol.All(str)),
        ("vol.All(vol.Coerce(str))", vol.All(vol.Coerce(str))),
        ("vol.All(str, vol.Match(r'^test$'))", vol.All(str, vol.Match(r'^test$'))),
        ("vol.All(vol.Coerce(str), vol.Match(r'^test$'))", vol.All(vol.Coerce(str), vol.Match(r'^test$'))),
    ]
    
    for name, validator in validators_to_test:
        try:
            schema = vol.Schema({"test": validator})
            result = convert(schema)
            print(f"✓ {name}: SUCCESS")
        except Exception as e:
            print(f"✗ {name}: FAILED - {e}")

def test_schema_variations():
    """Test different schema variations that match our use case."""
    
    schemas = [
        # Original problematic schema
        ("Original user schema", vol.Schema({
            vol.Required("host"): vol.All(str, vol.Match(r'^[a-zA-Z0-9\.\-\:]+$')),
            vol.Required("username"): str,
            vol.Required("password"): str,
        })),
        
        # Without regex
        ("Without regex", vol.Schema({
            vol.Required("host"): str,
            vol.Required("username"): str,
            vol.Required("password"): str,
        })),
        
        # With vol.Coerce instead of str
        ("With vol.Coerce", vol.Schema({
            vol.Required("host"): vol.All(vol.Coerce(str), vol.Match(r'^[a-zA-Z0-9\.\-\:]+$')),
            vol.Required("username"): vol.Coerce(str),
            vol.Required("password"): vol.Coerce(str),
        })),
        
        
        # Original options schema
        ("Original options schema", vol.Schema({
            vol.Optional("write_access", default=False): bool,
            vol.Optional("fetch_interval", default=30): vol.All(int, vol.Range(min=10, max=300)),
        })),
        
        # Options with vol.Boolean and vol.Coerce
        ("Options with vol.Boolean and vol.Coerce", vol.Schema({
            vol.Optional("write_access", default=False): vol.Boolean(),
            vol.Optional("fetch_interval", default=30): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
        })),
    ]
    
    for name, schema in schemas:
        try:
            result = convert(schema)
            print(f"✓ {name}: SUCCESS")
        except Exception as e:
            print(f"✗ {name}: FAILED - {e}")

if __name__ == "__main__":
    print("=== Testing Individual Validators ===")
    test_individual_validators()
    
    print("\n=== Testing Schema Variations ===")
    test_schema_variations()