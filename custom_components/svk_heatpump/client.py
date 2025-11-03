"""HTTP client for SVK Heatpump LOM320 web module."""

import asyncio
import hashlib
import json
import logging
import random
import re
import time
from typing import Any

import aiohttp
from yarl import URL

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


class SVKInvalidDataFormatError(Exception):
    """Invalid data format error."""

    def __init__(self, expected: str, received: str, details: str = ""):
        message = f"Expected {expected}, received {received}"
        if details:
            message += f": {details}"
        super().__init__(f"JSON parsing error: {message}")


class SVKWriteError(Exception):
    """Write operation failed."""

    def __init__(self, parameter: str, value: Any, message: str):
        self.parameter = parameter
        self.value = value
        self.message = message
        super().__init__(f"Failed to set {parameter} to {value}: {message}")


class LOMJsonClient:
    """Client for communicating with SVK LOM320 web module using JSON API with Digest authentication."""

    def __init__(self, host: str, username: str, password: str, timeout: int = 10):
        """Initialize the JSON client."""
        self.host = host
        self._base = URL.build(scheme="http", host=host)
        self._username = username
        self._password = password
        self._session: aiohttp.ClientSession | None = None
        self._timeout = aiohttp.ClientTimeout(
            total=timeout, connect=15.0, sock_read=30.0
        )

        self._chunk_size = 25  # Fixed chunk size of 25 for all requests
        self._max_retries = 3  # Maximum number of retries for failed requests
        self._retry_delay = 0.5  # Initial retry delay in seconds

        # Authentication state tracking
        self._auth_nonce = None  # Current nonce for authentication
        self._auth_realm = None  # Current realm for authentication
        self._auth_qop = None  # Current qop for authentication
        self._auth_algorithm = None  # Current algorithm for authentication
        self._auth_opaque = None  # Current opaque for authentication
        self._last_auth_time = 0  # Timestamp of last successful authentication
        self._auth_valid_duration = (
            300  # Nonce validity duration in seconds (5 minutes)
        )

        # Default ID list - configurable
        self._default_ids = [
            299,
            255,
            256,
            257,
            258,
            259,
            262,
            263,
            422,
            388,
            298,
            376,
            505,
            302,
            435,
            301,
            382,
            405,
            222,
            223,
            224,
            225,
            234,
            438,
            437,
        ]

        # Track failed IDs for better error handling
        self._failed_ids: set[int] = set()  # IDs that consistently fail
        self._unsupported_ids: set[int] = set()  # IDs that are not supported by the API

    def _parse_json_response(self, data: Any) -> list[dict[str, Any]]:
        """
        Parse JSON response in the expected format: [{"id": "299", "name": "HeatPump.CapacityAct", "value": "25.2"}, ...]

        Args:
            data: The parsed JSON data

        Returns:
            List of dictionaries with 'id', 'name', and 'value' fields

        Raises:
            SVKInvalidDataFormatError: If the data format is not as expected
        """
        _LOGGER.debug("Parsing JSON response")
        _LOGGER.debug("Response data type: %s", type(data))

        # Handle list format (expected format)
        if isinstance(data, list):
            _LOGGER.debug("Processing list format with %d items", len(data))
            valid_items = 0
            for item in data:
                if (
                    isinstance(item, dict)
                    and "id" in item
                    and "name" in item
                    and "value" in item
                ):
                    valid_items += 1

            if valid_items > 0:
                _LOGGER.debug("Found %d valid items in list format", valid_items)
                return data
            else:
                raise SVKInvalidDataFormatError(
                    "list with dictionaries containing 'id', 'name', and 'value' fields",
                    "list without valid items",
                    f"List has {len(data)} items but none contain required fields",
                )

        # Handle dict format (alternative format)
        elif isinstance(data, dict):
            _LOGGER.debug("Processing dict format with %d keys", len(data))

            # Check if it's an error response first
            if any(
                key.lower() in ["error", "message", "code", "status"]
                for key in data.keys()
            ):
                raise SVKInvalidDataFormatError(
                    "list or dict with recognizable structure",
                    f"dict with error-like keys: {list(data.keys())}",
                    "Response appears to be an error message rather than data",
                )

            # Handle the heat pump format: {"253": {"name": "...", "value": "..."}, ...}
            dict_items = []
            for key, value in data.items():
                try:
                    # Try to convert key to integer ID
                    entity_id = int(key)

                    # Check if value is a dict with name and value fields
                    if isinstance(value, dict) and "name" in value and "value" in value:
                        # This is the expected heat pump format
                        dict_items.append(
                            {
                                "id": str(entity_id),
                                "name": str(value["name"]),
                                "value": str(value["value"]),
                            }
                        )
                    # Check if value is a simple dict with just a value field
                    elif isinstance(value, dict) and "value" in value:
                        dict_items.append(
                            {
                                "id": str(entity_id),
                                "name": f"entity_{entity_id}",
                                "value": str(value["value"]),
                            }
                        )
                    # Check if value is a simple value
                    elif not isinstance(value, dict):
                        dict_items.append(
                            {
                                "id": str(entity_id),
                                "name": f"entity_{entity_id}",
                                "value": str(value),
                            }
                        )

                except (ValueError, TypeError):
                    # Key is not a numeric ID, skip it
                    continue

            if dict_items:
                _LOGGER.debug(
                    "Successfully converted heat pump dict format to list with %d items",
                    len(dict_items),
                )
                return dict_items

            raise SVKInvalidDataFormatError(
                "list or dict with recognizable structure",
                f"dict with keys: {list(data.keys())[:5]}",
                "Dict format not recognized. Expected list or heat pump dict format",
            )

        else:
            raise SVKInvalidDataFormatError(
                "list or dict",
                f"{type(data).__name__}",
                f"Unsupported data type: {type(data).__name__}",
            )

    async def start(self) -> None:
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

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _parse_www_authenticate(self, header: str) -> dict[str, str]:
        """Parse WWW-Authenticate header for Digest authentication."""
        auth_params: dict[str, str] = {}
        if not header.startswith("Digest "):
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
        opaque: str | None = None,
    ) -> str:
        """Compute Digest authentication response."""
        cnonce = self._generate_cnonce()
        nc = "00000001"  # Simple fixed nonce count

        # Compute HA1 = MD5(username:realm:password)
        ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()

        # Compute HA2 = MD5(method:uri)
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()

        # Compute response
        if qop and qop.lower() in ("auth", "auth-int"):
            # With qop: response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
            response = hashlib.md5(
                f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
            ).hexdigest()
        else:
            # Without qop: response = MD5(HA1:nonce:HA2)
            response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

        # Build Authorization header
        auth_parts = [
            f'username="{username}"',
            f'realm="{realm}"',
            f'nonce="{nonce}"',
            f'uri="{uri}"',
            f'response="{response}"',
            f"algorithm={algorithm}",
        ]

        if qop:
            auth_parts.extend(
                [
                    f"qop={qop}",
                    f"nc={nc}",
                    f'cnonce="{cnonce}"',
                ]
            )

        if opaque:
            auth_parts.append(f'opaque="{opaque}"')

        return f"Digest {', '.join(auth_parts)}"

    def _is_authentication_valid(self) -> bool:
        """
        Check if current authentication state is still valid.

        Returns:
            True if authentication is valid, False otherwise
        """
        if not self._auth_nonce or not self._auth_realm:
            return False

        current_time = time.time()
        # Check if nonce has expired (typically 5-10 minutes)
        if current_time - self._last_auth_time > self._auth_valid_duration:
            _LOGGER.debug("Authentication nonce has expired, will re-authenticate")
            return False

        return True

    def _invalidate_authentication(self) -> None:
        """Invalidate current authentication state."""
        self._auth_nonce = None
        self._auth_realm = None
        self._auth_qop = None
        self._auth_algorithm = None
        self._auth_opaque = None
        self._last_auth_time = 0
        _LOGGER.debug("Authentication state invalidated")

    async def _digest_auth_request(
        self, path: str, method: str = "GET", **kwargs
    ) -> aiohttp.ClientResponse:
        """
        Make an authenticated request using Digest authentication with retry logic.
        """
        if not self._session:
            await self.start()

        # Parse the path to separate actual path from query parameters
        if "?" in path:
            actual_path, query_string = path.split("?", 1)
            url = self._base.with_path(actual_path).with_query(query_string)
        else:
            actual_path = path
            url = self._base.with_path(path)
        max_auth_retries = 2  # Maximum authentication attempts
        base_delay = 0.5  # Base delay for exponential backoff

        for auth_attempt in range(max_auth_retries + 1):
            try:
                # Check if we have valid authentication
                if self._is_authentication_valid():
                    # Use existing authentication
                    _LOGGER.debug(
                        "Using existing authentication for %s (attempt %d)",
                        url, auth_attempt + 1
                    )

                    # Compute digest response with stored parameters
                    # Use the full path including query parameters for Digest auth
                    uri = path
                    digest_header = self._compute_digest_response(
                        method=method,
                        uri=uri,
                        username=self._username,
                        password=self._password,
                        realm=self._auth_realm or "",
                        nonce=self._auth_nonce or "",
                        qop=self._auth_qop or "",
                        algorithm=self._auth_algorithm or "",
                        opaque=self._auth_opaque,
                    )

                    headers = kwargs.get("headers", {})
                    headers["Authorization"] = digest_header
                    kwargs["headers"] = headers

                    # Check if session is None and reinitialize if needed
                    if self._session is None:
                        await self.start()
                        if self._session is None:  # Check again after start()
                            raise SVKConnectionError("Failed to initialize HTTP session")

                    resp = await self._session.request(
                        method, url, allow_redirects=False, **kwargs
                    )

                    # Check if authentication is still valid
                    if resp.status == 401:
                        _LOGGER.warning(
                            "Existing authentication rejected, invalidating auth state"
                        )
                        self._invalidate_authentication()
                        resp.release()
                        continue  # Try to re-authenticate
                    elif resp.status == 200:
                        return resp
                    else:
                        # Handle other HTTP errors
                        error_text = await resp.text()
                        raise SVKConnectionError(
                            f"HTTP {resp.status}: {error_text[:200]}"
                        )
                else:
                    # Need to authenticate from scratch
                    _LOGGER.debug(
                        "Authenticating from scratch for %s (attempt %d)",
                        url, auth_attempt + 1
                    )

                    # Step 1: Make unauthenticated request to get WWW-Authenticate header
                    allow_redirects = method != "GET"
                    
                    # Check if session is None and reinitialize if needed
                    if self._session is None:
                        await self.start()
                        if self._session is None:  # Check again after start()
                            raise SVKConnectionError("Failed to initialize HTTP session")
                    
                    resp = await self._session.request(
                        method, url, allow_redirects=allow_redirects, **kwargs
                    )

                    # Step 2: Handle authentication challenge
                    if resp.status == 401:
                        www_auth = resp.headers.get("WWW-Authenticate", "")
                        if not www_auth.startswith("Digest "):
                            raise SVKAuthenticationError(
                                f"Server does not support Digest authentication: {www_auth}"
                            )

                        # Parse and store authentication parameters
                        auth_params = self._parse_www_authenticate(www_auth)
                        self._auth_realm = auth_params.get("realm")
                        self._auth_nonce = auth_params.get("nonce")
                        self._auth_qop = auth_params.get("qop", "auth")
                        self._auth_algorithm = auth_params.get("algorithm", "MD5")
                        self._auth_opaque = auth_params.get("opaque")

                        if not self._auth_realm or not self._auth_nonce:
                            raise SVKAuthenticationError(
                                "Missing required Digest authentication parameters"
                            )

                        # Step 3: Compute Digest response
                        # Use the full path including query parameters for Digest auth
                        uri = path
                        digest_header = self._compute_digest_response(
                            method=method,
                            uri=uri,
                            username=self._username,
                            password=self._password,
                            realm=self._auth_realm,
                            nonce=self._auth_nonce,
                            qop=self._auth_qop,
                            algorithm=self._auth_algorithm,
                            opaque=self._auth_opaque,
                        )

                        # Step 4: Retry with authentication
                        _LOGGER.debug("Retrying with Digest authentication for %s", url)
                        headers = kwargs.get("headers", {})
                        headers["Authorization"] = digest_header
                        kwargs["headers"] = headers

                        resp = await self._session.request(
                            method, url, allow_redirects=False, **kwargs
                        )

                        # Check if authentication was successful
                        if resp.status == 200:
                            self._last_auth_time = time.time()
                            _LOGGER.debug("Authentication successful")
                            return resp
                        elif resp.status == 401:
                            _LOGGER.warning(
                                "Authentication failed with 401, invalidating auth state"
                            )
                            self._invalidate_authentication()
                            resp.release()
                            continue  # Try again
                        else:
                            # Handle other HTTP errors
                            error_text = await resp.text()
                            raise SVKConnectionError(
                                f"HTTP {resp.status}: {error_text[:200]}"
                            )
                    else:
                        # Unexpected response status
                        error_text = await resp.text()
                        raise SVKConnectionError(
                            f"Unexpected HTTP {resp.status}: {error_text[:200]}"
                        )

            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("Request attempt %d failed: %s", auth_attempt + 1, err)

                if auth_attempt < max_auth_retries:
                    # Exponential backoff with jitter
                    delay = base_delay * (2**auth_attempt) + random.uniform(0.1, 0.5)
                    _LOGGER.debug("Retrying in %.2f seconds...", delay)
                    await asyncio.sleep(delay)

                    # Invalidate authentication on connection errors
                    self._invalidate_authentication()
                else:
                    raise SVKConnectionError(
                        f"Request failed after {max_auth_retries + 1} attempts: {err}"
                    ) from err

        # This should not be reached, but just in case
        raise SVKConnectionError("Authentication failed after all retry attempts")

    async def _request_with_get_params(self, ids: list[int]) -> list[dict[str, Any]]:
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
        resp = await self._digest_auth_request(url_path, method="GET")
        try:
            response_text = await resp.text()

            # Check for empty response before JSON parsing
            if not response_text or not response_text.strip():
                _LOGGER.error("Empty response received from GET request")
                _LOGGER.error(
                    "Response status: %d, Content-Type: %s, Content-Length: %s",
                    resp.status,
                    resp.headers.get("Content-Type", "unknown"),
                    resp.headers.get("Content-Length", "unknown"),
                )
                _LOGGER.error("Requested IDs: %s", ids)
                raise SVKConnectionError("Empty response body from GET request")

            # Parse JSON from the text
            import json

            try:
                data = json.loads(response_text)
                _LOGGER.debug(
                    "GET request JSON data with %d items",
                    len(data) if isinstance(data, list) else "unknown",
                )
            except json.JSONDecodeError as json_err:
                _LOGGER.error("JSON decode error in GET request: %s", json_err)
                _LOGGER.error(
                    "Response status: %d, Content-Type: %s, Content-Length: %s",
                    resp.status,
                    resp.headers.get("Content-Type", "unknown"),
                    resp.headers.get("Content-Length", "unknown"),
                )
                _LOGGER.error(
                    "Raw response text (first 200 chars): %s", repr(response_text[:200])
                )
                raise SVKInvalidDataFormatError(
                    "valid JSON", f"JSON decode error in GET: {json_err}"
                ) from json_err

            # Check for empty or blank response after parsing
            if not data:
                _LOGGER.error("Empty JSON data received from GET request")
                _LOGGER.error(
                    "Response status: %d, Content-Type: %s, Content-Length: %s",
                    resp.status,
                    resp.headers.get("Content-Type", "unknown"),
                    resp.headers.get("Content-Length", "unknown"),
                )
                _LOGGER.error("Requested IDs: %s", ids)
                raise SVKConnectionError("Empty JSON response body from GET request")

            # Parse the response
            result = self._parse_json_response(data)
            return result

        except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError) as err:
            if not response_text.strip():
                raise SVKConnectionError("Blank response body") from err

            # Log the full response for debugging
            _LOGGER.error(
                "Invalid JSON response received. Status: %d, Content-Type: %s, Response (first 500 chars): %s",
                resp.status,
                resp.headers.get("Content-Type", "unknown"),
                response_text[:500],
            )

            raise SVKInvalidDataFormatError(
                "valid JSON", f"Invalid JSON response: {response_text[:100]}"
            ) from err

        finally:
            resp.release()

    async def read_values(self, ids: list[int] | None = None) -> list[dict[str, Any]]:
        """
        Read values from the JSON API using Digest authentication.

        Args:
            ids: Optional list of register IDs to read. If None, uses default IDs.

        Returns:
            List of dictionaries with 'id', 'name', and 'value' fields
        """
        # Use default IDs if none provided
        if ids is None:
            ids = self._default_ids

        _LOGGER.info("Reading values for %d IDs", len(ids))
        _LOGGER.debug("Requesting IDs: %s", ids[:20])  # Log first 20 IDs

        if not ids:
            _LOGGER.warning("read_values called with empty ID list")
            return []

        # Convert to list if needed and filter out unsupported IDs
        id_list = list(ids)
        filtered_ids = [
            entity_id for entity_id in id_list if entity_id not in self._unsupported_ids
        ]

        if len(filtered_ids) != len(id_list):
            _LOGGER.info(
                "Filtered %d unsupported IDs", len(id_list) - len(filtered_ids)
            )

        if not filtered_ids:
            _LOGGER.warning("No valid IDs remaining after filtering")
            return []

        # Process IDs in chunks
        results = []
        total_chunks = (len(filtered_ids) + self._chunk_size - 1) // self._chunk_size

        for i in range(0, len(filtered_ids), self._chunk_size):
            chunk = filtered_ids[i : i + self._chunk_size]
            chunk_num = i // self._chunk_size + 1

            _LOGGER.debug(
                "Processing chunk %d/%d (IDs %d-%d): %s",
                chunk_num,
                total_chunks,
                i,
                i + len(chunk) - 1,
                chunk,
            )

            try:
                chunk_results = await self._request_with_get_params(chunk)
                if chunk_results:
                    results.extend(chunk_results)
                    _LOGGER.debug(
                        "Chunk %d/%d completed successfully, returned %d items",
                        chunk_num,
                        total_chunks,
                        len(chunk_results),
                    )
                else:
                    _LOGGER.warning(
                        "Chunk %d/%d returned no results", chunk_num, total_chunks
                    )
            except Exception as err:
                _LOGGER.error("Chunk %d/%d failed: %s", chunk_num, total_chunks, err)
                # Continue with other chunks instead of failing completely

        _LOGGER.info(
            "Read values completed: %d items returned from %d requested IDs",
            len(results),
            len(filtered_ids),
        )

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

        # Prepare JSON payload
        payload = {"id": id, "value": value}
        start_time = time.time()

        resp = None
        try:
            _LOGGER.info(
                "WRITE_OPERATION: Starting write of value %s to register %s", value, id
            )
            _LOGGER.debug(
                "WRITE_OPERATION: Request payload: %s", payload
            )
            _LOGGER.debug(
                "WRITE_OPERATION: Authentication state valid: %s", self._is_authentication_valid()
            )

            resp = await self._digest_auth_request(
                "/cgi-bin/json_values.cgi", method="POST", json=payload
            )

            # Log timing and response details
            request_time = time.time() - start_time
            _LOGGER.debug(
                "WRITE_OPERATION: Request completed in %.2f seconds, status: %d",
                request_time, resp.status
            )
            _LOGGER.debug(
                "WRITE_OPERATION: Response headers: %s", dict(resp.headers)
            )

            # Check for success
            if resp.status == 200:
                # Parse JSON response with enhanced error handling
                response_text = await resp.text(errors="ignore")
                _LOGGER.debug(
                    "WRITE_OPERATION: Raw response text: %s", response_text[:200]
                )
                
                try:
                    data = json.loads(response_text)
                    _LOGGER.debug(
                        "WRITE_OPERATION: Parsed JSON response: %s", data
                    )
                    
                    success = bool(data.get("success", False))
                    
                    if success:
                        _LOGGER.info(
                            "WRITE_OPERATION: Successfully wrote value %s to register %s",
                            value, id
                        )
                        return True
                    else:
                        # Enhanced error logging for failed writes
                        error_message = data.get("message", data.get("error", "Unknown error"))
                        error_code = data.get("code", "N/A")
                        _LOGGER.error(
                            "WRITE_OPERATION: Heat pump rejected write to register %s: %s",
                            id, error_message
                        )
                        _LOGGER.error(
                            "WRITE_OPERATION: Error details - Code: %s, Value: %s, Full response: %s",
                            error_code, value, data
                        )
                        
                        # Create a detailed error for diagnostics
                        raise SVKWriteError(
                            parameter=str(id),
                            value=value,
                            message=f"Heat pump rejected write: {error_message} (code: {error_code})"
                        )
                        
                except json.JSONDecodeError as json_err:
                    _LOGGER.error(
                        "WRITE_OPERATION: JSON decode error for register %s: %s",
                        id, json_err
                    )
                    _LOGGER.error(
                        "WRITE_OPERATION: Raw response that failed to parse: %s",
                        response_text[:500]
                    )
                    _LOGGER.error(
                        "WRITE_OPERATION: Response content-type: %s, status: %d",
                        resp.headers.get("Content-Type", "unknown"), resp.status
                    )
                    return False

            # Handle errors with improved diagnostics
            if resp.status == 401:
                _LOGGER.error(
                    "WRITE_OPERATION: Authentication failed for write to register %s", id
                )
                _LOGGER.error(
                    "WRITE_OPERATION: Current auth state - nonce: %s, realm: %s, last_auth: %s",
                    self._auth_nonce is not None,
                    self._auth_realm,
                    time.time() - self._last_auth_time if self._last_auth_time > 0 else "never"
                )
                raise SVKAuthenticationError(
                    "Invalid username or password for write operation"
                )

            # For other HTTP errors, capture full response details
            response_text = await resp.text(errors="ignore")
            _LOGGER.error(
                "WRITE_OPERATION: HTTP error %d for register %s", resp.status, id
            )
            _LOGGER.error(
                "WRITE_OPERATION: Response headers: %s", dict(resp.headers)
            )
            _LOGGER.error(
                "WRITE_OPERATION: Response body (first 300 chars): %s",
                response_text[:300]
            )
            
            raise SVKConnectionError(f"HTTP {resp.status}: {response_text[:160]}")

        except SVKWriteError:
            # Re-raise SVKWriteError without wrapping
            raise
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            request_time = time.time() - start_time
            _LOGGER.error(
                "WRITE_OPERATION: Network error after %.2f seconds for register %s: %s",
                request_time, id, err
            )
            _LOGGER.error(
                "WRITE_OPERATION: Write value was: %s", value
            )
            return False
        except Exception as err:
            request_time = time.time() - start_time
            _LOGGER.error(
                "WRITE_OPERATION: Unexpected error after %.2f seconds for register %s: %s",
                request_time, id, err
            )
            _LOGGER.error(
                "WRITE_OPERATION: Exception type: %s", type(err).__name__
            )
            return False
        finally:
            if resp:
                resp.release()

    async def test_connection(self) -> bool:
        """
        Test basic connectivity to the heat pump.

        Returns:
            True if connection test succeeds, False otherwise
        """
        try:
            _LOGGER.info("Testing connection to heat pump at %s", self.host)

            # Try a minimal request with just one essential ID
            test_ids = [253]  # display_input_theatsupply - essential sensor

            # Start session if needed
            if not self._session:
                await self.start()

            # Try GET request
            try:
                result = await self._request_with_get_params(test_ids)
                if result and len(result) > 0:
                    _LOGGER.info("Connection test successful")
                    return True
            except Exception as err:
                _LOGGER.error("Connection test failed: %s", err)

            return False

        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

    def set_default_ids(self, ids: list[int]) -> None:
        """
        Set the default ID list for requests.

        Args:
            ids: List of register IDs to use as default
        """
        self._default_ids = ids
        _LOGGER.info("Updated default ID list with %d IDs", len(ids))
