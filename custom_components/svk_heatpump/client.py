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
        
        Always sends preemptive Basic Auth on the first request and on every redirect.
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
    
    def __init__(self, host: str, username: str = "", password: str = "", timeout: int = 10, allow_basic_auth: bool = False):
        """Initialize the JSON client."""
        self.host = host
        self._base = URL.build(scheme="http", host=host)
        self._username = username
        self._password = password
        self._allow_basic_auth = allow_basic_auth
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._chunk_size = 50  # Maximum number of IDs to request in one batch
        self._max_retries = 3  # Maximum number of retries for failed requests
        self._retry_delay = 1.0  # Initial retry delay in seconds
        self._digest_nonce = None  # Store nonce for subsequent requests
        self._digest_opaque = None  # Store opaque for subsequent requests
        self._digest_realm = None  # Store realm for subsequent requests
        self._digest_qop = "auth"  # Quality of protection
        self._digest_algorithm = "MD5"  # Hash algorithm
        self._digest_nc = 0  # Nonce count
        self._basic_auth = aiohttp.BasicAuth(username, password) if (username or password) else None
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
        
        assert self._session is not None
        url = self._base.with_path(path)
        
        # Prepare JSON payload
        payload = {"ids": ids}
        
        # For GET requests with query parameters
        query_params = f"ids={','.join(map(str, ids))}"
        get_url = self._base.with_path("/cgi-bin/json_values.cgi").with_query(query_params)
        
        for attempt in range(self._max_retries):
            try:
                # First, send an unauthenticated GET request
                _LOGGER.debug("Attempt %d: Making unauthenticated request to %s", attempt + 1, get_url)
                headers = {}
                resp = await self._session.get(get_url, headers=headers, allow_redirects=False)
                self._last_status_code = resp.status
                _LOGGER.debug("Response status: %d", resp.status)
                
                try:
                    # Handle 401 - Need authentication
                    if resp.status == 401:
                        auth_header = resp.headers.get('WWW-Authenticate', '')
                        _LOGGER.debug("Received WWW-Authenticate header: %s", auth_header)
                        if not auth_header.startswith('Digest '):
                            # Check if Basic Auth is allowed as fallback
                            if self._allow_basic_auth and auth_header.startswith('Basic '):
                                _LOGGER.debug("Falling back to Basic authentication as Digest is not supported")
                                # Retry with Basic Auth
                                if self._basic_auth:
                                    headers["Authorization"] = self._basic_auth.encode()
                                    resp = await self._session.get(get_url, headers=headers, allow_redirects=False)
                                    self._last_status_code = resp.status
                                else:
                                    raise SVKAuthenticationError("Server requires Basic authentication but no credentials provided")
                            else:
                                raise SVKAuthenticationError("Server does not support Digest authentication")
                        
                        # Parse WWW-Authenticate header
                        auth_params = _parse_www_authenticate(auth_header)
                        _LOGGER.debug("Parsed auth params: %s", auth_params)
                        
                        # Check for stale=true
                        is_stale = auth_params.get('stale', '').lower() == 'true'
                        if is_stale:
                            _LOGGER.debug("Server indicated stale nonce")
                        
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
                        uri = str(get_url.relative())
                        _LOGGER.debug("Digest auth URI: %s", uri)
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
                        _LOGGER.debug("Digest auth response status: %d", resp.status)
                        
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
                        # Parse JSON response
                        try:
                            data = await resp.json()
                            _LOGGER.debug("Received JSON data with %d items", len(data) if isinstance(data, list) else "unknown")
                            
                            # Check for empty or blank response
                            if not data:
                                raise SVKConnectionError("Empty response body")
                            
                            # Ensure we have a list of items
                            if not isinstance(data, list):
                                _LOGGER.warning("Unexpected response format: expected list, got %s", type(data))
                                # Convert to list if it's a dict (for backward compatibility)
                                if isinstance(data, dict):
                                    # Convert dict to list of items
                                    items = []
                                    for id_val, value in data.items():
                                        items.append({
                                            "id": str(id_val),
                                            "name": f"item_{id_val}",
                                            "value": str(value)
                                        })
                                    return items
                                else:
                                    raise SVKParseError("json", f"Expected list of items, got {type(data)}")
                            
                            return data
                        except (aiohttp.ContentTypeError, ValueError) as err:
                            # Try to get text response for debugging
                            text = await resp.text(errors="ignore")
                            if not text.strip():
                                raise SVKConnectionError("Blank response body") from err
                            raise SVKParseError("json", f"Invalid JSON response: {text[:100]}") from err
                    
                    # Handle other errors
                    if resp.status == 401:
                        raise SVKAuthenticationError("Invalid username or password")
                    
                    text = await resp.text(errors="ignore")
                    raise SVKConnectionError(f"HTTP {resp.status} {get_url}: {text[:160]}")
                
                finally:
                    resp.release()
            
            except asyncio.TimeoutError as err:
                if attempt < self._max_retries - 1:
                    # Exponential backoff
                    delay = self._retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise SVKTimeoutError(f"Timeout connecting to {self.host}") from err
            
            except aiohttp.ClientError as err:
                if attempt < self._max_retries - 1:
                    # Exponential backoff
                    delay = self._retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
                raise SVKConnectionError(f"Failed to fetch {path}: {err}") from err
        
        raise SVKConnectionError(f"Max retries exceeded for {path}")
    
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
            async with self._session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text(errors="ignore")
                    raise SVKConnectionError(f"HTTP {resp.status} {url}: {text[:160]}")
                
                # Parse JSON response
                try:
                    data = await resp.json()
                    
                    # Check for empty or blank response
                    if not data:
                        raise SVKConnectionError("Empty response body")
                    
                    # Ensure we have a list of items
                    if not isinstance(data, list):
                        _LOGGER.warning("Unexpected response format: expected list, got %s", type(data))
                        # Convert to list if it's a dict (for backward compatibility)
                        if isinstance(data, dict):
                            # Convert dict to list of items
                            items = []
                            for id_val, value in data.items():
                                items.append({
                                    "id": str(id_val),
                                    "name": f"item_{id_val}",
                                    "value": str(value)
                                })
                            return items
                        else:
                            raise SVKParseError("json", f"Expected list of items, got {type(data)}")
                    
                    return data
                except (aiohttp.ContentTypeError, ValueError) as err:
                    # Try to get text response for debugging
                    text = await resp.text(errors="ignore")
                    if not text.strip():
                        raise SVKConnectionError("Blank response body") from err
                    raise SVKParseError("json", f"Invalid JSON response: {text[:100]}") from err
        
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            raise SVKConnectionError(f"Failed to fetch {path}: {err}") from err
    
    async def read_values(self, ids: List[int]) -> List[Dict[str, Any]]:
        """
        Read values from the JSON API.
        
        Args:
            ids: Iterable of register IDs to read
            
        Returns:
            List of dictionaries with 'id', 'name', and 'value' fields
        """
        if not ids:
            return []
        
        # Convert to list if needed
        id_list = list(ids)
        
        # If the number of IDs is small, make a single request
        if len(id_list) <= self._chunk_size:
            return await self._request_with_retry("/cgi-bin/json_values.cgi", id_list)
        
        # For larger ID lists, split into chunks
        results = []
        for i in range(0, len(id_list), self._chunk_size):
            chunk = id_list[i:i + self._chunk_size]
            try:
                chunk_results = await self._request_with_retry("/cgi-bin/json_values.cgi", chunk)
                # Extend the results list with the new items
                if isinstance(chunk_results, list):
                    results.extend(chunk_results)
                else:
                    _LOGGER.warning("Unexpected response format for chunk %s-%s: expected list, got %s",
                                  i, i + len(chunk), type(chunk_results))
            except SVKConnectionError as err:
                _LOGGER.warning("Failed to read chunk %s-%s: %s", i, i + len(chunk), err)
                # Continue with other chunks even if one fails
        
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
                        # Check if Basic Auth is allowed as fallback
                        if self._allow_basic_auth and auth_header.startswith('Basic '):
                            _LOGGER.debug("Falling back to Basic authentication for write operation")
                            # Retry with Basic Auth
                            if self._basic_auth:
                                headers["Authorization"] = self._basic_auth.encode()
                                resp = await self._session.post(url, json=payload, headers=headers, allow_redirects=False)
                                self._last_status_code = resp.status
                            else:
                                raise SVKAuthenticationError("Server requires Basic authentication but no credentials provided")
                        else:
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