"""Test constants."""

from __future__ import annotations

from custom_components.vyloz_smeti.const import (
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
)

LOCATION_ID = 12345
LOCATION_NAME = "Bratislava"

MOCK_CONFIG_DATA = {
    CONF_LOCATION_ID: LOCATION_ID,
    CONF_LOCATION_NAME: LOCATION_NAME,
}
