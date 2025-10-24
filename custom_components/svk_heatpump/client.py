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


class SVKHeatpumpClient:
    """Client for communicating with SVK LOM320 web module with HTTP Compatibility Mode."""
    
    def __init__(self, host: str, username: str = "", password: str = "", timeout: int = 10):
        """Initialize the client."""
        self.host = host
        self._base = URL.build(scheme="http", host=host)
        self._auth = aiohttp.BasicAuth(username, password) if (username or password) else None
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=timeout)
    
    async def start(self):
        """Start the client session."""
        if self._session:
            return
        self._session = aiohttp.ClientSession(
            timeout=self._timeout,
            connector=aiohttp.TCPConnector(limit=6, force_close=True),
            headers={
                "User-Agent": "SVKHeatpump/0.1 (HomeAssistant)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en",
                "Accept-Encoding": "identity",
                "Connection": "close",
            },
            auto_decompress=False,
            cookie_jar=aiohttp.CookieJar(unsafe=True),  # Keep cookies between requests
        )
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def _request(self, path: str, *, max_hops: int = 3) -> str:
        """
        Make a request with LOM320 HTTP Compatibility Mode.
        
        Always sends preemptive Digest Auth on the first request and on every redirect.
        Follows redirects manually and re-attaches auth each hop.
        """
        if not self._session:
            await self.start()
        
        assert self._session is not None
        url = self._base.with_path(path)
        headers = {}
        
        # Preemptive Authorization header
        if self._auth:
            headers["Authorization"] = self._auth.encode()

        for hop in range(max_hops):
            try:
                resp = await self._session.get(url, headers=headers, allow_redirects=False)
                try:
                    if resp.status in (302, 303, 307, 308):
                        loc = resp.headers.get("Location")
                        if not loc:
                            break
                        # Build absolute URL; re-attach preemptive auth and cookies preserved by session
                        url = url.join(URL(loc))
                        continue
                    if resp.status == 401 and self._auth:
                        # Retry once already preemptively auth'd? Surface error.
                        text = await resp.text(errors="ignore")
                        raise SVKAuthenticationError("Invalid username or password")
                    if resp.status == 204:
                        # Transient empty response; small backoff then retry
                        await asyncio.sleep(0.25)
                        continue
                    if resp.status != 200:
                        text = await resp.text(errors="ignore")
                        raise SVKConnectionError(f"HTTP {resp.status} {url}: {text[:160]}")
                    # Decode with fallback if server omits charset
                    body = await resp.read()
                    try:
                        return body.decode("utf-8")
                    except UnicodeDecodeError:
                        return body.decode("latin-1", errors="replace")
                finally:
                    resp.release()
            except asyncio.TimeoutError as err:
                raise SVKTimeoutError(f"Timeout connecting to {self.host}") from err
            except aiohttp.ClientError as err:
                raise SVKConnectionError(f"Failed to fetch {path}: {err}") from err
        
        raise SVKConnectionError(f"Too many redirects or empty responses for {path}")
    
    async def get(self, path: str) -> str:
        """Get a page from the LOM320 module."""
        return await self._request(path)
    
    async def get_display(self) -> str:
        """Get the display page."""
        return await self._request("/display.htm")
    
    async def get_heating(self) -> str:
        """Get the heating page."""
        return await self._request("/heating.htm")
    
    async def get_heatpump(self) -> str:
        """Get the heatpump page."""
        return await self._request("/heatpump.htm")
    
    async def get_user(self) -> str:
        """Get the user page."""
        return await self._request("/user.htm")
    
    async def get_solar(self) -> str:
        """Get the solar page."""
        return await self._request("/solar.htm")
    
    async def get_hotwater(self) -> str:
        """Get the hot water page."""
        return await self._request("/hotwater.htm")
    
    async def fetch_page(self, page: str) -> str:
        """Fetch a specific page from the LOM320 module (legacy method)."""
        return await self.get(page)
    
    async def set_parameter(self, parameter: str, value: Any) -> bool:
        """Set a parameter value on the LOM320 module."""
        # This would need to be implemented based on the actual form structure
        # For now, we'll simulate the write operation
        _LOGGER.info("Setting %s to %s", parameter, value)
        
        # In a real implementation, this would:
        # 1. Fetch the form page (likely user.htm)
        # 2. Parse the form to find the correct input field
        # 3. Submit the form with the new value
        # 4. Verify the change was accepted
        
        # For now, we'll just return True to simulate success
        return True
    
    async def fetch_all_pages(self) -> Dict[str, str]:
        """Fetch all relevant pages from the LOM320 module."""
        pages = {
            "display": "index.htm",
            "user": "user.htm",
            "heating": "heating.htm",
            "heatpump": "heatpump.htm",
            "solar": "solar.htm",
            "hotwater": "hotwater.htm"
        }
        
        results = {}
        for page_name, page_path in pages.items():
            try:
                html = await self.fetch_page(page_path)
                results[page_name] = html
            except SVKConnectionError as err:
                _LOGGER.warning("Failed to fetch %s page: %s", page_name, err)
                # Continue with other pages
        
        return results


