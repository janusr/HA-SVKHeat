#!/usr/bin/env python3
"""Test script to verify the enhanced JSON parsing with Digest authentication."""

import asyncio
import logging
import sys
import os

# Add the custom_components to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

from custom_components.svk_heatpump.client import LOMJsonClient

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_digest_client(host, username, password):
    """Test the LOMJsonClient with Digest authentication."""
    print(f"Testing connection to {host} with Digest authentication...")
    
    client = LOMJsonClient(host, username, password, timeout=10)
    
    try:
        await client.start()
        
        # Test with a few sample IDs
        test_ids = [297, 253, 254, 255, 256]
        print(f"Requesting IDs: {test_ids}")
        
        # Read values from the device
        result = await client.read_values(test_ids)
        
        print(f"✓ Successfully received {len(result)} items")
        print("Sample items:")
        for i, item in enumerate(result[:5]):  # Show first 5 items
            print(f"  {i+1}. ID: {item.get('id')}, Name: {item.get('name')}, Value: {item.get('value')}")
        
        if len(result) > 5:
            print(f"  ... and {len(result) - 5} more items")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        return False
        
    finally:
        await client.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python test_digest_client.py <host> <username> <password>")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    success = asyncio.run(test_digest_client(host, username, password))
    
    if success:
        print("\n✓ Test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Test failed!")
        sys.exit(1)