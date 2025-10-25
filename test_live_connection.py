#!/usr/bin/env python3
"""Live connection test for SVK Heatpump API.

This script performs a live connection test to the heat pump API at http://192.168.50.9
using admin:admin credentials and HTTP Digest authentication.
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


class SVKTimeoutError(SVKConnectionError):
    """Connection timeout."""
    pass


class SVKParseError(Exception):
    """HTML parsing failed."""
    pass


class SVKInvalidDataFormatError(SVKParseError):
    """Invalid data format error."""
    def __init__(self, expected: str, received: str, details: str = ""):
        message = f"Expected {expected}, received {received}"
        if details:
            message += f": {details}"
        super().__init__(message)


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


def _parse_json_response_flexible(data: Any, response_text: str = "") -> List[Dict[str, Any]]:
    """
    Parse JSON response with flexible format handling.
    
    Enhanced to better handle the actual heat pump response format which appears
    to be a dictionary with numeric keys containing nested objects with name/value fields.
    """
    # Add diagnostic logging at the beginning of the method
    _LOGGER.info("RAW JSON RESPONSE: %s", response_text[:1000])  # First 1000 chars
    _LOGGER.info("PARSED ITEMS COUNT: %d", len(data) if data else 0)
    
    _LOGGER.debug("Parsing JSON response with flexible format handling")
    _LOGGER.debug("Response data type: %s", type(data))
    if isinstance(data, (list, dict)):
        _LOGGER.debug("Response data size: %d items", len(data))
    
    # Enhanced structure logging
    _LOGGER.info("JSON RESPONSE STRUCTURE: type=%s, keys=%s, sample=%s",
                 type(data), list(data.keys())[:10] if isinstance(data, dict) else "N/A",
                 str(data)[:500])
    
    # Log a sample of the raw data for debugging (only first few items to avoid log spam)
    if isinstance(data, list) and len(data) > 0:
        _LOGGER.debug("Sample response data (first 2 items): %s", data[:2])
    elif isinstance(data, dict) and len(data) > 0:
        sample_keys = list(data.keys())[:3]
        sample_items = {k: data[k] for k in sample_keys}
        _LOGGER.debug("Sample response data (first 3 keys): %s", sample_items)
    
    # Handle list format (expected format)
    if isinstance(data, list):
        _LOGGER.debug("Processing list format with %d items", len(data))
        valid_items = 0
        for item in data:
            if isinstance(item, dict) and 'id' in item:
                valid_items += 1
        
        if valid_items > 0:
            _LOGGER.debug("Found %d valid items in list format", valid_items)
            return data
        else:
            raise SVKInvalidDataFormatError(
                "list with dictionaries containing 'id' field",
                "list without valid items",
                f"List has {len(data)} items but none contain 'id' field"
            )
    
    # Handle dict format (alternative format) - Enhanced for heat pump format
    elif isinstance(data, dict):
        _LOGGER.debug("Processing dict format with %d keys", len(data))
        
        # Check if it's an error response first
        if any(key.lower() in ['error', 'message', 'code', 'status'] for key in data.keys()):
            raise SVKInvalidDataFormatError(
                "list or dict with recognizable structure",
                f"dict with error-like keys: {list(data.keys())}",
                "Response appears to be an error message rather than data"
            )
        
        # ENHANCED: Handle the actual heat pump format: {"253": {"name": "...", "value": "..."}, ...}
        # This appears to be the actual format returned by the heat pump
        dict_items = []
        for key, value in data.items():
            try:
                # Try to convert key to integer ID
                entity_id = int(key)
                
                # Check if value is a dict with name and value fields
                if isinstance(value, dict) and 'name' in value and 'value' in value:
                    # This is the expected heat pump format
                    dict_items.append({
                        "id": str(entity_id),
                        "name": str(value['name']),
                        "value": str(value['value'])
                    })
                    _LOGGER.debug("Successfully parsed heat pump format item: ID=%s, Name=%s, Value=%s",
                               entity_id, value['name'], value['value'])
                # Check if value is a simple dict with just a value field
                elif isinstance(value, dict) and 'value' in value:
                    dict_items.append({
                        "id": str(entity_id),
                        "name": f"entity_{entity_id}",
                        "value": str(value['value'])
                    })
                    _LOGGER.debug("Parsed simplified heat pump format item: ID=%s, Value=%s",
                               entity_id, value['value'])
                # Check if value is a simple value
                elif not isinstance(value, dict):
                    dict_items.append({
                        "id": str(entity_id),
                        "name": f"entity_{entity_id}",
                        "value": str(value)
                    })
                    _LOGGER.debug("Parsed simple key-value item: ID=%s, Value=%s", entity_id, value)
                else:
                    # Complex nested structure that we don't recognize
                    _LOGGER.warning("Unrecognized nested structure for ID %s: %s", entity_id, str(value)[:100])
                    # Try to extract any useful information
                    if isinstance(value, dict):
                        # Use first string value we find
                        for sub_key, sub_value in value.items():
                            if isinstance(sub_value, (str, int, float, bool)):
                                dict_items.append({
                                    "id": str(entity_id),
                                    "name": f"entity_{entity_id}_{sub_key}",
                                    "value": str(sub_value)
                                })
                                _LOGGER.debug("Extracted nested value for ID %s: %s=%s", entity_id, sub_key, sub_value)
                                break
                
            except (ValueError, TypeError):
                # Key is not a numeric ID, skip it
                _LOGGER.debug("Skipping non-numeric key: %s", key)
                continue
        
        if dict_items:
            _LOGGER.info("Successfully converted heat pump dict format to list with %d items", len(dict_items))
            return dict_items
        
        # Check if it's a simple key-value format (fallback)
        if all(isinstance(k, (str, int, float)) for k in data.keys()):
            _LOGGER.debug("Converting simple dict format to list")
            items = []
            for id_val, value in data.items():
                items.append({
                    "id": str(id_val),
                    "name": f"item_{id_val}",
                    "value": str(value)
                })
            _LOGGER.debug("Converted dict to list with %d items", len(items))
            return items
        
        # Check if it's a nested format with items under a key
        for possible_key in ['data', 'items', 'values', 'result']:
            if possible_key in data and isinstance(data[possible_key], list):
                _LOGGER.debug("Found nested list under key '%s'", possible_key)
                nested_data = data[possible_key]
                if nested_data:  # Non-empty list
                    return _parse_json_response_flexible(nested_data, response_text)
        
        # Check if it's a single item format
        if 'id' in data and 'value' in data:
            _LOGGER.debug("Found single item format, converting to list")
            return [data]
        
        # Try to extract any numeric keys as IDs (fallback)
        numeric_items = []
        for key, value in data.items():
            try:
                int_key = int(key)
                numeric_items.append({
                    "id": str(int_key),
                    "name": f"item_{int_key}",
                    "value": str(value)
                })
            except (ValueError, TypeError):
                continue
        
        if numeric_items:
            _LOGGER.debug("Extracted %d numeric-key items from dict", len(numeric_items))
            return numeric_items
        
        raise SVKInvalidDataFormatError(
            "list or dict with recognizable structure",
            f"dict with keys: {list(data.keys())[:5]}",
            "Dict format not recognized. Expected list, simple dict, or nested dict with 'data'/'items' key"
        )
    
    # Handle single value (unlikely but possible)
    elif isinstance(data, (str, int, float, bool)):
        _LOGGER.debug("Processing single value format: %s", data)
        return [{
            "id": "0",
            "name": "single_value",
            "value": str(data)
        }]
    
    else:
        raise SVKInvalidDataFormatError(
            "list, dict, or single value",
            f"{type(data).__name__}",
            f"Unsupported data type: {type(data).__name__}"
        )


class TestLOMJsonClient:
    """Test client for communicating with SVK LOM320 web module using JSON API with Digest authentication."""
    
    def __init__(self, host: str, username: str = "", password: str = "", timeout: int = 10):
        """Initialize the JSON client."""
        self.host = host
        self._base = URL.build(scheme="http", host=host)
        self._username = username
        self._password = password
        self._session: aiohttp.ClientSession = None
        self._timeout = aiohttp.ClientTimeout(total=timeout, connect=15.0, sock_read=30.0)
        self._digest_nonce = None  # Store nonce for subsequent requests
        self._digest_opaque = None  # Store opaque for subsequent requests
        self._digest_realm = None  # Store realm for subsequent requests
        self._digest_qop = "auth"  # Quality of protection
        self._digest_algorithm = "MD5"  # Hash algorithm
        self._digest_nc = 0  # Nonce count
        self._last_status_code = None  # Track last HTTP status code for diagnostics
    
    async def start(self):
        """Start the client session."""
        if self._session:
            return
        
        # Create session with shared configuration
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
    
    async def _request_with_digest_auth(self, path: str, ids: List[int]) -> List[Dict[str, Any]]:
        """Make a request with Digest authentication."""
        if not self._session:
            await self.start()
        
        url = self._base.with_path(path)
        
        # For GET requests with query parameters
        query_params = f"ids={','.join(map(str, ids))}"
        get_url = self._base.with_path("/cgi-bin/json_values.cgi").with_query(query_params)
        _LOGGER.info("Making digest auth request to: %s", get_url)
        _LOGGER.debug("Requesting %d IDs: %s", len(ids), ids[:10])  # Log first 10 IDs
        
        try:
            # Add overall timeout protection to prevent infinite retry loops
            result = await asyncio.wait_for(
                self._request_with_digest_auth_internal(path, ids, get_url),
                timeout=30.0  # 30 second timeout for network operations
            )
            return result
        except asyncio.TimeoutError:
            _LOGGER.error("CRITICAL: Digest auth request to %s timed out after 30 seconds - this is blocking", get_url)
            raise SVKTimeoutError(f"Request timeout after 30 seconds for {path}")
    
    async def _request_with_digest_auth_internal(self, path: str, ids: List[int], get_url: URL) -> List[Dict[str, Any]]:
        """Internal method for Digest authentication with retry logic."""
        max_retries = 3
        retry_delay = 0.5  # Initial retry delay in seconds
        
        for attempt in range(max_retries + 1):  # Add 1 to ensure at least one attempt
            try:
                # Calculate exponential backoff delay
                if attempt > 0:
                    delay = retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    _LOGGER.debug("Retrying after %.1f seconds (attempt %d/%d)", delay, attempt + 1, max_retries + 1)
                    await asyncio.sleep(delay)
                
                # First, send an unauthenticated GET request
                _LOGGER.debug("Attempt %d/%d: Making unauthenticated request to %s", attempt + 1, max_retries + 1, get_url)
                headers = {}
                resp = await self._session.get(get_url, headers=headers, allow_redirects=False)
                self._last_status_code = resp.status
                
                try:
                    # Handle 401 - Need authentication
                    if resp.status == 401:
                        auth_header = resp.headers.get('WWW-Authenticate', '')
                        _LOGGER.debug("Received 401 - WWW-Authenticate header: %s", auth_header)
                        if not auth_header.startswith('Digest '):
                            _LOGGER.error("Server does not support Digest authentication - auth scheme: %s", auth_header[:50])
                            raise SVKAuthenticationError("Server does not support Digest authentication. Please check if your device supports Digest authentication.")
                        
                        # Parse WWW-Authenticate header
                        auth_params = _parse_www_authenticate(auth_header)
                        
                        # Update stored digest parameters
                        self._digest_nonce = auth_params.get('nonce')
                        self._digest_opaque = auth_params.get('opaque')
                        self._digest_realm = auth_params.get('realm')
                        self._digest_qop = auth_params.get('qop', 'auth')
                        self._digest_algorithm = auth_params.get('algorithm', 'MD5')
                        
                        if not self._digest_nonce or not self._digest_realm:
                            _LOGGER.error("Missing required Digest authentication parameters: nonce=%s, realm=%s",
                                        bool(self._digest_nonce), bool(self._digest_realm))
                            raise SVKAuthenticationError("Invalid Digest authentication parameters received from server")
                        
                        # Increment nonce count
                        self._digest_nc += 1
                        nc_hex = f"{self._digest_nc:08x}"
                        
                        # Generate cnonce
                        import hashlib
                        import random
                        cnonce = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
                        
                        # Compute Digest authorization header
                        # Use the exact same URI that will be used in the request
                        uri = str(get_url.relative())
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
                        _LOGGER.debug("Retrying with Digest authentication")
                        headers["Authorization"] = auth_header
                        resp = await self._session.get(get_url, headers=headers, allow_redirects=False)
                        self._last_status_code = resp.status
                    
                    # Check for success
                    if resp.status == 200:
                        _LOGGER.debug("Successfully authenticated and received response")
                        _LOGGER.debug("Response headers: %s", dict(resp.headers))
                        _LOGGER.debug("Content-Type: %s", resp.headers.get('Content-Type', 'unknown'))
                        
                        # Parse JSON response with enhanced error handling
                        try:
                            # Read raw response first for debugging
                            response_text = await resp.text()
                            _LOGGER.debug("Raw response (first 200 chars): %s", response_text[:200])
                            
                            # Parse JSON from the text
                            data = json.loads(response_text)
                            _LOGGER.debug("Received JSON data with %d items", len(data) if isinstance(data, list) else "unknown")
                            _LOGGER.debug("Raw JSON response type: %s", type(data))
                            
                            # Check for empty or blank response
                            if not data:
                                _LOGGER.error("Empty JSON response received")
                                raise SVKConnectionError("Empty response body")
                            
                            # Use flexible parsing to handle different response formats
                            try:
                                result = _parse_json_response_flexible(data, response_text)
                                _LOGGER.debug("Successfully parsed response, returning %d items", len(result))
                                return result
                            except SVKInvalidDataFormatError as format_err:
                                _LOGGER.error("Data format error: %s", format_err.message)
                                _LOGGER.debug("Full response that caused format error: %s", response_text[:1000])
                                raise
                            
                        except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError) as err:
                            # We already have the response_text from above
                            if not response_text.strip():
                                raise SVKConnectionError("Blank response body") from err
                            
                            # Log the full response for debugging
                            _LOGGER.error("Invalid JSON response received. Status: %d, Content-Type: %s, Response (first 500 chars): %s",
                                         resp.status, resp.headers.get('Content-Type', 'unknown'), response_text[:500])
                            
                            raise SVKParseError("json", f"Invalid JSON response: {response_text[:100]}") from err
                    
                    # Handle other errors
                    if resp.status == 401:
                        _LOGGER.error("Authentication failed after Digest auth attempt - invalid credentials")
                        raise SVKAuthenticationError("Invalid username or password")
                    elif resp.status == 403:
                        _LOGGER.error("Access forbidden - check user permissions")
                        raise SVKAuthenticationError("Access forbidden - user may not have required permissions")
                    elif resp.status == 404:
                        _LOGGER.error("JSON API endpoint not found - device may not support JSON API")
                        raise SVKConnectionError("JSON API endpoint not found - device may not support this API")
                    elif resp.status >= 500:
                        _LOGGER.error("Server error %d - device may be experiencing issues", resp.status)
                        raise SVKConnectionError(f"Server error {resp.status} - device may be experiencing issues")
                    
                    text = await resp.text(errors="ignore")
                    _LOGGER.error("HTTP error %d from %s: %s", resp.status, get_url, text[:160])
                    raise SVKConnectionError(f"HTTP {resp.status} {get_url}: {text[:160]}")
                
                finally:
                    resp.release()
            
            except asyncio.TimeoutError as err:
                if attempt < max_retries:
                    # Exponential backoff is already handled at the start of the loop
                    _LOGGER.debug("Timeout on attempt %d, will retry with exponential backoff", attempt + 1)
                    continue
                _LOGGER.error("Timeout connecting to %s after %d attempts", self.host, attempt + 1)
                raise SVKTimeoutError(f"Timeout connecting to {self.host}") from err
            
            except aiohttp.ClientError as err:
                if attempt < max_retries:
                    # Exponential backoff is already handled at the start of the loop
                    _LOGGER.debug("Client error on attempt %d, will retry with exponential backoff: %s", attempt + 1, err)
                    continue
                _LOGGER.error("Client error connecting to %s after %d attempts: %s", self.host, attempt + 1, err)
                raise SVKConnectionError(f"Failed to fetch {path}: {err}") from err
        
        _LOGGER.error("Max retries exceeded for %s", path)
        raise SVKConnectionError(f"Max retries exceeded for {path}")
    
    async def read_values(self, ids: List[int]) -> List[Dict[str, Any]]:
        """Read values from the JSON API."""
        _LOGGER.info("read_values called with %d IDs", len(ids))
        _LOGGER.debug("Requesting IDs: %s", ids[:20])  # Log first 20 IDs
        
        if not ids:
            _LOGGER.warning("read_values called with empty ID list")
            return []
        
        # Make a single request for all IDs
        try:
            result = await self._request_with_digest_auth("/cgi-bin/json_values.cgi", ids)
            return result or []
        except Exception as err:
            _LOGGER.error("Request failed: %s", err)
            raise


async def main():
    """Main function to run the live connection test."""
    print("=" * 80)
    print("SVK Heatpump Live Connection Test")
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
    print(f"Requesting {len(test_ids)} IDs: {test_ids}")
    print()
    
    # Create client
    client = TestLOMJsonClient(host, username, password)
    
    try:
        # Start the client
        await client.start()
        
        # Make the request
        print("Making request to JSON API...")
        start_time = time.time()
        
        try:
            result = await client.read_values(test_ids)
            end_time = time.time()
            
            print(f"Request completed in {end_time - start_time:.2f} seconds")
            print(f"Received {len(result)} items")
            print()
            
            # Display the raw response
            print("RAW RESPONSE DATA:")
            print("-" * 40)
            for item in result:
                print(f"ID: {item.get('id', 'N/A')}, Name: {item.get('name', 'N/A')}, Value: {item.get('value', 'N/A')}")
            print()
            
            # Display parsed data in a more readable format
            print("PARSED DATA:")
            print("-" * 40)
            for item in result:
                item_id = item.get('id', 'N/A')
                item_name = item.get('name', 'N/A')
                item_value = item.get('value', 'N/A')
                
                # Try to convert numeric values
                try:
                    numeric_value = float(item_value)
                    print(f"ID {item_id} ({item_name}): {numeric_value}")
                except (ValueError, TypeError):
                    print(f"ID {item_id} ({item_name}): {item_value}")
            print()
            
            # Compare with expected format
            print("FORMAT ANALYSIS:")
            print("-" * 40)
            if len(result) == len(test_ids):
                print("✓ Received expected number of items")
            else:
                print(f"✗ Expected {len(test_ids)} items, received {len(result)} items")
            
            # Check if items have the expected structure
            valid_items = 0
            for item in result:
                if 'id' in item and 'name' in item and 'value' in item:
                    valid_items += 1
            
            if valid_items == len(result):
                print("✓ All items have expected structure (id, name, value)")
            else:
                print(f"✗ Only {valid_items}/{len(result)} items have expected structure")
            
            print()
            print("Test completed successfully!")
            
        except SVKConnectionError as err:
            print(f"Connection error: {err}")
            return 1
        except SVKAuthenticationError as err:
            print(f"Authentication error: {err}")
            return 1
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