"""Constants for SVK Heatpump integration."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, Union

import aiofiles
import voluptuous as vol
import yaml
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant

DOMAIN = "svk_heatpump"
LOGGER = logging.getLogger(__package__)

# Configuration keys
CONF_WRITE_ACCESS = "write_access"
CONF_FETCH_INTERVAL = "fetch_interval"

# Default values
DEFAULT_WRITE_ACCESS = False
DEFAULT_FETCH_INTERVAL = 30

# API endpoints
ENDPOINT_READ = "/cgi-bin/json_values.cgi"
ENDPOINT_WRITE = "/cgi-bin/rdb_edit.cgi"

# Service names
SERVICE_SET_VALUE = "set_value"
SERVICE_REFRESH_ENTITIES = "refresh_entities"

# Platform definitions
PLATFORMS = [Platform.SENSOR]

# Catalog file path
CATALOG_FILE_PATH = Path(__file__).parent / "catalog.yaml"

# Configuration schema
CONFIG_SCHEMA = {
    vol.Required(CONF_HOST): str,
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_WRITE_ACCESS, default=DEFAULT_WRITE_ACCESS): bool,
    vol.Optional(CONF_FETCH_INTERVAL, default=DEFAULT_FETCH_INTERVAL): int,
}


class ValueMap(TypedDict, total=False):
    """Type definition for value mapping."""
    type: str
    mapping: Dict[str, str]


@dataclass
class CatalogEntity:
    """Represents a single entity in the catalog."""
    id: str
    key: str
    enabled: bool
    platform: str
    device_class: str
    unit_of_measurement: str
    state_class: str
    icon: str
    precision: int = 0
    value_map: Optional[Dict[str, str]] = None
    translation_key: Optional[str] = None
    write_access: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogEntity":
        """Create a CatalogEntity from a dictionary."""
        return cls(
            id=str(data["id"]),
            key=data["key"],
            enabled=bool(data["enabled"]),
            platform=data["platform"],
            device_class=data.get("device_class", ""),
            unit_of_measurement=data.get("unit_of_measurement", ""),
            state_class=data.get("state_class", ""),
            icon=data.get("icon", ""),
            precision=int(data.get("precision", 0)),
            value_map=data.get("value_map"),
            translation_key=data.get("translation_key"),
            write_access=bool(data.get("write_access", False)),
        )


@dataclass
class Catalog:
    """Represents the complete catalog of entities."""
    sensors: List[CatalogEntity] = field(default_factory=list)

    def get_enabled_entities(self) -> List[CatalogEntity]:
        """Get all enabled entities from the catalog."""
        return [entity for entity in self.sensors if entity.enabled]

    def get_all_entities(self) -> List[CatalogEntity]:
        """Get all entities from the catalog regardless of enabled status."""
        return self.sensors

    def get_fetchable_entities(self) -> List[CatalogEntity]:
        """Get entities that should be actively fetched (both catalog-enabled and user-enabled).
        
        Returns entities that have enabled=True in the catalog, as these are the ones
        that should be polled from the heat pump API.
        """
        return [entity for entity in self.sensors if entity.enabled]

    def get_entity_by_id(self, entity_id: str) -> Optional[CatalogEntity]:
        """Find an entity by its ID."""
        for entity in self.sensors:
            if entity.id == entity_id:
                return entity
        return None

    def get_entity_by_key(self, key: str) -> Optional[CatalogEntity]:
        """Find an entity by its key."""
        for entity in self.sensors:
            if entity.key == key:
                return entity
        return None

    def get_writable_entities(self) -> List[CatalogEntity]:
        """Get all entities that support write operations."""
        return [entity for entity in self.sensors if entity.write_access and entity.enabled]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Catalog":
        """Create a Catalog from a dictionary."""
        catalog = cls()
        
        # Parse sensors
        if "sensors" in data:
            for sensor_data in data["sensors"]:
                entity = CatalogEntity.from_dict(sensor_data)
                catalog.sensors.append(entity)
        
        return catalog


async def async_load_catalog() -> Catalog:
    """Load the catalog from the YAML file asynchronously.
    
    Returns:
        Catalog: The loaded catalog.
        
    Raises:
        FileNotFoundError: If the catalog file is not found.
        yaml.YAMLError: If the catalog file cannot be parsed.
    """
    try:
        async with aiofiles.open(CATALOG_FILE_PATH, "r", encoding="utf-8") as file:
            content = await file.read()
            data = yaml.safe_load(content)
            if not data:
                LOGGER.error("Catalog file is empty")
                return Catalog()
            
            return Catalog.from_dict(data)
    except FileNotFoundError:
        LOGGER.error("Catalog file not found at %s", CATALOG_FILE_PATH)
        raise
    except yaml.YAMLError as error:
        LOGGER.error("Error parsing catalog file: %s", error)
        raise


async def load_catalog(hass: Optional[HomeAssistant] = None) -> Catalog:
    """Load the catalog from the YAML file asynchronously.
    
    Args:
        hass: Optional HomeAssistant instance (kept for compatibility).
        
    Returns:
        Catalog: The loaded catalog.
        
    Raises:
        FileNotFoundError: If the catalog file is not found.
        yaml.YAMLError: If the catalog file cannot be parsed.
    """
    return await async_load_catalog()


def transform_value(entity: CatalogEntity, raw_value: Union[str, int, float]) -> Any:
    """Transform a raw value according to the entity's configuration.
    
    Args:
        entity: The catalog entity defining the transformation.
        raw_value: The raw value from the heat pump.
        
    Returns:
        The transformed value.
    """
    # Convert to string for mapping
    str_value = str(raw_value)
    
    # Apply value mapping if defined
    if entity.value_map and str_value in entity.value_map:
        return entity.value_map[str_value]
    
    # Apply precision to numeric values
    if entity.precision > 0:
        try:
            numeric_value = float(raw_value)
            return round(numeric_value, entity.precision)
        except (ValueError, TypeError):
            # If conversion fails, return the original value
            pass
    
    # Return the original value if no transformation applies
    return raw_value


def get_unique_id(host: str, entity_id: str) -> str:
    """Generate a unique ID for an entity.
    
    Args:
        host: The heat pump host/IP.
        entity_id: The entity ID from the catalog.
        
    Returns:
        A unique ID in the format svk_heatpump-<host>-<entity_id>.
    """
    # Sanitize host to create a valid unique ID
    sanitized_host = host.replace(".", "_").replace(":", "_").replace("-", "_")
    return f"{DOMAIN}-{sanitized_host}-{entity_id}"


# Entity categories for better organization
class EntityCategory:
    """Entity category constants."""
    STATUS = "diagnostic"
    TEMPERATURE = "measurement"
    ENERGY = "measurement"
    CONTROL = "config"
    MAINTENANCE = "diagnostic"


# Default icons for different device classes
DEFAULT_ICONS = {
    "temperature": "mdi:thermometer",
    "humidity": "mdi:water-percent",
    "pressure": "mdi:gauge",
    "power": "mdi:flash",
    "energy": "mdi:lightning-bolt",
    "duration": "mdi:clock",
    "enum": "mdi:toggle-switch",
}