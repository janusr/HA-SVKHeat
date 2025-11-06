"""API client for SVK Heatpump integration."""

import asyncio
import ipaddress
import json
import logging
import re
import ssl
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Union

import httpx
from homeassistant.exceptions import HomeAssistantError

from .const import ENDPOINT_READ, ENDPOINT_WRITE, LOGGER

# Custom exceptions for better error handling
class SVKConnectionError(HomeAssistantError):
    """Exception raised for connection errors."""

class SVKAuthenticationError(HomeAssistantError):
    """Exception raised for authentication errors."""

class SVKTimeoutError(HomeAssistantError):
    """Exception raised for timeout errors."""

class SVKInvalidResponseError(HomeAssistantError):
    """Exception raised for invalid response format."""

class SVKWriteAccessError(HomeAssistantError):
    """Exception raised when write access is denied."""


class SVKHeatpumpAPI:
    """Class to communicate with the SVK Heatpump."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        use_ssl: bool = False,
        timeout: float = 10.0,
        max_retries: int = 3,
        chunk_size: int = 25,
        api_mode: str = "json",
        request_timeout: int = 30,
    ) -> None:
        """Initialize the API client.
        
        Args:
            host: The heat pump host/IP address
            username: Username for authentication
            password: Password for authentication
            use_ssl: Whether to use HTTPS (default: False)
            timeout: Request timeout in seconds (default: 10.0)
            max_retries: Maximum number of retries (default: 3)
            chunk_size: Number of entities to request in a single batch (default: 25)
            api_mode: API mode to use (json or html) (default: "json")
            request_timeout: Request timeout in seconds (default: 30)
        """
        self.host = host
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self.api_mode = api_mode
        self.request_timeout = request_timeout
        
        # Build base URL with protocol
        protocol = "https" if use_ssl else "http"
        self.base_url = f"{protocol}://{host}"
        
        # Set up authentication
        self._auth = httpx.DigestAuth(username, password)
        
        # Determine if SSL verification should be used
        self._verify_ssl = self._should_verify_ssl(host)
        
        # Create persistent client
        self._client: Optional[httpx.AsyncClient] = None
        
        # Track connection state
        self._last_success_time = None
        self._consecutive_failures = 0
        self._client_initialized = False

    def _should_verify_ssl(self, host: str) -> bool:
        """Determine if SSL verification should be used based on host.
        
        Args:
            host: The host/IP address to connect to
            
        Returns:
            True if SSL verification should be used, False otherwise
        """
        try:
            # Try to parse as IP address
            ip = ipaddress.ip_address(host)
            
            # Check if it's a private/local IP address
            if isinstance(ip, ipaddress.IPv4Address):
                return not (ip.is_private or ip.is_loopback or ip.is_link_local)
            elif isinstance(ip, ipaddress.IPv6Address):
                return not (ip.is_private or ip.is_loopback or ip.is_link_local)
        except ValueError:
            # Not an IP address, treat as hostname
            # For hostnames, we'll verify SSL unless it's a common local hostname
            local_hostnames = [
                "localhost",
                "homeassistant.local",
                "hassio.local",
            ]
            return not any(host.lower().startswith(local_name) for local_name in local_hostnames)
        
        # Default to verifying SSL for safety
        return True

    def _create_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create an appropriate SSL context based on verification requirements.
        
        Returns:
            SSL context if SSL is enabled, None otherwise
        """
        if not self.use_ssl:
            return None
            
        if self._verify_ssl:
            # Create a default SSL context with verification
            # This will be called in a thread executor to avoid blocking
            return ssl.create_default_context()
        else:
            # Create unverified SSL context for local connections
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the persistent HTTP client.
        
        Returns:
            The configured AsyncClient instance
        """
        if not self._client_initialized or self._client is None:
            # Configure client with SSL settings
            client_config = {
                "auth": self._auth,
                "timeout": httpx.Timeout(self.timeout, connect=5.0),
                "follow_redirects": True,
                "headers": {
                    "User-Agent": "HomeAssistant-SVKHeatpump/1.0",
                    "Accept": "application/json, application/xml, text/plain",
                    "Connection": "keep-alive",
                },
            }
            
            # Add SSL configuration
            if self.use_ssl:
                # Always create an explicit SSL context in a thread executor to avoid blocking
                ssl_context = await asyncio.to_thread(self._create_ssl_context)
                if ssl_context:
                    client_config["verify"] = ssl_context
                else:
                    # This should not happen with our updated _create_ssl_context,
                    # but keep as a fallback
                    client_config["verify"] = False
            
            # Create the persistent client
            self._client = httpx.AsyncClient(**client_config)
            self._client_initialized = True
            
        return self._client

    async def async_close(self) -> None:
        """Close the HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._client_initialized = False

    async def async_read_values(self, ids: List[str]) -> Dict[str, Any]:
        """Read values from the heat pump.
        
        Args:
            ids: List of entity IDs to read
            
        Returns:
            Dictionary mapping entity IDs to their values
            
        Raises:
            SVKConnectionError: If connection fails
            SVKAuthenticationError: If authentication fails
            SVKTimeoutError: If request times out
            SVKInvalidResponseError: If response format is invalid
        """
        if not ids:
            LOGGER.warning("No entity IDs provided for reading")
            return {}
        
        url = f"{self.base_url}{ENDPOINT_READ}"
        params = {"ids": ";".join(ids)}
        
        LOGGER.debug("Reading values for %d entities: %s", len(ids), ids[:5])  # Log first 5 IDs
        LOGGER.debug("Using chunk_size=%d, api_mode=%s, request_timeout=%d",
                    self.chunk_size, self.api_mode, self.request_timeout)
        
        last_exception = None
        start_time = time.time()
        
        # Get the persistent client
        client = await self._get_client()
        
        for attempt in range(self.max_retries + 1):
            try:
                # Add jitter to avoid thundering herd
                if attempt > 0:
                    jitter = min(0.5, 0.1 * attempt)
                    await asyncio.sleep(2 ** attempt + jitter)
                
                LOGGER.debug("Attempting to read values (attempt %d/%d)", attempt + 1, self.max_retries + 1)
                response = await client.get(url, params=params)
                
                # Log response details for debugging
                LOGGER.debug(
                    "Response status: %d, content-type: %s, content-length: %d",
                    response.status_code,
                    response.headers.get("content-type", "unknown"),
                    len(response.content)
                )
                
                # Handle authentication errors
                if response.status_code == 401:
                    self._consecutive_failures += 1
                    raise SVKAuthenticationError("Authentication failed. Check credentials.")
                
                # Handle other HTTP errors
                response.raise_for_status()
                
                # Parse response based on content type
                result = await self._parse_response(response)
                
                # Reset failure counters on success
                self._consecutive_failures = 0
                self._last_success_time = time.time()
                
                LOGGER.debug("Successfully read %d values in %.2f seconds", len(result), time.time() - start_time)
                return result
                       
            except httpx.TimeoutException as ex:
                last_exception = SVKTimeoutError(f"Request timed out after {self.timeout} seconds")
                self._consecutive_failures += 1
                if attempt < self.max_retries:
                    LOGGER.warning(
                        "Timeout reading values, retrying... (attempt %d/%d): %s",
                        attempt + 1, self.max_retries + 1, ex
                    )
                    continue
                break
                    
            except httpx.ConnectError as ex:
                last_exception = SVKConnectionError(f"Connection failed: {ex}")
                self._consecutive_failures += 1
                if attempt < self.max_retries:
                    LOGGER.warning(
                        "Connection error, retrying... (attempt %d/%d): %s",
                        attempt + 1, self.max_retries + 1, ex
                    )
                    continue
                break
                    
            except httpx.HTTPStatusError as ex:
                self._consecutive_failures += 1
                if ex.response.status_code == 401:
                    last_exception = SVKAuthenticationError("Authentication failed. Check credentials.")
                elif ex.response.status_code == 403:
                    last_exception = SVKAuthenticationError("Access forbidden. Check permissions.")
                elif ex.response.status_code == 404:
                    last_exception = SVKConnectionError(f"Endpoint not found: {url}")
                elif ex.response.status_code >= 500:
                    last_exception = SVKConnectionError(f"Server error: {ex.response.status_code}")
                else:
                    last_exception = SVKConnectionError(f"HTTP error {ex.response.status_code}: {ex}")
                
                LOGGER.error(
                    "HTTP error during read: %s (status: %d, url: %s)",
                    ex, ex.response.status_code, url
                )
                break
                
            except (json.JSONDecodeError, ET.ParseError) as ex:
                last_exception = SVKInvalidResponseError(f"Invalid response format: {ex}")
                self._consecutive_failures += 1
                LOGGER.error("Response parsing error: %s", ex)
                break
                
            except Exception as ex:
                last_exception = SVKConnectionError(f"Unexpected error: {ex}")
                self._consecutive_failures += 1
                LOGGER.error("Unexpected error during read: %s", ex, exc_info=True)
                break
        
        # If we get here, all retries failed
        if last_exception:
            LOGGER.error(
                "Failed to read values after %d attempts in %.2f seconds: %s",
                self.max_retries + 1, time.time() - start_time, last_exception
            )
            raise last_exception
        else:
            raise SVKConnectionError("Failed to read values for unknown reason")

    async def async_write_value(self, itemno: str, value: Any, write_access_enabled: bool = False) -> bool:
        """Write a value to the heat pump.
        
        Args:
            itemno: The item number (entity ID) to write to
            value: The value to write
            write_access_enabled: Whether write access is enabled in configuration
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            SVKWriteAccessError: If write access is disabled
            SVKConnectionError: If connection fails
            SVKAuthenticationError: If authentication fails
            SVKTimeoutError: If request times out
        """
        # Check if write access is enabled
        if not write_access_enabled:
            raise SVKWriteAccessError("Write access is disabled in configuration")
        
        if not itemno:
            raise SVKWriteAccessError("Item number cannot be empty")
        
        url = f"{self.base_url}{ENDPOINT_WRITE}"
        params = {"itemno": itemno, "itemval": str(value)}
        
        LOGGER.debug("Writing value %s to item %s", value, itemno)
        
        last_exception = None
        start_time = time.time()
        
        # Get the persistent client
        client = await self._get_client()
        
        for attempt in range(self.max_retries + 1):
            try:
                # Add jitter to avoid thundering herd
                if attempt > 0:
                    jitter = min(0.5, 0.1 * attempt)
                    await asyncio.sleep(2 ** attempt + jitter)
                
                LOGGER.debug(
                    "Attempting to write value (attempt %d/%d): itemno=%s, value=%s",
                    attempt + 1, self.max_retries + 1, itemno, value
                )
                response = await client.get(url, params=params)
                
                # Log response details for debugging
                LOGGER.debug(
                    "Write response status: %d, content-type: %s, content-length: %d",
                    response.status_code,
                    response.headers.get("content-type", "unknown"),
                    len(response.content)
                )
                
                # Handle authentication errors
                if response.status_code == 401:
                    self._consecutive_failures += 1
                    raise SVKAuthenticationError("Authentication failed. Check credentials.")
                
                # Handle write permission errors
                if response.status_code == 403:
                    self._consecutive_failures += 1
                    raise SVKWriteAccessError("Write access denied. Check permissions.")
                
                # Check if operation was successful
                if response.status_code == 200:
                    # Try to parse response to confirm success
                    try:
                        if response.headers.get("content-type", "").startswith("application/json"):
                            result = response.json()
                            success = result.get("success", True)
                            if not success:
                                LOGGER.warning("Write operation returned success=false: %s", result)
                        else:
                            # For non-JSON responses, assume success if status is 200
                            success = True
                        
                        # Reset failure counters on success
                        self._consecutive_failures = 0
                        self._last_success_time = time.time()
                        
                        LOGGER.debug(
                            "Successfully wrote value %s to %s in %.2f seconds",
                            value, itemno, time.time() - start_time
                        )
                        return success
                    except (json.JSONDecodeError, KeyError) as ex:
                        # If we can't parse the response, assume success based on status code
                        LOGGER.debug("Could not parse write response, assuming success: %s", ex)
                        self._consecutive_failures = 0
                        self._last_success_time = time.time()
                        return True
                else:
                    response.raise_for_status()
                         
            except httpx.TimeoutException as ex:
                last_exception = SVKTimeoutError(f"Write request timed out after {self.timeout} seconds")
                self._consecutive_failures += 1
                if attempt < self.max_retries:
                    LOGGER.warning(
                        "Write timeout, retrying... (attempt %d/%d): %s",
                        attempt + 1, self.max_retries + 1, ex
                    )
                    continue
                break
                    
            except httpx.ConnectError as ex:
                last_exception = SVKConnectionError(f"Write connection failed: {ex}")
                self._consecutive_failures += 1
                if attempt < self.max_retries:
                    LOGGER.warning(
                        "Write connection error, retrying... (attempt %d/%d): %s",
                        attempt + 1, self.max_retries + 1, ex
                    )
                    continue
                break
                    
            except httpx.HTTPStatusError as ex:
                self._consecutive_failures += 1
                if ex.response.status_code == 401:
                    last_exception = SVKAuthenticationError("Authentication failed. Check credentials.")
                elif ex.response.status_code == 403:
                    last_exception = SVKWriteAccessError("Write access denied. Check permissions.")
                elif ex.response.status_code == 404:
                    last_exception = SVKConnectionError(f"Write endpoint not found: {url}")
                elif ex.response.status_code >= 500:
                    last_exception = SVKConnectionError(f"Server error during write: {ex.response.status_code}")
                else:
                    last_exception = SVKConnectionError(f"HTTP error {ex.response.status_code}: {ex}")
                
                LOGGER.error(
                    "HTTP error during write: %s (status: %d, url: %s)",
                    ex, ex.response.status_code, url
                )
                break
                
            except Exception as ex:
                last_exception = SVKConnectionError(f"Unexpected write error: {ex}")
                self._consecutive_failures += 1
                LOGGER.error("Unexpected error during write: %s", ex, exc_info=True)
                break
        
        # If we get here, all retries failed
        if last_exception:
            LOGGER.error(
                "Failed to write value %s to %s after %d attempts in %.2f seconds: %s",
                value, itemno, self.max_retries + 1, time.time() - start_time, last_exception
            )
            raise last_exception
        else:
            raise SVKConnectionError(f"Failed to write value {value} to {itemno} for unknown reason")

    async def async_test_connection(self) -> bool:
        """Test connection to the heat pump.
        
        Returns:
            True if connection is successful, False otherwise
            
        Raises:
            SVKConnectionError: If connection fails for reasons other than authentication
            SVKAuthenticationError: If authentication fails
            SVKTimeoutError: If request times out
        """
        LOGGER.debug("Testing connection to %s", self.base_url)
        start_time = time.time()
        
        try:
            # Try to read a basic value to test connection
            # Use a common entity ID that should exist on most systems
            result = await self.async_read_values(["1"])
            LOGGER.debug(
                "Connection test successful in %.2f seconds",
                time.time() - start_time
            )
            return True
        except SVKAuthenticationError:
            # Re-raise authentication errors
            LOGGER.debug("Connection test failed: authentication error")
            raise
        except (SVKConnectionError, SVKTimeoutError, SVKInvalidResponseError):
            # Re-raise connection and timeout errors
            LOGGER.debug(
                "Connection test failed in %.2f seconds: connection/timeout/response error",
                time.time() - start_time
            )
            raise
        except Exception as ex:
            # Convert any other exceptions to connection errors
            LOGGER.error(
                "Connection test failed with unexpected error in %.2f seconds: %s",
                time.time() - start_time, ex, exc_info=True
            )
            raise SVKConnectionError(f"Connection test failed: {ex}")

    async def _parse_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse the response based on content type.
        
        Args:
            response: The HTTP response object
            
        Returns:
            Dictionary mapping entity IDs to their values
            
        Raises:
            SVKInvalidResponseError: If response format is invalid
        """
        content_type = response.headers.get("content-type", "").lower()
        
        LOGGER.debug(
            "Parsing response with content-type: %s, length: %d",
            content_type, len(response.content)
        )
        
        try:
            # SVK heat pump returns JSON data as text/html, so we need to try JSON parsing first
            # regardless of the content type
            try:
                return self._parse_json_response(response)
            except (json.JSONDecodeError, SVKInvalidResponseError):
                # If JSON parsing fails, try other formats based on content type
                if "application/xml" in content_type or "text/xml" in content_type:
                    return self._parse_xml_response(response)
                else:
                    # Default to text parsing
                    return self._parse_text_response(response)
        except Exception as ex:
            LOGGER.error(
                "Failed to parse response (content-type: %s): %s",
                content_type, ex, exc_info=True
            )
            raise SVKInvalidResponseError(f"Failed to parse response: {ex}")

    def _parse_json_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse JSON response.
        
        Args:
            response: The HTTP response object
            
        Returns:
            Dictionary mapping entity IDs to their values
        """
        try:
            # SVK heat pump returns JSON data as text/html, so we need to parse the text
            # content_type might be text/html but contain valid JSON
            text_content = response.text
            
            # Check for malformed SVK JSON format: {obj},{obj},{obj} (missing array brackets)
            # This is a common issue with SVK heat pumps where they return comma-separated
            # JSON objects without the outer array brackets
            if text_content.strip().startswith('{') and not text_content.strip().startswith('['):
                # Check if it looks like comma-separated JSON objects
                if '},{ ' in text_content or '},{' in text_content:
                    # Pre-process by adding array brackets
                    LOGGER.debug("Detected malformed SVK JSON format, adding array brackets")
                    text_content = f'[{text_content}]'
            
            # Try to parse as JSON directly first
            try:
                data = response.json()
            except json.JSONDecodeError:
                # If that fails, try to parse the text content
                data = json.loads(text_content)
            
            # Handle different JSON response formats
            if isinstance(data, dict):
                # Format 1: {"id1": "value1", "id2": "value2", ...}
                if all(isinstance(k, str) for k in data.keys()):
                    LOGGER.debug("Parsed JSON response with %d key-value pairs", len(data))
                    return data
                
                # Format 2: {"values": [{"id": "id1", "value": "value1"}, ...]}
                elif "values" in data and isinstance(data["values"], list):
                    result = {}
                    for item in data["values"]:
                        if isinstance(item, dict) and "id" in item and "value" in item:
                            result[str(item["id"])] = item["value"]
                    LOGGER.debug("Parsed JSON response with %d values in list format", len(result))
                    return result
                    
            elif isinstance(data, list):
                # Format 3: SVK heat pump format: [{"id": "id1", "name": "name1", "value": "value1"}, ...]
                result = {}
                for item in data:
                    if isinstance(item, dict) and "id" in item and "value" in item:
                        result[str(item["id"])] = item["value"]
                LOGGER.debug("Successfully parsed SVK JSON response with %d values in array format", len(result))
                return result
                    
            # If we can't parse the format, return empty dict
            LOGGER.warning("Unexpected JSON response format: %s", data)
            return {}
        except json.JSONDecodeError as ex:
            LOGGER.error("JSON decode error: %s", ex)
            raise SVKInvalidResponseError(f"Invalid JSON response: {ex}")
        except Exception as ex:
            LOGGER.error("Error parsing JSON response: %s", ex)
            raise SVKInvalidResponseError(f"Error parsing JSON response: {ex}")

    def _parse_xml_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse XML response.
        
        Args:
            response: The HTTP response object
            
        Returns:
            Dictionary mapping entity IDs to their values
        """
        try:
            root = ET.fromstring(response.text)
            result = {}
            
            # Handle different XML response formats
            # Format 1: <values><value id="id1">value1</value><value id="id2">value2</value></values>
            for value_elem in root.findall(".//value"):
                if "id" in value_elem.attrib:
                    result[value_elem.attrib["id"]] = value_elem.text or ""
            
            # Format 2: <items><item id="id1"><val>value1</val></item></items>
            for item_elem in root.findall(".//item"):
                if "id" in item_elem.attrib:
                    val_elem = item_elem.find("val")
                    if val_elem is not None:
                        result[item_elem.attrib["id"]] = val_elem.text or ""
            
            LOGGER.debug("Parsed XML response with %d values", len(result))
            return result
        except ET.ParseError as ex:
            LOGGER.error("XML parse error: %s", ex)
            raise SVKInvalidResponseError(f"Invalid XML response: {ex}")
        except Exception as ex:
            LOGGER.error("Error parsing XML response: %s", ex)
            raise SVKInvalidResponseError(f"Error parsing XML response: {ex}")

    def _parse_text_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse plain text response.
        
        Args:
            response: The HTTP response object
            
        Returns:
            Dictionary mapping entity IDs to their values
        """
        try:
            text = response.text.strip()
            result = {}
            
            LOGGER.debug("Parsing text response: %s", text[:100])  # Log first 100 chars
            
            # Try different text formats
            # Format 1: id1=value1;id2=value2;...
            if "=" in text and ";" in text:
                for pair in text.split(";"):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        result[key.strip()] = value.strip()
            
            # Format 2: Line-by-line: id1 value1\nid2 value2\n...
            elif "\n" in text:
                for line in text.split("\n"):
                    line = line.strip()
                    if line and " " in line:
                        parts = line.split(" ", 1)
                        result[parts[0].strip()] = parts[1].strip()
            
            # Format 3: Single value (for single ID requests)
            elif text and not any(c in text for c in [";", "\n", "="]):
                # If we requested a single ID, return it with that ID
                # This is a fallback - the caller should handle this case
                pass
            
            LOGGER.debug("Parsed text response with %d values", len(result))
            return result
        except Exception as ex:
            LOGGER.error("Error parsing text response: %s", ex)
            raise SVKInvalidResponseError(f"Error parsing text response: {ex}")

    def transform_value(self, entity_config: Dict[str, Any], raw_value: Union[str, int, float]) -> Any:
        """Transform a raw value according to the entity's configuration.
        
        Args:
            entity_config: The entity configuration from the catalog
            raw_value: The raw value from the heat pump
            
        Returns:
            The transformed value
        """
        # Convert to string for mapping
        str_value = str(raw_value)
        
        # Apply value mapping if defined
        if "value_map" in entity_config and entity_config["value_map"]:
            value_map = entity_config["value_map"]
            if str_value in value_map:
                return value_map[str_value]
        
        # Apply precision to numeric values
        if "precision" in entity_config and entity_config["precision"] > 0:
            try:
                numeric_value = float(raw_value)
                return round(numeric_value, entity_config["precision"])
            except (ValueError, TypeError):
                # If conversion fails, return the original value
                pass
        
        # Return the original value if no transformation applies
        return raw_value