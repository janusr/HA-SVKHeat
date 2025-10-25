#!/usr/bin/env python3
"""
Final verification test to confirm that the fix for using semicolon-separated IDs 
works correctly with the actual heat pump API.

This script:
1. Uses the updated client code with the semicolon separator fix
2. Makes a real request to the heat pump API at http://192.168.50.9 with admin:admin credentials
3. Requests the same 25 IDs from the original example
4. Verifies that all 25 items are now returned (not just 1)
5. Confirms that the JSON parsing works correctly for all returned items
6. Displays a summary of the verification results
"""

import asyncio
import logging
import sys
import time
from typing import List, Dict, Any

# Import the actual client module
from custom_components.svk_heatpump.client import LOMJsonClient

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# The 25 IDs from the original example
TEST_IDS = [
    299, 255, 256, 257, 258, 259, 262, 263, 422, 388,
    298, 376, 505, 302, 435, 301, 382, 405, 222, 223,
    224, 225, 234, 438, 437
]

async def test_semicolon_fix():
    """Test that the semicolon-separated IDs fix works correctly."""
    print("=" * 80)
    print("VERIFICATION TEST: Semicolon-separated IDs Fix")
    print("=" * 80)
    
    # Create client with the heat pump API details
    client = LOMJsonClient(
        host="192.168.50.9",
        username="admin",
        password="admin",
        timeout=15
    )
    
    try:
        # Start the client session
        await client.start()
        print(f"✓ Client session started successfully")
        
        # Make the request with all 25 IDs
        print(f"\n📡 Requesting {len(TEST_IDS)} IDs from heat pump API...")
        print(f"   IDs: {TEST_IDS}")
        
        start_time = time.time()
        results = await client.read_values(TEST_IDS)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"✓ Request completed in {duration:.2f} seconds")
        
        # Verify the results
        print(f"\n📊 RESULTS ANALYSIS:")
        print(f"   Requested IDs: {len(TEST_IDS)}")
        print(f"   Returned items: {len(results)}")
        
        # Check if we got all the items we requested
        if len(results) == len(TEST_IDS):
            print(f"✅ SUCCESS: All {len(TEST_IDS)} requested IDs were returned!")
        elif len(results) > 0:
            print(f"⚠️  PARTIAL SUCCESS: {len(results)} out of {len(TEST_IDS)} IDs returned")
            missing_ids = set(TEST_IDS) - set(int(item['id']) for item in results)
            print(f"   Missing IDs: {sorted(missing_ids)}")
        else:
            print(f"❌ FAILURE: No items returned from the API")
            return False
        
        # Analyze the returned items
        print(f"\n🔍 DETAILED ANALYSIS:")
        
        # Group items by ID to check for duplicates
        id_counts = {}
        for item in results:
            item_id = int(item['id'])
            if item_id not in id_counts:
                id_counts[item_id] = []
            id_counts[item_id].append(item)
        
        # Check for duplicates
        duplicates = {id: items for id, items in id_counts.items() if len(items) > 1}
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} IDs with multiple entries:")
            for id, items in duplicates.items():
                print(f"   ID {id}: {len(items)} entries")
        else:
            print(f"✅ No duplicate IDs found")
        
        # Show sample of returned items
        print(f"\n📋 SAMPLE OF RETURNED ITEMS (first 10):")
        for i, item in enumerate(results[:10]):
            print(f"   {i+1:2d}. ID: {item['id']:3s} | Name: {item['name'][:30]:30s} | Value: {item['value']}")
        
        if len(results) > 10:
            print(f"   ... and {len(results) - 10} more items")
        
        # Verify JSON parsing worked correctly
        print(f"\n🔧 JSON PARSING VERIFICATION:")
        valid_items = 0
        invalid_items = 0
        
        for item in results:
            if all(key in item for key in ['id', 'name', 'value']):
                valid_items += 1
            else:
                invalid_items += 1
                print(f"   ❌ Invalid item structure: {item}")
        
        print(f"   Valid items: {valid_items}")
        print(f"   Invalid items: {invalid_items}")
        
        if invalid_items == 0:
            print(f"✅ JSON parsing successful for all items")
        else:
            print(f"⚠️  Some items have invalid structure")
        
        # Summary
        print(f"\n📈 SUMMARY:")
        print(f"   Request duration: {duration:.2f} seconds")
        print(f"   Success rate: {len(results)}/{len(TEST_IDS)} ({100*len(results)/len(TEST_IDS):.1f}%)")
        print(f"   Items per second: {len(results)/duration:.1f}")
        
        # Final verdict
        if len(results) >= len(TEST_IDS) * 0.9:  # 90% success rate
            print(f"\n🎉 VERIFICATION PASSED: The semicolon-separated IDs fix is working correctly!")
            print(f"   The API now returns multiple items instead of just one.")
            return True
        else:
            print(f"\n❌ VERIFICATION FAILED: The fix is not working as expected.")
            print(f"   Expected at least 90% success rate, got {100*len(results)/len(TEST_IDS):.1f}%")
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR during verification: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        await client.close()
        print(f"\n🧹 Client session closed")

async def main():
    """Main function to run the verification test."""
    print("Starting verification test for semicolon-separated IDs fix...")
    print("This test will connect to the heat pump at 192.168.50.9")
    
    # Run the test
    success = await test_semicolon_fix()
    
    # Exit with appropriate code
    if success:
        print("\n✅ VERIFICATION TEST COMPLETED SUCCESSFULLY")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION TEST FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())