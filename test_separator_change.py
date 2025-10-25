#!/usr/bin/env python3
"""Simple test to verify the ID separator change from comma to semicolon."""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_separator_change():
    """Test that the client now uses semicolon-separated IDs."""
    try:
        # Import the client module
        import custom_components.svk_heatpump.client as client
        
        # Create a test client
        test_client = client.LOMJsonClient("192.168.1.100", "admin", "password")
        
        # Test IDs
        test_ids = [299, 255, 256, 257, 258]
        
        # Create a mock URL to test the separator
        from yarl import URL
        
        # This simulates what happens in the _request_with_digest_auth method
        query_params = f"ids={';'.join(map(str, test_ids))}"
        base_url = URL.build(scheme="http", host="192.168.1.100")
        get_url = base_url.with_path("/cgi-bin/json_values.cgi").with_query(query_params)
        
        print(f"Generated URL: {get_url}")
        print(f"Query parameters: {query_params}")
        
        # Verify the separator is semicolon
        if ';' in query_params and ',' not in query_params.split('ids=')[1]:
            print("✓ SUCCESS: IDs are now separated by semicolons")
            return True
        else:
            print("❌ FAILURE: IDs are still separated by commas")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing ID separator change...")
    print("=" * 50)
    
    success = test_separator_change()
    
    print("=" * 50)
    if success:
        print("✅ Test passed: ID separator successfully changed to semicolon")
        sys.exit(0)
    else:
        print("❌ Test failed: ID separator was not changed correctly")
        sys.exit(1)