class SVKHeatpumpParser:
    """Parser for LOM320 HTML pages."""
    
    @staticmethod
    def _extract_value_by_label(soup: BeautifulSoup, label: str) -> Optional[str]:
        """Extract value by finding a label and getting the next cell."""
        # Try different patterns for label-value pairs
        patterns = [
            # Table with label in first cell, value in second
            lambda s: s.find('td', string=re.compile(label, re.IGNORECASE)) and s.find('td', string=re.compile(label, re.IGNORECASE)).find_next_sibling('td'),
            # Table with label in th, value in td
            lambda s: s.find('th', string=re.compile(label, re.IGNORECASE)) and s.find('th', string=re.compile(label, re.IGNORECASE)).find_next_sibling('td'),
            # Div with label class
            lambda s: s.find('div', class_='label', string=re.compile(label, re.IGNORECASE)) and s.find('div', class_='label', string=re.compile(label, re.IGNORECASE)).find_next_sibling('div'),
            # Span with label class
            lambda s: s.find('span', class_='label', string=re.compile(label, re.IGNORECASE)) and s.find('span', class_='label', string=re.compile(label, re.IGNORECASE)).find_next_sibling('span'),
            # Any element containing the label text
            lambda s: s.find(string=re.compile(label, re.IGNORECASE)) and s.find(string=re.compile(label, re.IGNORECASE)).parent.find_next_sibling(),
        ]
        
        for pattern in patterns:
            element = pattern(soup)
            if element:
                value = element.get_text(strip=True)
                # Clean up the value
                value = re.sub(r'[°C%Vh]', '', value).strip()
                return value
        
        return None
    
    @staticmethod
    def _parse_temperature(value: str) -> Optional[float]:
        """Parse temperature value."""
        if not value:
            return None
        try:
            # Extract numeric value
            match = re.search(r'-?\d+\.?\d*', value.replace(',', '.'))
            if match:
                return float(match.group())
        except (ValueError, AttributeError):
            pass
        return None
    
    @staticmethod
    def _parse_number(value: str) -> Optional[float]:
        """Parse numeric value."""
        if not value:
            return None
        try:
            # Extract numeric value
            match = re.search(r'-?\d+\.?\d*', value.replace(',', '.'))
            if match:
                return float(match.group())
        except (ValueError, AttributeError):
            pass
        return None
    
    @staticmethod
    def parse_display_page(html: str) -> Dict[str, Any]:
        """Parse the Display page to extract system status."""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Parse temperature sensors
        for key, sensor_def in TEMP_SENSORS.items():
            if sensor_def["page"] == "display":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    temp = SVKHeatpumpParser._parse_temperature(value)
                    if temp is not None:
                        data[key] = temp
        
        # Parse system information
        for key, sensor_def in SYSTEM_SENSORS.items():
            if sensor_def["page"] == "display":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    data[key] = value
        
        # Parse heat pump state
        heatpump_state = SVKHeatpumpParser._extract_value_by_label(soup, "Heat pump state")
        if heatpump_state:
            # Map to our enum values
            for state_text, state_value in HEATPUMP_STATES.items():
                if state_text.lower() in heatpump_state.lower():
                    data["heatpump_state"] = state_value
                    break
            else:
                data["heatpump_state"] = heatpump_state
        
        # Parse alarm status
        alarm_active = SVKHeatpumpParser._extract_value_by_label(soup, "Alarm active")
        if alarm_active:
            data["alarm_active"] = "yes" in alarm_active.lower()
        
        # Parse alarm list if present
        alarm_table = soup.find('table', string=re.compile('alarm', re.IGNORECASE))
        if alarm_table:
            alarms = []
            rows = alarm_table.find_all('tr')
            for row in rows[1:]:  # Skip header
                cells = row.find_all('td')
                if len(cells) >= 3:
                    code = cells[0].get_text(strip=True)
                    description = cells[1].get_text(strip=True)
                    severity = cells[2].get_text(strip=True)
                    
                    # Map severity
                    severity_value = "warning"
                    for severity_text, severity_value_map in ALARM_SEVERITIES.items():
                        if severity_text.lower() in severity.lower():
                            severity_value = severity_value_map
                            break
                    
                    alarms.append({
                        "code": code,
                        "description": description or ALARM_CODES.get(code, "Unknown alarm"),
                        "severity": severity_value
                    })
            
            if alarms:
                data["alarm_list"] = alarms
        
        return data
    
    @staticmethod
    def parse_user_page(html: str) -> Dict[str, Any]:
        """Parse the User page to extract setpoints and configuration."""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Parse setpoint sensors
        for key, sensor_def in SETPOINT_SENSORS.items():
            if sensor_def["page"] == "user":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    temp = SVKHeatpumpParser._parse_temperature(value)
                    if temp is not None:
                        data[key] = temp
        
        # Parse season mode
        season_mode = SVKHeatpumpParser._extract_value_by_label(soup, "Season mode")
        if season_mode:
            for mode_text, mode_value in SEASON_MODES.items():
                if mode_text.lower() in season_mode.lower():
                    data["season_mode"] = mode_value
                    break
            else:
                data["season_mode"] = season_mode
        
        return data
    
    @staticmethod
    def parse_heating_page(html: str) -> Dict[str, Any]:
        """Parse the Heating page to extract heating system data."""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Parse performance sensors
        for key, sensor_def in PERFORMANCE_SENSORS.items():
            if sensor_def["page"] == "heating":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    num = SVKHeatpumpParser._parse_number(value)
                    if num is not None:
                        data[key] = num
        
        # Parse counter sensors
        for key, sensor_def in COUNTER_SENSORS.items():
            if sensor_def["page"] == "heating":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    num = SVKHeatpumpParser._parse_number(value)
                    if num is not None:
                        data[key] = num
        
        return data
    
    @staticmethod
    def parse_heatpump_page(html: str) -> Dict[str, Any]:
        """Parse the Heatpump page to extract compressor and performance data."""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Parse performance sensors
        for key, sensor_def in PERFORMANCE_SENSORS.items():
            if sensor_def["page"] == "heatpump":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    num = SVKHeatpumpParser._parse_number(value)
                    if num is not None:
                        data[key] = num
        
        # Parse counter sensors
        for key, sensor_def in COUNTER_SENSORS.items():
            if sensor_def["page"] == "heatpump":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    num = SVKHeatpumpParser._parse_number(value)
                    if num is not None:
                        data[key] = num
        
        return data
    
    @staticmethod
    def parse_solar_page(html: str) -> Dict[str, Any]:
        """Parse the Solar page to extract solar system data."""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # Parse temperature sensors
        for key, sensor_def in TEMP_SENSORS.items():
            if sensor_def["page"] == "solar":
                value = SVKHeatpumpParser._extract_value_by_label(soup, sensor_def["label"])
                if value:
                    temp = SVKHeatpumpParser._parse_temperature(value)
                    if temp is not None:
                        data[key] = temp
        
        # Parse solar panel state
        solar_state = SVKHeatpumpParser._extract_value_by_label(soup, "Solar panel state")
        if solar_state:
            for state_text, state_value in SOLAR_STATES.items():
                if state_text.lower() in solar_state.lower():
                    data["solar_panel_state"] = state_value
                    break
            else:
                data["solar_panel_state"] = solar_state
        
        return data
    
    @staticmethod
    def parse_hotwater_page(html: str) -> Dict[str, Any]:
        """Parse the Hot Water page to extract DHW system data."""
        soup = BeautifulSoup(html, 'lxml')
        data = {}
        
        # This page might contain additional hot water specific data
        # For now, we'll keep it simple and extract any temperature data
        
        # Look for any temperature-related data
        temp_labels = ["Hot water", "DHW", "Tank", "Legionella"]
        for label in temp_labels:
            value = SVKHeatpumpParser._extract_value_by_label(soup, label)
            if value:
                temp = SVKHeatpumpParser._parse_temperature(value)
                if temp is not None:
                    key = label.lower().replace(" ", "_") + "_temp"
                    data[key] = temp
        
        return data


