"""Constants for the Vyloz Smeti integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "vyloz_smeti"
PLATFORMS: Final = [Platform.CALENDAR]

MANUFACTURER: Final = "FCC"
MODEL: Final = "Waste Collection Schedule"
ATTRIBUTION: Final = "Data provided by FCC Vyloz Smeti (vylozsmeti.kabernet.sk)"

CONF_LOCATION_ID: Final = "location_id"
CONF_LOCATION_NAME: Final = "location_name"
CONF_UPDATE_INTERVAL: Final = "update_interval"

API_BASE_URL: Final = "https://vylozsmeti.kabernet.sk/api/public"
API_OPTIONS_URL: Final = f"{API_BASE_URL}/schedule/options"
API_SCHEDULE_URL: Final = f"{API_BASE_URL}/schedule"
API_LOCATIONS_URL: Final = f"{API_BASE_URL}/location?includeLocations=True"

API_TIMEOUT_SECONDS: Final = 10

DEFAULT_UPDATE_INTERVAL_HOURS: Final = 6
MIN_UPDATE_INTERVAL_HOURS: Final = 1
MAX_UPDATE_INTERVAL_HOURS: Final = 24
