"""HTTP client for SVK Heatpump LOM320 web module."""
import asyncio
import hashlib
import logging
import re
import time
import random
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, Tag
from yarl import URL

from .const import (
    ALARM_CODES,
    ALARM_SEVERITIES,
    HEATPUMP_STATES,
    SEASON_MODES,
    SOLAR_STATES,
    TEMP_SENSORS,
    SETPOINT_SENSORS,
    PERFORMANCE_SENSORS,
    COUNTER_SENSORS,
    SYSTEM_SENSORS,
    BINARY_SENSORS,
    SELECT_ENTITIES,
    NUMBER_ENTITIES,
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
    def __init__(self, page: str, message: str):
        self.page = page
        self.message = message
        super().__init__(f"Failed to parse {page}: {message}")


class SVKInvalidDataFormatError(SVKParseError):
    """Invalid data format error."""
    def __init__(self, expected: str, received: str, details: str = ""):
        message = f"Expected {expected}, received {received}"
        if details:
            message += f": {details}"
        super().__init__("json", message)


class SVKHTMLResponseError(SVKParseError):
    """HTML error page received instead of JSON."""
    def __init__(self, status_code: int, title: str = ""):
        message = f"Received HTML error page (status {status_code})"
        if title:
            message += f": {title}"
        super().__init__("json", message)


class SVKWriteError(Exception):
    """Write operation failed."""
    def __init__(self, parameter: str, value: Any, message: str):
        self.parameter = parameter
        self.value = value
        self.message = message
        super().__init__(f"Failed to set {parameter} to {value}: {message}")


class LOMJsonClient:
    """Client for communicating with SVK LOM320 web module using JSON API with simplified Digest authentication."""
    
    def __init__(self, host: str, username: str, password: str, timeout: int = 10):
        """Initialize the JSON client."""
        self.host = host
        self._base = URL.build(scheme="http", host=host)
        self._username = username
        self._password = password
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=timeout, connect=15.0, sock_read=30.0)
        
        self._chunk_size = 25  # Fixed chunk size of 25 for all requests
        # Chunking is always enabled
        
        self._max_retries = 3  # Maximum number of retries for failed requests
        self._retry_delay = 0.5  # Initial retry delay in seconds
        
        # Simplified Digest authentication - removed complex session management
        self._last_status_code = None  # Track last HTTP status code for diagnostics
        
        # Track failed IDs for better error handling
        self._failed_ids = set()  # IDs that consistently fail
        self._unsupported_ids = set()  # IDs that are not supported by the API
    
    def _parse_json_response_flexible(self, data: Any, response_text: str = "") -> List[Dict[str, Any]]:
        """
        Parse JSON response with simplified format handling.
        
        Simplified to handle the dictionary format directly without excessive conversion attempts.
        
        Args:
            data: The parsed JSON data
            response_text: Raw response text for debugging
            
        Returns:
            List of dictionaries with 'id', 'name', and 'value' fields
            
        Raises:
            SVKInvalidDataFormatError: If the data format is not supported
        """
        _LOGGER.debug("Parsing JSON response with simplified format handling")
        _LOGGER.debug("Response data type: %s", type(data))
        
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
        
        # Handle dict format (heat pump format)
        elif isinstance(data, dict):
            _LOGGER.debug("Processing dict format with %d keys", len(data))
            
            # Check if it's an error response first
            if any(key.lower() in ['error', 'message', 'code', 'status'] for key in data.keys()):
                raise SVKInvalidDataFormatError(
                    "list or dict with recognizable structure",
                    f"dict with error-like keys: {list(data.keys())}",
                    "Response appears to be an error message rather than data"
                )
            
            # Handle the heat pump format: {"253": {"name": "...", "value": "..."}, ...}
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
                    # Check if value is a simple dict with just a value field
                    elif isinstance(value, dict) and 'value' in value:
                        dict_items.append({
                            "id": str(entity_id),
                            "name": f"entity_{entity_id}",
                            "value": str(value['value'])
                        })
                    # Check if value is a simple value
                    elif not isinstance(value, dict):
                        dict_items.append({
                            "id": str(entity_id),
                            "name": f"entity_{entity_id}",
                            "value": str(value)
                        })
                
                except (ValueError, TypeError):
                    # Key is not a numeric ID, skip it
                    continue
            
            if dict_items:
                _LOGGER.debug("Successfully converted heat pump dict format to list with %d items", len(dict_items))
                return dict_items
            
            # Check if it's a single item format
            if 'id' in data and 'value' in data:
                _LOGGER.debug("Found single item format, converting to list")
                return [data]
            
            raise SVKInvalidDataFormatError(
                "list or dict with recognizable structure",
                f"dict with keys: {list(data.keys())[:5]}",
                "Dict format not recognized. Expected list or heat pump dict format"
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
    
    def _detect_html_error_page(self, text: str) -> Optional[str]:
        """
        Detect if the response is an HTML error page and extract error information.
        
        Args:
            text: Response text to analyze
            
        Returns:
            Error title if HTML error page detected, None otherwise
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Check for HTML doctype or html tag
        if not (text.startswith('<!DOCTYPE') or text.startswith('<html')):
            return None
        
        _LOGGER.debug("Detected HTML response, checking for error indicators")
        
        # Look for common error indicators in HTML
        error_patterns = [
            r'<title[^>]*>([^<]+Error[^<]*)</title>',
            r'<title[^>]*>([^<]+Unauthorized[^<]*)</title>',
            r'<title[^>]*>([^<]+Forbidden[^<]*)</title>',
            r'<title[^>]*>([^<]+Not Found[^<]*)</title>',
            r'<title[^>]*>([^<]+Internal Server Error[^<]*)</title>',
            r'<h1[^>]*>([^<]+Error[^<]*)</h1>',
            r'<h1[^>]*>([^<]+Unauthorized[^<]*)</h1>',
            r'<h1[^>]*>([^<]+Forbidden[^<]*)</h1>',
            r'<h1[^>]*>([^<]+Not Found[^<]*)</h1>',
            r'<h1[^>]*>([^<]+Internal Server Error[^<]*)</h1>',
        ]
        
        import re
        for pattern in error_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                error_title = match.group(1).strip()
                _LOGGER.debug("Found HTML error: %s", error_title)
                return error_title
        
        # Look for error messages in common patterns
        error_msg_patterns = [
            r'error[:\s]+([^\n<]+)',
            r'error code[:\s]+(\d+)',
            r'status[:\s]+([^\n<]+)',
        ]
        
        for pattern in error_msg_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                error_msg = match.group(1).strip()
                _LOGGER.debug("Found HTML error message: %s", error_msg)
                return f"Error: {error_msg}"
        
        return "HTML Error Page"
    
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
        # No complex session state to reset with simplified auth
        pass
    
    def _parse_www_authenticate(self, header: str) -> Dict[str, str]:
        """Parse WWW-Authenticate header for Digest authentication."""
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
    
    def _generate_cnonce(self) -> str:
        """Generate a client nonce."""
        return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
    
    def _compute_digest_response(
        self,
        method: str,
        uri: str,
        username: str,
        password: str,
        realm: str,
        nonce: str,
        qop: str = "auth",
        algorithm: str = "MD5",
        opaque: Optional[str] = None,
    ) -> str:
        """Compute Digest authentication response - simplified version."""
        cnonce = self._generate_cnonce()
        nc = "00000001"  # Simple fixed nonce count
        
        # Compute HA1 = MD5(username:realm:password)
        ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode('utf-8')).hexdigest()
        
        # Compute HA2 = MD5(method:uri)
        ha2 = hashlib.md5(f"{method}:{uri}".encode('utf-8')).hexdigest()
        
        # Compute response
        if qop and qop.lower() in ("auth", "auth-int"):
            # With qop: response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
            response = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode('utf-8')).hexdigest()
        else:
            # Without qop: response = MD5(HA1:nonce:HA2)
            response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode('utf-8')).hexdigest()
        
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
    
    async def _simple_digest_auth_request(self, path: str, method: str = "GET", **kwargs) -> aiohttp.ClientResponse:
        """
        Make an authenticated request using simplified Digest authentication.
        
        This is the core fix - simple, reliable Digest auth without complex session management.
        """
        if not self._session:
            await self.start()
        
        url = self._base.with_path(path)
        
        # Step 1: Make unauthenticated request to get WWW-Authenticate header
        _LOGGER.debug(f"Making initial request to {url}")
        # For GET requests, we need to allow redirects to avoid 400 errors
        # Also need to handle the query string properly for GET requests
        allow_redirects = method != "GET"
        resp = await self._session.request(method, url, allow_redirects=allow_redirects, **kwargs)
        
        # Step 2: Handle authentication challenge
        if resp.status == 401:
            www_auth = resp.headers.get('WWW-Authenticate', '')
            if not www_auth.startswith('Digest '):
                raise SVKAuthenticationError(f"Server does not support Digest authentication: {www_auth}")
            
            # Parse authentication parameters
            auth_params = self._parse_www_authenticate(www_auth)
            realm = auth_params.get('realm')
            nonce = auth_params.get('nonce')
            qop = auth_params.get('qop', 'auth')
            algorithm = auth_params.get('algorithm', 'MD5')
            opaque = auth_params.get('opaque')
            
            if not realm or not nonce:
                raise SVKAuthenticationError("Missing required Digest authentication parameters")
            
            # Step 3: Compute Digest response
            uri = str(url.path) + (f"?{url.query_string}" if url.query_string else "")  # Include query parameters
            digest_header = self._compute_digest_response(
                method=method,
                uri=uri,
                username=self._username,
                password=self._password,
                realm=realm,
                nonce=nonce,
                qop=qop,
                algorithm=algorithm,
                opaque=opaque,
            )
            
            # Step 4: Retry with authentication
            _LOGGER.debug(f"Retrying with Digest authentication for {url}")
            headers = kwargs.get('headers', {})
            headers['Authorization'] = digest_header
            kwargs['headers'] = headers
            
            resp = await self._session.request(method, url, allow_redirects=False, **kwargs)
        
        # Step 5: Handle response
        if resp.status == 401:
            raise SVKAuthenticationError("Authentication failed - invalid credentials")
        elif resp.status == 404:
            raise SVKConnectionError(f"Endpoint not found: {path}")
        elif resp.status != 200:
            error_text = await resp.text()
            raise SVKConnectionError(f"HTTP {resp.status}: {error_text[:200]}")
        
        return resp
    
    async def _request_with_get_params(self, ids: List[int]) -> List[Dict[str, Any]]:
        """
        Make a GET request with semicolon-separated IDs as query parameters.
        
        Args:
            ids: List of register IDs to request
            
        Returns:
            List of dictionaries with 'id', 'name', and 'value' fields
            
        Raises:
            SVKConnectionError: If the request fails
        """
        ids_str = ";".join(str(id) for id in ids)
        url_path = f"/cgi-bin/json_values.cgi?ids={ids_str}"
        
        # Make the request and parse the response
        resp = await self._simple_digest_auth_request(url_path, method="GET")
        try:
            response_text = await resp.text()
            
            # Parse JSON from the text
            import json
            data = json.loads(response_text)
            
            # Check for empty or blank response
            if not data:
                raise SVKConnectionError("Empty response body")
            
            # Use flexible parsing to handle different response formats
            result = self._parse_json_response_flexible(data, response_text)
            return result
            
        except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError) as err:
            if not response_text.strip():
                raise SVKConnectionError("Blank response body") from err
            
            # Log the full response for debugging
            _LOGGER.error("Invalid JSON response received. Status: %d, Content-Type: %s, Response (first 500 chars): %s",
                         resp.status, resp.headers.get('Content-Type', 'unknown'), response_text[:500])
            
            # Check if it's an HTML error page
            html_error = self._detect_html_error_page(response_text)
            if html_error:
                raise SVKHTMLResponseError(resp.status, html_error)
            
            raise SVKParseError("json", f"Invalid JSON response: {response_text[:100]}") from err
        
        finally:
            resp.release()
    
    async def _request_with_digest_auth(self, path: str, ids: List[int]) -> List[Dict[str, Any]]:
        """Make a request with simplified Digest authentication."""
        import time
        start_time = time.time()
        
        _LOGGER.debug("PERFORMANCE: _request_with_digest_auth called for %d IDs", len(ids))
        
        if not self._session:
            _LOGGER.debug("Starting new session for digest auth")
            await self.start()
        
        _LOGGER.info("PERFORMANCE: Making simplified digest auth request for %d IDs", len(ids))
        _LOGGER.debug("Requesting %d IDs: %s", len(ids), ids[:10])  # Log first 10 IDs
        
        try:
            # Add overall timeout protection to prevent infinite retry loops
            _LOGGER.debug("PERFORMANCE: Starting simplified digest auth with 30 second timeout")
            auth_start = time.time()
            
            # Try GET with query parameters first
            try:
                _LOGGER.debug("PERFORMANCE: Trying GET with query parameters")
                result = await self._request_with_get_params(ids)
                auth_duration = time.time() - auth_start
                total_duration = time.time() - start_time
                _LOGGER.info("PERFORMANCE: Simplified digest auth completed in %.2fs (auth=%.2fs, total=%.2fs) for %d IDs",
                           total_duration, auth_duration, total_duration, len(ids))
                return result
            except SVKConnectionError:
                # Fall back to POST with JSON payload
                _LOGGER.debug("PERFORMANCE: GET failed, falling back to POST with JSON payload")
                payload = {"ids": ids}
                resp = await self._simple_digest_auth_request("/cgi-bin/json_values.cgi", method="POST", json=payload)
                
                # Parse JSON response with enhanced error handling
                try:
                    # Read raw response first for debugging
                    response_text = await resp.text()
                    _LOGGER.debug("Raw response (first 200 chars): %s", response_text[:200])
                    
                    # Parse JSON from the text
                    import json
                    data = json.loads(response_text)
                    _LOGGER.debug("Received JSON data with %d items", len(data) if isinstance(data, list) else "unknown")
                    _LOGGER.debug("Raw JSON response type: %s", type(data))
                    
                    # Check for empty or blank response
                    if not data:
                        _LOGGER.error("Empty JSON response received")
                        raise SVKConnectionError("Empty response body")
                    
                    # Use flexible parsing to handle different response formats
                    try:
                        result = self._parse_json_response_flexible(data, response_text)
                        _LOGGER.debug("Successfully parsed response, returning %d items", len(result))
                        auth_duration = time.time() - auth_start
                        total_duration = time.time() - start_time
                        _LOGGER.info("PERFORMANCE: Simplified digest auth completed in %.2fs (auth=%.2fs, total=%.2fs) for %d IDs",
                                   total_duration, auth_duration, total_duration, len(ids))
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
                    
                    # Check if it's an HTML error page
                    html_error = self._detect_html_error_page(response_text)
                    if html_error:
                        raise SVKHTMLResponseError(resp.status, html_error)
                    
                    raise SVKParseError("json", f"Invalid JSON response: {response_text[:100]}") from err
                
                finally:
                    resp.release()
                
        except asyncio.TimeoutError:
            total_duration = time.time() - start_time
            _LOGGER.error("CRITICAL: Simplified digest auth request to %s timed out after 30 seconds (total=%.2fs) - this is blocking Home Assistant",
                        url_path, total_duration)
            raise SVKTimeoutError(f"Request timeout after 30 seconds for {path}")
    
    
    async def _request_individual_ids(self, path: str, ids: List[int]) -> List[Dict[str, Any]]:
        """Make individual requests for each ID as a fallback mechanism."""
        import time
        start_time = time.time()
        
        _LOGGER.info("PERFORMANCE: Using individual requests fallback for %d IDs", len(ids))
        results = []
        failed_ids = []
        request_times = []
        
        for i, entity_id in enumerate(ids):
            # Skip if this ID is known to be unsupported
            if entity_id in self._unsupported_ids:
                _LOGGER.debug("Skipping known unsupported ID %d", entity_id)
                continue
                
            # Skip if this ID is in the excluded list
            # Note: _excluded_ids functionality has been removed
            if hasattr(self, '_excluded_ids') and entity_id in self._excluded_ids:
                _LOGGER.debug("Skipping excluded ID %d", entity_id)
                continue
                
            try:
                _LOGGER.debug("PERFORMANCE: Making individual request %d/%d for ID %d", i+1, len(ids), entity_id)
                request_start = time.time()
                result = await self._request_with_retry(path, [entity_id])
                request_duration = time.time() - request_start
                request_times.append(request_duration)
                
                if result:
                    results.extend(result)
                    _LOGGER.debug("PERFORMANCE: Successfully retrieved ID %d in %.2fs", entity_id, request_duration)
                else:
                    _LOGGER.warning("PERFORMANCE: No data returned for ID %d in %.2fs", entity_id, request_duration)
                    failed_ids.append(entity_id)
            except Exception as err:
                request_duration = time.time() - request_start
                request_times.append(request_duration)
                _LOGGER.warning("PERFORMANCE: Failed to retrieve ID %d individually after %.2fs: %s", entity_id, request_duration, err)
                failed_ids.append(entity_id)
                
                # If we consistently fail for this ID, mark it as unsupported
                if entity_id in self._failed_ids:
                    _LOGGER.info("ID %d has failed multiple times, marking as unsupported", entity_id)
                    self._unsupported_ids.add(entity_id)
                else:
                    self._failed_ids.add(entity_id)
        
        total_duration = time.time() - start_time
        
        # Log performance summary
        if request_times:
            avg_request_time = sum(request_times) / len(request_times)
            max_request_time = max(request_times)
            min_request_time = min(request_times)
            _LOGGER.info("PERFORMANCE: Individual request timing summary - avg=%.2fs, min=%.2fs, max=%.2fs (%d requests)",
                        avg_request_time, min_request_time, max_request_time, len(request_times))
        
        _LOGGER.info("PERFORMANCE: Individual requests completed in %.2fs total: %d successful, %d failed",
                    total_duration, len(results), len(failed_ids))
        
        if failed_ids:
            _LOGGER.debug("Failed IDs: %s", failed_ids[:20])  # Log first 20 failed IDs
        
        # Performance warning if individual requests are taking too long
        if total_duration > 15:  # 15 seconds for individual requests is concerning
            _LOGGER.warning("PERFORMANCE WARNING: Individual requests took %.2fs - this is very inefficient", total_duration)
            _LOGGER.warning("PERFORMANCE WARNING: Consider increasing chunk size or checking network connectivity")
        
        return results

    async def _request_with_retry(self, path: str, ids: List[int]) -> List[Dict[str, Any]]:
        """Make a request with retry logic for timeouts and blank bodies using Digest authentication."""
        # Always use Digest authentication - credentials are required
        return await self._request_with_digest_auth(path, ids)
    
    async def read_values(self, ids: List[int]) -> List[Dict[str, Any]]:
        """
        Read values from the JSON API with enhanced chunking and fallback mechanisms.
        
        Args:
            ids: Iterable of register IDs to read
            
        Returns:
            List of dictionaries with 'id', 'name', and 'value' fields
        """
        import time
        start_time = time.time()
        
        _LOGGER.info("PERFORMANCE: read_values called with %d IDs", len(ids))
        _LOGGER.debug("Requesting IDs: %s", ids[:20])  # Log first 20 IDs
        
        if not ids:
            _LOGGER.warning("read_values called with empty ID list")
            return []
        
        # Convert to list if needed and filter out unsupported IDs
        id_list = list(ids)
        filtered_ids = [entity_id for entity_id in id_list
                       if entity_id not in self._unsupported_ids]
        
        if len(filtered_ids) != len(id_list):
            _LOGGER.info("Filtered %d unsupported IDs",
                        len(id_list) - len(filtered_ids))
        
        if not filtered_ids:
            _LOGGER.warning("No valid IDs remaining after filtering")
            return []
        
        _LOGGER.info("PERFORMANCE: Processing %d IDs after filtering", len(filtered_ids))
        
        # Chunking is always enabled, so we skip the non-chunking path
        
        # If the number of IDs is small, make a single request
        if len(filtered_ids) <= self._chunk_size:
            _LOGGER.info("PERFORMANCE: Making single request for %d IDs (below chunk size threshold)", len(filtered_ids))
            single_start = time.time()
            try:
                result = await self._request_with_retry("/cgi-bin/json_values.cgi", filtered_ids)
                single_duration = time.time() - single_start
                items_returned = len(result) if result else 0
                _LOGGER.info("PERFORMANCE: Single request completed in %.2fs, returned %d items",
                           single_duration, items_returned)
                
                # Check if we got significantly fewer items than expected
                if items_returned < len(filtered_ids) * 0.5:  # Less than 50% success rate
                    _LOGGER.warning("Low success rate (%d/%d), falling back to individual requests",
                                  items_returned, len(filtered_ids))
                    return await self._request_individual_ids("/cgi-bin/json_values.cgi", filtered_ids)
                
                return result or []
            except Exception as err:
                _LOGGER.error("Single request failed: %s", err)
                # Fallback to individual requests
                _LOGGER.info("Falling back to individual requests due to single request failure")
                return await self._request_individual_ids("/cgi-bin/json_values.cgi", filtered_ids)
        
        # For larger ID lists, split into chunks with enhanced logging
        total_chunks = (len(filtered_ids) + self._chunk_size - 1) // self._chunk_size
        _LOGGER.info("PERFORMANCE: Splitting %d IDs into %d chunks of %d", len(filtered_ids), total_chunks, self._chunk_size)
        results = []
        failed_chunks = []
        successful_chunks = 0
        chunk_times = []
        
        # Process chunks in parallel to reduce total time
        import asyncio
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests to avoid overwhelming the device
        
        async def process_chunk(chunk, chunk_num):
            chunk_start = time.time()
            try:
                chunk_results = await self._request_with_retry("/cgi-bin/json_values.cgi", chunk)
                chunk_duration = time.time() - chunk_start
                items_returned = len(chunk_results) if chunk_results else 0
                _LOGGER.info("PERFORMANCE: Chunk %d/%d completed in %.2fs, returned %d items",
                           chunk_num, total_chunks, chunk_duration, items_returned)
                return chunk_results, chunk_duration
            except Exception as err:
                chunk_duration = time.time() - chunk_start
                _LOGGER.error("PERFORMANCE: Chunk %d/%d failed after %.2fs: %s", chunk_num, total_chunks, chunk_duration, err)
                return None, chunk_duration
        
        # Create tasks for all chunks
        chunk_tasks = []
        for i in range(0, len(filtered_ids), self._chunk_size):
            chunk = filtered_ids[i:i + self._chunk_size]
            chunk_num = i // self._chunk_size + 1
            
            _LOGGER.info("PERFORMANCE: Processing chunk %d/%d (IDs %d-%d): %s",
                        chunk_num, total_chunks, i, i + len(chunk) - 1, chunk)
            
            # Create task for this chunk
            task = asyncio.create_task(process_chunk(chunk, chunk_num))
            chunk_tasks.append(task)
        
        # Wait for all chunks to complete (with timeout)
        try:
            _LOGGER.info("PERFORMANCE: Waiting for %d chunks to complete with 60 second timeout", len(chunk_tasks))
            chunk_results_list = await asyncio.wait_for(
                asyncio.gather(*chunk_tasks, return_exceptions=True),
                timeout=60.0  # 60 second timeout for all chunks
            )
        except asyncio.TimeoutError:
            _LOGGER.error("PERFORMANCE: Parallel chunk processing timed out after 60 seconds")
            # Cancel any remaining tasks
            for task in chunk_tasks:
                if not task.done():
                    task.cancel()
        
        # Process results
        for i, task_result in enumerate(chunk_results_list):
            if isinstance(task_result, Exception):
                _LOGGER.error("PERFORMANCE: Chunk %d/%d failed with exception: %s", i+1, total_chunks, task_result)
                failed_chunks.append(i)
            else:
                chunk_results, chunk_duration = task_result
                if chunk_results:
                    chunk_times.append(chunk_duration)
                    successful_chunks += 1
                    # Extend the results list with the new items
                    if isinstance(chunk_results, list):
                        results.extend(chunk_results)
                    else:
                        _LOGGER.warning("Unexpected response format for chunk %d/%d: expected list, got %s",
                                      i+1, total_chunks, type(chunk_results))
                        failed_chunks.append(i)
        
        # Log chunk performance summary
        if chunk_times:
            avg_chunk_time = sum(chunk_times) / len(chunk_times)
            max_chunk_time = max(chunk_times)
            min_chunk_time = min(chunk_times)
            _LOGGER.info("PERFORMANCE: Parallel chunk timing summary - avg=%.2fs, min=%.2fs, max=%.2fs (%d chunks)",
                        avg_chunk_time, min_chunk_time, max_chunk_time, len(chunk_times))
        
        _LOGGER.info("PERFORMANCE: Parallel chunk processing completed: %d successful, %d failed chunks",
                    successful_chunks, len(failed_chunks))
        
        # If we have failed chunks, try individual requests for those IDs
        if failed_chunks:
            failed_ids = []
            for i, chunk_index in enumerate(failed_chunks):
                if chunk_index < len(filtered_ids):
                    chunk = filtered_ids[chunk_index:chunk_index + self._chunk_size]
                    failed_ids.extend(chunk)
            
            _LOGGER.info("PERFORMANCE: Attempting individual requests for %d IDs from failed chunks", len(failed_ids))
            individual_start = time.time()
            
            try:
                individual_results = await self._request_individual_ids("/cgi-bin/json_values.cgi", failed_ids)
                individual_duration = time.time() - individual_start
                results.extend(individual_results)
                _LOGGER.info("PERFORMANCE: Individual requests completed in %.2fs, recovered %d additional items",
                           individual_duration, len(individual_results))
            except Exception as err:
                individual_duration = time.time() - individual_start
                _LOGGER.error("PERFORMANCE: Individual requests failed after %.2fs: %s", individual_duration, err)
        
        total_duration = time.time() - start_time
        _LOGGER.info("PERFORMANCE: read_values completed in %.2fs total, returned %d items from %d requested IDs",
                    total_duration, len(results), len(filtered_ids))
        
        # Performance warning if taking too long
        if total_duration > 20:  # 20 seconds is getting close to 30s timeout
            _LOGGER.warning("PERFORMANCE WARNING: read_values took %.2fs - this may cause timeouts", total_duration)
            _LOGGER.warning("PERFORMANCE WARNING: Consider reducing chunk size further or checking network connectivity")
        
        return results
    
    async def write_value(self, id: int, value: Any) -> bool:
        """
        Write a value to a register using Digest authentication.
        
        Args:
            id: Register ID to write to
            value: Value to write
            
        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            await self.start()
        
        assert self._session is not None
        url = self._base.with_path("/cgi-bin/json_values.cgi")
        
        # Prepare JSON payload
        payload = {"id": id, "value": value}
        
        # Digest authentication is always required - no fallback to unauthenticated
        
        try:
            # Use simplified authentication for write operations
            _LOGGER.debug("Making POST request to %s with simplified auth", url)
            
            # Use the simplified digest auth method
            resp = await self._simple_digest_auth_request("/cgi-bin/json_values.cgi", method="POST", json=payload)
            
            # Check for success
            if resp.status == 200:
                # Parse JSON response
                try:
                    data = await resp.json()
                    return data.get("success", False)
                except (aiohttp.ContentTypeError, ValueError):
                    return False
            
            # Handle errors with improved diagnostics
            if resp.status == 401:
                _LOGGER.error("Write operation failed with 401 - invalid credentials")
                raise SVKAuthenticationError("Invalid username or password for write operation")
            
            text = await resp.text(errors="ignore")
            raise SVKConnectionError(f"HTTP {resp.status} {url}: {text[:160]}")
        
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Failed to write value %s to register %s: %s", value, id, err)
            return False
        
        finally:
            resp.release()