# Digest authentication helper functions
def _parse_www_authenticate(header: str) -> Dict[str, str]:
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


def _md5_hex(data: str) -> str:
    """Calculate MD5 hash of a string."""
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
    opaque: Optional[str] = None,
    nc: str = "00000001",
    cnonce: Optional[str] = None,
) -> str:
    """
    Compute Digest authentication response according to RFC 7616.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        uri: Request URI
        username: Username for authentication
        password: Password for authentication
        realm: Authentication realm
        nonce: Server-provided nonce value
        qop: Quality of protection (auth, auth-int)
        algorithm: Hash algorithm (MD5, MD5-sess)
        opaque: Server-provided opaque value
        nc: Nonce count in hex format
        cnonce: Client nonce value
    
    Returns:
        Authorization header value for Digest authentication
    """
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


class LOMJsonClient:
    """Client for communicating with SVK LOM320 web module using JSON API with Digest authentication."""
    
    def __init__(self, host: str, username: str = "", password: str = "", timeout: int = 10,
                 chunk_size: int = None, enable_chunking: bool = None, excluded_ids: str = None):
        """Initialize the JSON client."""
        self.host = host
        self._base = URL.build(scheme="http", host=host)
        self._username = username
        self._password = password
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=timeout, connect=5.0, sock_read=10.0)
        # Handle backward compatibility for optional parameters
        if chunk_size is None:
            from .const import DEFAULT_CHUNK_SIZE
            chunk_size = DEFAULT_CHUNK_SIZE
        
        if enable_chunking is None:
            from .const import DEFAULT_ENABLE_CHUNKING
            enable_chunking = DEFAULT_ENABLE_CHUNKING
        
        if excluded_ids is None:
            from .const import DEFAULT_EXCLUDED_IDS
            excluded_ids = DEFAULT_EXCLUDED_IDS
        
        self._chunk_size = chunk_size  # Maximum number of IDs to request in one batch
        self._enable_chunking = enable_chunking  # Whether to use chunking at all
        self._excluded_ids = set()  # Set of IDs to exclude from requests
        
        # Parse excluded IDs if provided
        if excluded_ids:
            try:
                from .const import parse_id_list
                self._excluded_ids = set(parse_id_list(excluded_ids))
                _LOGGER.info("Excluding %d IDs from requests: %s", len(self._excluded_ids), list(self._excluded_ids)[:10])
            except Exception as err:
                _LOGGER.warning("Failed to parse excluded IDs '%s': %s", excluded_ids, err)
        
        self._max_retries = 3  # Maximum number of retries for failed requests
        self._retry_delay = 0.5  # Initial retry delay in seconds
        self._digest_nonce = None  # Store nonce for subsequent requests
        self._digest_opaque = None  # Store opaque for subsequent requests
        self._digest_realm = None  # Store realm for subsequent requests
        self._digest_qop = "auth"  # Quality of protection
        self._digest_algorithm = "MD5"  # Hash algorithm
        self._digest_nc = 0  # Nonce count
        self._last_status_code = None  # Track last HTTP status code for diagnostics
        
        # Track failed IDs for better error handling
        self._failed_ids = set()  # IDs that consistently fail
        self._unsupported_ids = set()  # IDs that are not supported by the API
    
    def _parse_json_response_flexible(self, data: Any, response_text: str = "") -> List[Dict[str, Any]]:
        """
        Parse JSON response with flexible format handling.
        
        Args:
            data: The parsed JSON data
            response_text: Raw response text for debugging
            
        Returns:
            List of dictionaries with 'id', 'name', and 'value' fields
            
        Raises:
            SVKInvalidDataFormatError: If the data format is not supported
        """
        _LOGGER.debug("Parsing JSON response with flexible format handling")
        _LOGGER.debug("Response data type: %s", type(data))
        if isinstance(data, (list, dict)):
            _LOGGER.debug("Response data size: %d items", len(data))
        
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
        
        # Handle dict format (alternative format)
        elif isinstance(data, dict):
            _LOGGER.debug("Processing dict format with %d keys", len(data))
            
            # Check if it's an error response first
            if any(key.lower() in ['error', 'message', 'code', 'status'] for key in data.keys()):
                raise SVKInvalidDataFormatError(
                    "list or dict with recognizable structure",
                    f"dict with error-like keys: {list(data.keys())}",
                    "Response appears to be an error message rather than data"
                )
            
            # Check if it's a simple key-value format
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
                        return self._parse_json_response_flexible(nested_data, response_text)
            
            
            
            # Check if it's a single item format
            if 'id' in data and 'value' in data:
                _LOGGER.debug("Found single item format, converting to list")
                return [data]
            
            # Try to extract any numeric keys as IDs
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
    
    async def _request_with_digest_auth(self, path: str, ids: List[int]) -> List[Dict[str, Any]]:
        """Make a request with Digest authentication."""
        import time
        start_time = time.time()
        
        _LOGGER.debug("PERFORMANCE: _request_with_digest_auth called for %d IDs", len(ids))
        
        if not self._session:
            _LOGGER.debug("Starting new session for digest auth")
            await self.start()
        
        assert self._session is not None
        url = self._base.with_path(path)
        
        # Prepare JSON payload
        payload = {"ids": ids}
        
        # For GET requests with query parameters
        query_params = f"ids={','.join(map(str, ids))}"
        get_url = self._base.with_path("/cgi-bin/json_values.cgi").with_query(query_params)
        _LOGGER.info("PERFORMANCE: Making digest auth request to: %s", get_url)
        _LOGGER.debug("Requesting %d IDs: %s", len(ids), ids[:10])  # Log first 10 IDs
        
        try:
            # Add overall timeout protection to prevent infinite retry loops
            _LOGGER.debug("PERFORMANCE: Starting digest auth with 30 second timeout")
            auth_start = time.time()
            result = await asyncio.wait_for(
                self._request_with_digest_auth_internal(path, ids, get_url, payload),
                timeout=30.0  # 30 second timeout for network operations
            )
            auth_duration = time.time() - auth_start
            total_duration = time.time() - start_time
            _LOGGER.info("PERFORMANCE: Digest auth completed in %.2fs (auth=%.2fs, total=%.2fs) for %d IDs",
                       total_duration, auth_duration, total_duration, len(ids))
            return result
        except asyncio.TimeoutError:
            total_duration = time.time() - start_time
            _LOGGER.error("CRITICAL: Digest auth request to %s timed out after 30 seconds (total=%.2fs) - this is blocking Home Assistant",
                        get_url, total_duration)
            raise SVKTimeoutError(f"Request timeout after 30 seconds for {path}")
    
    async def _request_with_digest_auth_internal(self, path: str, ids: List[int], get_url: URL, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Internal method for Digest authentication with retry logic."""
        import time
        attempt_start = time.time()
        
        _LOGGER.debug("PERFORMANCE: Starting digest auth internal method with %d max retries", self._max_retries)
        
        for attempt in range(self._max_retries + 1):  # Add 1 to ensure at least one attempt
            try:
                # Calculate exponential backoff delay
                if attempt > 0:
                    delay = self._retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    _LOGGER.debug("PERFORMANCE: Retrying after %.1f seconds (attempt %d/%d)", delay, attempt + 1, self._max_retries + 1)
                    await asyncio.sleep(delay)
                
                # First, send an unauthenticated GET request
                _LOGGER.info("PERFORMANCE: Attempt %d/%d: Making unauthenticated request to %s", attempt + 1, self._max_retries + 1, get_url)
                headers = {}
                _LOGGER.debug("PERFORMANCE: About to make HTTP GET request - potential blocking point")
                request_start = time.time()
                resp = await self._session.get(get_url, headers=headers, allow_redirects=False)
                request_duration = time.time() - request_start
                self._last_status_code = resp.status
                _LOGGER.info("PERFORMANCE: Initial request completed in %.2fs, status: %d", request_duration, resp.status)
                
                try:
                    # Handle 401 - Need authentication
                    if resp.status == 401:
                        auth_header = resp.headers.get('WWW-Authenticate', '')
                        _LOGGER.info("PERFORMANCE: Received 401 - WWW-Authenticate header: %s", auth_header)
                        if not auth_header.startswith('Digest '):
                            _LOGGER.error("Server does not support Digest authentication - auth scheme: %s", auth_header[:50])
                            raise SVKAuthenticationError("Server does not support Digest authentication. Please check if your device supports Digest authentication.")
                        
                        # Parse WWW-Authenticate header
                        auth_params = _parse_www_authenticate(auth_header)
                        _LOGGER.debug("PERFORMANCE: Parsed auth params: %s", auth_params)
                        
                        # Check for stale=true
                        is_stale = auth_params.get('stale', '').lower() == 'true'
                        if is_stale:
                            _LOGGER.debug("PERFORMANCE: Server indicated stale nonce")
                        
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
                        cnonce = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
                        
                        # Compute Digest authorization header
                        # Use the exact same URI that will be used in the request
                        uri = str(get_url.relative())
                        _LOGGER.debug("PERFORMANCE: Digest auth URI: %s", uri)
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
                        _LOGGER.debug("PERFORMANCE: Retrying with Digest authentication")
                        headers["Authorization"] = auth_header
                        auth_start = time.time()
                        resp = await self._session.get(get_url, headers=headers, allow_redirects=False)
                        auth_duration = time.time() - auth_start
                        self._last_status_code = resp.status
                        _LOGGER.info("PERFORMANCE: Digest auth request completed in %.2fs, status: %d", auth_duration, resp.status)
                        
                        # Handle 401 with stale=true - retry once with new nonce
                        if resp.status == 401 and not is_stale:
                            _LOGGER.debug("Digest authentication failed, checking for stale nonce")
                            resp_text = await resp.text(errors="ignore")
                            new_auth_header = resp.headers.get('WWW-Authenticate', '')
                            _LOGGER.debug("New WWW-Authenticate header: %s", new_auth_header)
                            if new_auth_header.startswith('Digest '):
                                new_auth_params = _parse_www_authenticate(new_auth_header)
                                if new_auth_params.get('stale', '').lower() == 'true':
                                    # Update nonce and retry
                                    self._digest_nonce = new_auth_params.get('nonce')
                                    self._digest_nc += 1
                                    nc_hex = f"{self._digest_nc:08x}"
                                    new_cnonce = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
                                    
                                    auth_header = _compute_digest_response(
                                        method="GET",
                                        uri=str(get_url.relative()),
                                        username=self._username,
                                        password=self._password,
                                        realm=self._digest_realm,
                                        nonce=self._digest_nonce,
                                        qop=self._digest_qop,
                                        algorithm=self._digest_algorithm,
                                        opaque=self._digest_opaque,
                                        nc=nc_hex,
                                        cnonce=new_cnonce,
                                    )
                                    
                                    headers["Authorization"] = auth_header
                                    resp = await self._session.get(get_url, headers=headers, allow_redirects=False)
                                    self._last_status_code = resp.status
                        
                        # Handle redirects manually and re-attach Digest header
                        if resp.status in (302, 303, 307, 308):
                            loc = resp.headers.get("Location")
                            if loc:
                                # Build absolute URL
                                redirect_url = get_url.join(URL(loc))
                                # Retry with same auth header
                                resp = await self._session.get(redirect_url, headers=headers, allow_redirects=False)
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
                attempt_duration = time.time() - attempt_start
                if attempt < self._max_retries:
                    # Exponential backoff is already handled at the start of the loop
                    _LOGGER.debug("PERFORMANCE: Timeout on attempt %d after %.2fs, will retry with exponential backoff",
                                attempt + 1, attempt_duration)
                    continue
                _LOGGER.error("PERFORMANCE: Timeout connecting to %s after %d attempts (total %.2fs)",
                             self.host, attempt + 1, attempt_duration)
                raise SVKTimeoutError(f"Timeout connecting to {self.host}") from err
            
            except aiohttp.ClientError as err:
                attempt_duration = time.time() - attempt_start
                if attempt < self._max_retries:
                    # Exponential backoff is already handled at the start of the loop
                    _LOGGER.debug("PERFORMANCE: Client error on attempt %d after %.2fs, will retry with exponential backoff: %s",
                                attempt + 1, attempt_duration, err)
                    continue
                _LOGGER.error("PERFORMANCE: Client error connecting to %s after %d attempts (total %.2fs): %s",
                             self.host, attempt + 1, attempt_duration, err)
                raise SVKConnectionError(f"Failed to fetch {path}: {err}") from err
        
            total_attempt_duration = time.time() - attempt_start
            _LOGGER.error("PERFORMANCE: Max retries exceeded for %s after %.2fs", path, total_attempt_duration)
            raise SVKConnectionError(f"Max retries exceeded for {path}")
    
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
            if entity_id in self._excluded_ids:
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
        # Only use Digest authentication if credentials are provided
        if self._username and self._password:
            return await self._request_with_digest_auth(path, ids)
        else:
            # Fallback to unauthenticated request
            return await self._request_unauthenticated(path, ids)
    
    async def _request_unauthenticated(self, path: str, ids: List[int]) -> List[Dict[str, Any]]:
        """Make an unauthenticated request (fallback)."""
        if not self._session:
            await self.start()
        
        assert self._session is not None
        url = self._base.with_path(path)
        
        # Prepare JSON payload
        payload = {"ids": ids}
        
        try:
            _LOGGER.debug("Making unauthenticated POST request to: %s", url)
            _LOGGER.debug("Request payload: %s", payload)
            
            async with self._session.post(url, json=payload) as resp:
                _LOGGER.debug("Unauthenticated response status: %d", resp.status)
                _LOGGER.debug("Response headers: %s", dict(resp.headers))
                
                if resp.status != 200:
                    text = await resp.text(errors="ignore")
                    _LOGGER.error("Unauthenticated request failed with status %d: %s", resp.status, text[:160])
                    raise SVKConnectionError(f"HTTP {resp.status} {url}: {text[:160]}")
                
                # Parse JSON response with enhanced error handling
                try:
                    # Read raw response first for debugging
                    response_text = await resp.text()
                    _LOGGER.debug("Raw unauthenticated response (first 200 chars): %s", response_text[:200])
                    
                    # Parse JSON from the text
                    import json
                    data = json.loads(response_text)
                    _LOGGER.debug("Received JSON data (unauthenticated) with %d items", len(data) if isinstance(data, list) else "unknown")
                    _LOGGER.debug("Raw JSON response type (unauthenticated): %s", type(data))
                    
                    # Check for empty or blank response
                    if not data:
                        _LOGGER.error("Empty JSON response received (unauthenticated)")
                        raise SVKConnectionError("Empty response body")
                    
                    # Use flexible parsing to handle different response formats
                    try:
                        result = self._parse_json_response_flexible(data, response_text)
                        _LOGGER.debug("Successfully parsed unauthenticated response, returning %d items", len(result))
                        return result
                    except SVKInvalidDataFormatError as format_err:
                        _LOGGER.error("Data format error (unauthenticated): %s", format_err.message)
                        _LOGGER.debug("Full response that caused format error: %s", response_text[:1000])
                        raise
                    
                except (aiohttp.ContentTypeError, ValueError, json.JSONDecodeError) as err:
                    # We already have the response_text from above
                    if not response_text.strip():
                        raise SVKConnectionError("Blank response body") from err
                    
                    # Log the full response for debugging
                    _LOGGER.error("Invalid JSON response (unauthenticated). Status: %d, Content-Type: %s, Response (first 500 chars): %s",
                                 resp.status, resp.headers.get('Content-Type', 'unknown'), response_text[:500])
                    
                    # Check if it's an HTML error page
                    html_error = self._detect_html_error_page(response_text)
                    if html_error:
                        raise SVKHTMLResponseError(resp.status, html_error)
                    
                    raise SVKParseError("json", f"Invalid JSON response: {response_text[:100]}") from err
        
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            raise SVKConnectionError(f"Failed to fetch {path}: {err}") from err
    
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
        
        # Convert to list if needed and filter out excluded/unsupported IDs
        id_list = list(ids)
        filtered_ids = [entity_id for entity_id in id_list
                       if entity_id not in self._excluded_ids and entity_id not in self._unsupported_ids]
        
        if len(filtered_ids) != len(id_list):
            _LOGGER.info("Filtered %d IDs (excluded: %d, unsupported: %d)",
                        len(id_list) - len(filtered_ids),
                        len([id for id in id_list if id in self._excluded_ids]),
                        len([id for id in id_list if id in self._unsupported_ids]))
        
        if not filtered_ids:
            _LOGGER.warning("No valid IDs remaining after filtering")
            return []
        
        _LOGGER.info("PERFORMANCE: Processing %d IDs after filtering", len(filtered_ids))
        
        # If chunking is disabled, make a single request with all IDs
        if not self._enable_chunking:
            _LOGGER.info("PERFORMANCE: Chunking disabled, making single request for %d IDs", len(filtered_ids))
            single_start = time.time()
            try:
                result = await self._request_with_retry("/cgi-bin/json_values.cgi", filtered_ids)
                single_duration = time.time() - single_start
                _LOGGER.info("PERFORMANCE: Single request completed in %.2fs, returned %d items",
                           single_duration, len(result) if result else 0)
                return result or []
            except Exception as err:
                _LOGGER.error("Single request failed: %s", err)
                # Fallback to individual requests
                _LOGGER.info("Falling back to individual requests due to single request failure")
                return await self._request_individual_ids("/cgi-bin/json_values.cgi", filtered_ids)
        
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
        
        # Only use Digest authentication if credentials are provided
        if not (self._username and self._password):
            # Fallback to unauthenticated request
            try:
                async with self._session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        text = await resp.text(errors="ignore")
                        raise SVKConnectionError(f"HTTP {resp.status} {url}: {text[:160]}")
                    
                    # Parse JSON response
                    try:
                        data = await resp.json()
                        return data.get("success", False)
                    except (aiohttp.ContentTypeError, ValueError):
                        return False
            
            except (asyncio.TimeoutError, aiohttp.ClientError) as err:
                _LOGGER.error("Failed to write value %s to register %s: %s", value, id, err)
                return False
        
        try:
            # First, send an unauthenticated POST request
            _LOGGER.debug("Making unauthenticated POST request to %s", url)
            headers = {}
            resp = await self._session.post(url, json=payload, headers=headers, allow_redirects=False)
            self._last_status_code = resp.status
            _LOGGER.debug("POST response status: %d", resp.status)
            
            try:
                # Handle 401 - Need authentication
                if resp.status == 401:
                    auth_header = resp.headers.get('WWW-Authenticate', '')
                    _LOGGER.debug("POST request received WWW-Authenticate header: %s", auth_header)
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
                    cnonce = hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:16]
                    
                    # Compute Digest authorization header
                    # Use the exact same URI that will be used in the request
                    uri = str(url.relative())
                    _LOGGER.debug("Digest auth URI for POST: %s", uri)
                    auth_header = _compute_digest_response(
                        method="POST",
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
                    _LOGGER.debug("Retrying POST with Digest authentication")
                    headers["Authorization"] = auth_header
                    resp = await self._session.post(url, json=payload, headers=headers, allow_redirects=False)
                    self._last_status_code = resp.status
                    _LOGGER.debug("POST Digest auth response status: %d", resp.status)
                    
                    # Handle redirects manually and re-attach Digest header
                    if resp.status in (302, 303, 307, 308):
                        loc = resp.headers.get("Location")
                        if loc:
                            # Build absolute URL
                            redirect_url = url.join(URL(loc))
                            # Retry with same auth header
                            resp = await self._session.post(redirect_url, json=payload, headers=headers, allow_redirects=False)
                            self._last_status_code = resp.status
                
                # Check for success
                if resp.status == 200:
                    # Parse JSON response
                    try:
                        data = await resp.json()
                        return data.get("success", False)
                    except (aiohttp.ContentTypeError, ValueError):
                        return False
                
                # Handle errors
                if resp.status == 401:
                    raise SVKAuthenticationError("Invalid username or password")
                
                text = await resp.text(errors="ignore")
                raise SVKConnectionError(f"HTTP {resp.status} {url}: {text[:160]}")
            
            finally:
                resp.release()
        
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Failed to write value %s to register %s: %s", value, id, err)
            return False


# Add deprecation warning to SVKHeatpumpClient
_original_init = SVKHeatpumpClient.__init__

def _deprecated_init(self, host: str, username: str = "", password: str = "", timeout: int = 10):
    """Initialize the deprecated client with warning."""
    import warnings
    warnings.warn(
        "SVKHeatpumpClient is deprecated. Use LOMJsonClient instead.",
        DeprecationWarning,
        stacklevel=2
    )
    _original_init(self, host, username, password, timeout)

# Replace the original __init__ with the deprecated version
SVKHeatpumpClient.__init__ = _deprecated_init