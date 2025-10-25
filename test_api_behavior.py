#!/usr/bin/env python3
"""Diagnostic script to investigate SVK Heatpump API behavior.

This script tests multiple approaches to requesting data from the heat pump API
to determine why only 1 item is returned instead of 25.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, List, Any

import aiohttp
from yarl import URL

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_LOGGER = logging.getLogger(__name__)


class SVKConnectionError(Exception):
    """Base exception for connection errors."""
    pass


class SVKAuthenticationError(SVKConnectionError):
    """Authentication failed."""
    pass


def _parse_www_authenticate(header: str) -> Dict[str, str]:
    """Parse WWW-Authenticate header for Digest authentication."""
    import re
    auth_params = {}
    if not header.startswith('Digest '):
        return auth_params
    
    # Remove 'Digest ' prefix
    header = header[7:]
    
    # Parse key=value pairs, handling quoted values
    parts = re.findall(r'(\w+)=(".*?"|[^,]+)', header)
    for key, value in parts:
        # Remove quotes if present
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        auth_params[key.lower()] = value
    
    return auth_params


def _md5_hex(data: str) -> str:
    """Calculate MD5 hash of a string."""
    import hashlib
    return hashlib.md5(data.encode('utf-8')).hexdigest()


def _compute_digest_response(
    method: str,
    uri: str,
    username: str,
    password: str,
    realm: str,
    nonce: str,
    qop: str = "auth",
    algorithm: str = "MD5",
    opaque: str = None,
    nc: str = "00000001",
    cnonce: str = None,
) -> str:
    """Compute Digest authentication response according to RFC 7616."""
    import hashlib
    import random
    
    if cnonce is None:
        cnonce = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
    
    # Compute HA1 = MD5(username:realm:password)
    ha1 = _md5_hex(f"{username}:{realm}:{password}")
    
    # Compute HA2 = MD5(method:uri)
    ha2 = _md5_hex(f"{method}:{uri}")
    
    # Compute response
    if qop and qop.lower() in ("auth", "auth-int"):
        # With qop: response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
        response = _md5_hex(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}")
    else:
        # Without qop: response = MD5(HA1:nonce:HA2)
        response = _md5_hex(f"{ha1}:{nonce}:{ha2}")
    
    # Build Authorization header
    auth_parts = [
        f'username="{username}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
        f'response="{response}"',
        f'algorithm={algorithm}',
    ]
    
    if qop:
        auth_parts.extend([
            f'qop={qop}',
            f'nc={nc}',
            f'cnonce="{cnonce}"',
        ])
    
    if opaque:
        auth_parts.append(f'opaque="{opaque}"')
    
    return f"Digest {', '.join(auth_parts)}"


class APITestClient:
    """Test client for communicating with SVK LOM320 web module using JSON API with Digest authentication."""
    
    def __init__(self, host: str, username: str = "", password: str = "", timeout: int = 10):
        """Initialize the JSON client."""
        self.host = host
        self._base = URL.build(scheme="http", host=host)
        self._username = username
        self._password = password
        self._session: aiohttp.ClientSession = None
        self._timeout = aiohttp.ClientTimeout(total=timeout, connect=15.0, sock_read=30.0)
        self._digest_nonce = None
        self._digest_opaque = None
        self._digest_realm = None
        self._digest_qop = "auth"
        self._digest_algorithm = "MD5"
        self._digest_nc = 0
    
    async def start(self):
        """Start the client session."""
        if self._session:
            return
        
        self._session = aiohttp.ClientSession(
            timeout=self._timeout,
            connector=aiohttp.TCPConnector(limit=6, force_close=True),
            headers={
                "User-Agent": "SVKHeatpump/0.1 (HomeAssistant)",
                "Accept": "application/json",
                "Accept-Language": "en",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "close",
            },
            cookie_jar=aiohttp.CookieJar(unsafe=True),
        )
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def test_request(self, path: str, query_params: str) -> Dict[str, Any]:
        """Make a test request with Digest authentication."""
        if not self._session:
            await self.start()
        
        url = self._base.with_path(path).with_query(query_params)
        _LOGGER.info("Making request to: %s", url)
        
        try:
            # First, send an unauthenticated GET request
            headers = {}
            resp = await self._session.get(url, headers=headers, allow_redirects=False)
            
            try:
                # Handle 401 - Need authentication
                if resp.status == 401:
                    auth_header = resp.headers.get('WWW-Authenticate', '')
                    _LOGGER.debug("Received 401 - WWW-Authenticate header: %s", auth_header)
                    if not auth_header.startswith('Digest '):
                        raise SVKAuthenticationError("Server does not support Digest authentication")
                    
                    # Parse WWW-Authenticate header
                    auth_params = _parse_www_authenticate(auth_header)
                    
                    # Update stored digest parameters
                    self._digest_nonce = auth_params.get('nonce')
                    self._digest_opaque = auth_params.get('opaque')
                    self._digest_realm = auth_params.get('realm')
                    self._digest_qop = auth_params.get('qop', 'auth')
                    self._digest_algorithm = auth_params.get('algorithm', 'MD5')
                    
                    if not self._digest_nonce or not self._digest_realm:
                        raise SVKAuthenticationError("Invalid Digest authentication parameters")
                    
                    # Increment nonce count
                    self._digest_nc += 1
                    nc_hex = f"{self._digest_nc:08x}"
                    
                    # Generate cnonce
                    import hashlib
                    import random
                    cnonce = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
                    
                    # Compute Digest authorization header
                    uri = str(url.relative())
                    auth_header = _compute_digest_response(
                        method="GET",
                        uri=uri,
                        username=self._username,
                        password=self._password,
                        realm=self._digest_realm,
                        nonce=self._digest_nonce,
                        qop=self._digest_qop,
                        algorithm=self._digest_algorithm,
                        opaque=self._digest_opaque,
                        nc=nc_hex,
                        cnonce=cnonce,
                    )
                    
                    # Retry with Digest authentication
                    headers["Authorization"] = auth_header
                    resp = await self._session.get(url, headers=headers, allow_redirects=False)
                
                # Check for success
                if resp.status == 200:
                    response_text = await resp.text()
                    _LOGGER.debug("Raw response (first 200 chars): %s", response_text[:200])
                    
                    # Parse JSON from the text
                    try:
                        data = json.loads(response_text)
                        return {
                            "status": "success",
                            "status_code": resp.status,
                            "data": data,
                            "raw_response": response_text,
                            "item_count": len(data) if isinstance(data, (list, dict)) else 1
                        }
                    except json.JSONDecodeError as err:
                        return {
                            "status": "error",
                            "status_code": resp.status,
                            "error": f"Invalid JSON response: {err}",
                            "raw_response": response_text,
                            "item_count": 0
                        }
                
                # Handle other errors
                elif resp.status == 401:
                    return {
                        "status": "error",
                        "status_code": resp.status,
                        "error": "Authentication failed",
                        "raw_response": await resp.text(),
                        "item_count": 0
                    }
                elif resp.status == 404:
                    return {
                        "status": "error",
                        "status_code": resp.status,
                        "error": "API endpoint not found",
                        "raw_response": await resp.text(),
                        "item_count": 0
                    }
                else:
                    return {
                        "status": "error",
                        "status_code": resp.status,
                        "error": f"HTTP {resp.status}",
                        "raw_response": await resp.text(),
                        "item_count": 0
                    }
            
            finally:
                resp.release()
        
        except Exception as err:
            return {
                "status": "error",
                "status_code": 0,
                "error": str(err),
                "raw_response": "",
                "item_count": 0
            }


async def test_approaches(client: APITestClient, test_ids: List[int]):
    """Test different approaches to requesting data from the API."""
    results = {}
    
    print("=" * 80)
    print("TESTING DIFFERENT API APPROACHES")
    print("=" * 80)
    print()
    
    # Test a: Semicolon-separated IDs (original approach)
    print("TEST A: Semicolon-separated IDs")
    print("-" * 40)
    semicolon_ids = ";".join(map(str, test_ids))
    query_a = f"ids={semicolon_ids}"
    url_a = f"http://{client.host}/cgi-bin/json_values.cgi?{query_a}"
    print(f"URL: {url_a}")
    
    result_a = await client.test_request("/cgi-bin/json_values.cgi", query_a)
    print(f"Status: {result_a['status']} ({result_a['status_code']})")
    print(f"Items returned: {result_a['item_count']}")
    if result_a['status'] == 'error':
        print(f"Error: {result_a['error']}")
    else:
        print(f"Response type: {type(result_a['data']).__name__}")
        if isinstance(result_a['data'], dict):
            print(f"Response keys: {list(result_a['data'].keys())[:10]}")
    print()
    
    results['semicolon'] = result_a
    
    # Test b: Comma-separated IDs
    print("TEST B: Comma-separated IDs")
    print("-" * 40)
    comma_ids = ",".join(map(str, test_ids))
    query_b = f"ids={comma_ids}"
    url_b = f"http://{client.host}/cgi-bin/json_values.cgi?{query_b}"
    print(f"URL: {url_b}")
    
    result_b = await client.test_request("/cgi-bin/json_values.cgi", query_b)
    print(f"Status: {result_b['status']} ({result_b['status_code']})")
    print(f"Items returned: {result_b['item_count']}")
    if result_b['status'] == 'error':
        print(f"Error: {result_b['error']}")
    else:
        print(f"Response type: {type(result_b['data']).__name__}")
        if isinstance(result_b['data'], dict):
            print(f"Response keys: {list(result_b['data'].keys())[:10]}")
    print()
    
    results['comma'] = result_b
    
    # Test c: Just a few IDs
    print("TEST C: Few IDs (first 5)")
    print("-" * 40)
    few_ids = test_ids[:5]
    comma_few = ",".join(map(str, few_ids))
    query_c = f"ids={comma_few}"
    url_c = f"http://{client.host}/cgi-bin/json_values.cgi?{query_c}"
    print(f"URL: {url_c}")
    print(f"IDs: {few_ids}")
    
    result_c = await client.test_request("/cgi-bin/json_values.cgi", query_c)
    print(f"Status: {result_c['status']} ({result_c['status_code']})")
    print(f"Items returned: {result_c['item_count']}")
    if result_c['status'] == 'error':
        print(f"Error: {result_c['error']}")
    else:
        print(f"Response type: {type(result_c['data']).__name__}")
        if isinstance(result_c['data'], dict):
            print(f"Response keys: {list(result_c['data'].keys())}")
    print()
    
    results['few'] = result_c
    
    # Test d: Single ID
    print("TEST D: Single ID")
    print("-" * 40)
    single_id = test_ids[0]
    query_d = f"ids={single_id}"
    url_d = f"http://{client.host}/cgi-bin/json_values.cgi?{query_d}"
    print(f"URL: {url_d}")
    print(f"ID: {single_id}")
    
    result_d = await client.test_request("/cgi-bin/json_values.cgi", query_d)
    print(f"Status: {result_d['status']} ({result_d['status_code']})")
    print(f"Items returned: {result_d['item_count']}")
    if result_d['status'] == 'error':
        print(f"Error: {result_d['error']}")
    else:
        print(f"Response type: {type(result_d['data']).__name__}")
        if isinstance(result_d['data'], dict):
            print(f"Response keys: {list(result_d['data'].keys())}")
    print()
    
    results['single'] = result_d
    
    # Test e: No IDs (default response)
    print("TEST E: No IDs (default response)")
    print("-" * 40)
    url_e = f"http://{client.host}/cgi-bin/json_values.cgi"
    print(f"URL: {url_e}")
    
    result_e = await client.test_request("/cgi-bin/json_values.cgi", "")
    print(f"Status: {result_e['status']} ({result_e['status_code']})")
    print(f"Items returned: {result_e['item_count']}")
    if result_e['status'] == 'error':
        print(f"Error: {result_e['error']}")
    else:
        print(f"Response type: {type(result_e['data']).__name__}")
        if isinstance(result_e['data'], dict):
            print(f"Response keys (first 20): {list(result_e['data'].keys())[:20]}")
    print()
    
    results['none'] = result_e
    
    # Test f: Test ID limit (if we suspect there's a limit)
    print("TEST F: Testing ID limits")
    print("-" * 40)
    limit_tests = [1, 2, 3, 5, 10, 15, 20, 25]
    for limit in limit_tests:
        limited_ids = test_ids[:limit]
        comma_limited = ",".join(map(str, limited_ids))
        query_f = f"ids={comma_limited}"
        
        result_f = await client.test_request("/cgi-bin/json_values.cgi", query_f)
        print(f"IDs ({limit}): {result_f['item_count']} items returned")
        
        if result_f['status'] == 'error':
            print(f"  Error: {result_f['error']}")
            break
    
    print()
    
    # Test g: Test individual IDs to see which ones exist
    print("TEST G: Testing individual IDs to check existence")
    print("-" * 40)
    existing_ids = []
    for test_id in test_ids[:10]:  # Test first 10 IDs to avoid too much output
        query_g = f"ids={test_id}"
        result_g = await client.test_request("/cgi-bin/json_values.cgi", query_g)
        
        if result_g['status'] == 'success' and result_g['item_count'] > 0:
            existing_ids.append(test_id)
            print(f"ID {test_id}: EXISTS")
        else:
            print(f"ID {test_id}: NOT FOUND or ERROR")
    
    print(f"Found {len(existing_ids)} existing IDs out of {min(10, len(test_ids))} tested")
    print()
    
    return results


async def analyze_results(results: Dict[str, Dict[str, Any]]):
    """Analyze the test results and provide insights."""
    print("=" * 80)
    print("ANALYSIS OF RESULTS")
    print("=" * 80)
    print()
    
    # Compare approaches
    print("COMPARISON OF APPROACHES:")
    print("-" * 40)
    print(f"Semicolon-separated: {results['semicolon']['item_count']} items")
    print(f"Comma-separated: {results['comma']['item_count']} items")
    print(f"Few IDs (5): {results['few']['item_count']} items")
    print(f"Single ID: {results['single']['item_count']} items")
    print(f"No IDs: {results['none']['item_count']} items")
    print()
    
    # Determine the best approach
    max_items = 0
    best_approach = ""
    for approach, result in results.items():
        if result['status'] == 'success' and result['item_count'] > max_items:
            max_items = result['item_count']
            best_approach = approach
    
    print(f"BEST APPROACH: {best_approach} (returned {max_items} items)")
    print()
    
    # Check for format differences
    print("FORMAT ANALYSIS:")
    print("-" * 40)
    for approach, result in results.items():
        if result['status'] == 'success':
            data = result['data']
            print(f"{approach}: {type(data).__name__}")
            if isinstance(data, dict):
                print(f"  Keys: {len(data)} total")
                # Check if keys are numeric strings
                numeric_keys = [k for k in data.keys() if k.isdigit()]
                print(f"  Numeric keys: {len(numeric_keys)}")
                if numeric_keys:
                    print(f"  Sample keys: {numeric_keys[:5]}")
            elif isinstance(data, list):
                print(f"  List items: {len(data)}")
                if data and isinstance(data[0], dict):
                    print(f"  Sample item keys: {list(data[0].keys())}")
    print()
    
    # Recommendations
    print("RECOMMENDATIONS:")
    print("-" * 40)
    if results['comma']['item_count'] > results['semicolon']['item_count']:
        print("✓ Use comma-separated IDs instead of semicolon-separated")
    else:
        print("✓ Semicolon-separated IDs work better than comma-separated")
    
    if results['single']['item_count'] > 0:
        print("✓ Single ID requests work - API is functional")
    
    if results['none']['item_count'] > 0:
        print("✓ API returns data without IDs - this can be used to discover available IDs")
    
    if max_items < 25:
        print(f"⚠ Maximum items returned ({max_items}) is less than expected (25)")
        print("  This might be due to:")
        print("  - ID limit per request")
        print("  - Some IDs don't exist on this heat pump")
        print("  - API pagination not implemented")
        print("  - Different API endpoint required for multiple IDs")
    
    print()


async def main():
    """Main function to run the API behavior test."""
    print("=" * 80)
    print("SVK Heatpump API Behavior Diagnostic")
    print("=" * 80)
    print()
    
    # Configuration
    host = "192.168.50.9"
    username = "admin"
    password = "admin"
    
    # IDs to test (from the example)
    test_ids = [299, 255, 256, 257, 258, 259, 262, 263, 422, 388, 298, 376, 505, 302, 435, 301, 382, 405, 222, 223, 224, 225, 234, 438, 437]
    
    print(f"Testing connection to heat pump at http://{host}")
    print(f"Using credentials: {username}:{password}")
    print(f"Testing with {len(test_ids)} IDs: {test_ids}")
    print()
    
    # Create client
    client = APITestClient(host, username, password)
    
    try:
        # Start the client
        await client.start()
        
        # Test different approaches
        results = await test_approaches(client, test_ids)
        
        # Analyze results
        await analyze_results(results)
        
        print("Diagnostic completed!")
        
    except Exception as err:
        print(f"Unexpected error: {err}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Close the client
        await client.close()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as err:
        print(f"Fatal error: {err}")
        import traceback
        traceback.print_exc()
        sys.exit(1)