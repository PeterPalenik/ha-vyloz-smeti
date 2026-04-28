"""DataUpdateCoordinator that pulls schedules from the FCC Vyloz Smeti API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import VylozSmetiClient, VylozSmetiError, WasteEvent
from .const import (
    CONF_LOCATION_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    MAX_UPDATE_INTERVAL_HOURS,
    MIN_UPDATE_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VylozSmetiData:
    """Snapshot of all data the coordinator exposes to platforms."""

    schedule: list[WasteEvent]
    waste_types: dict[int, str]


def _clamp_interval(raw: object) -> int:
    """Coerce a stored option to an integer hour count inside the valid band."""
    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = DEFAULT_UPDATE_INTERVAL_HOURS
    return max(MIN_UPDATE_INTERVAL_HOURS, min(MAX_UPDATE_INTERVAL_HOURS, value))


class VylozSmetiCoordinator(DataUpdateCoordinator[VylozSmetiData]):
    """Fetch schedule for the current and next year and merge them."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: VylozSmetiClient,
    ) -> None:
        """Initialize the coordinator."""
        stored_interval = config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_HOURS
        )
        update_hours = _clamp_interval(stored_interval)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=update_hours),
            config_entry=config_entry,
        )
        self._client = client
        self._location_id = int(config_entry.data[CONF_LOCATION_ID])

    @property
    def location_id(self) -> int:
        """Return the configured location id."""
        return self._location_id

    async def _async_update_data(self) -> VylozSmetiData:
        """Fetch waste types and the current+next year schedules in parallel."""
        current_year = dt_util.now().year
        try:
            waste_types, current, upcoming = await asyncio.gather(
                self._client.async_get_waste_types(self._location_id),
                self._client.async_get_schedule(self._location_id, current_year),
                self._client.async_get_schedule(self._location_id, current_year + 1),
            )
        except VylozSmetiError as err:
            raise UpdateFailed(str(err)) from err

        return VylozSmetiData(
            schedule=[*current, *upcoming],
            waste_types=waste_types,
        )
