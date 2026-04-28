"""HTTP client for the FCC Vyloz Smeti public API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp

from .const import (
    API_LOCATIONS_URL,
    API_OPTIONS_URL,
    API_SCHEDULE_URL,
    API_TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


class VylozSmetiError(Exception):
    """Base exception for the Vyloz Smeti API."""


class VylozSmetiConnectionError(VylozSmetiError):
    """Raised when the API cannot be reached."""


class VylozSmetiResponseError(VylozSmetiError):
    """Raised when the API returns an unexpected payload."""


@dataclass(frozen=True, slots=True)
class Location:
    """A municipality / collection point exposed by the API."""

    location_id: int
    city: str
    code: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Location | None:
        """Build a Location from a raw API dict, or return None if invalid."""
        location_id = payload.get("locationId")
        city = payload.get("city")
        code = payload.get("code")
        if location_id is None or not city or not code:
            return None
        return cls(location_id=int(location_id), city=str(city), code=str(code))


@dataclass(frozen=True, slots=True)
class WasteEvent:
    """A scheduled waste collection event for a given day."""

    waste_id: int
    date: str  # ISO-8601 string as returned by the API


class VylozSmetiClient:
    """Thin async wrapper around the three public Vyloz Smeti endpoints."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the client with a shared aiohttp session."""
        self._session = session

    async def async_get_locations(self) -> list[Location]:
        """Return all known municipalities."""
        payload = await self._request(API_LOCATIONS_URL)
        if not isinstance(payload, list):
            raise VylozSmetiResponseError(
                f"Locations endpoint returned {type(payload).__name__}, expected list"
            )
        locations: list[Location] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            loc = Location.from_payload(item)
            if loc is not None:
                locations.append(loc)
        return locations

    async def async_get_waste_types(self, location_id: int) -> dict[int, str]:
        """Return mapping of wasteId to human-readable title."""
        payload = await self._request(
            API_OPTIONS_URL, params={"locationId": location_id}
        )
        if not isinstance(payload, dict):
            raise VylozSmetiResponseError("Options endpoint did not return an object")
        wastes = payload.get("wastes", [])
        if not isinstance(wastes, list):
            raise VylozSmetiResponseError("'wastes' field is not a list")
        result: dict[int, str] = {}
        for item in wastes:
            if not isinstance(item, dict):
                continue
            waste_id = item.get("wasteId")
            title = item.get("title")
            if waste_id is None or not title:
                continue
            result[int(waste_id)] = str(title)
        return result

    async def async_get_schedule(self, location_id: int, year: int) -> list[WasteEvent]:
        """Return all collection events for a given location and year."""
        payload = await self._request(
            API_SCHEDULE_URL, params={"locationId": location_id, "year": year}
        )
        if not isinstance(payload, list):
            raise VylozSmetiResponseError("Schedule endpoint did not return a list")
        events: list[WasteEvent] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            waste_id = item.get("wasteId")
            date = item.get("date")
            if waste_id is None or not date:
                continue
            events.append(WasteEvent(waste_id=int(waste_id), date=str(date)))
        return events

    async def _request(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        """Issue a GET request with timeout and translate errors."""
        try:
            async with (
                asyncio.timeout(API_TIMEOUT_SECONDS),
                self._session.get(url, params=params) as response,
            ):
                response.raise_for_status()
                return await response.json()
        except TimeoutError as err:
            _LOGGER.debug("Timeout calling %s", url)
            raise VylozSmetiConnectionError(
                f"Timeout after {API_TIMEOUT_SECONDS}s while calling {url}"
            ) from err
        except aiohttp.ClientResponseError as err:
            _LOGGER.debug("HTTP %s from %s: %s", err.status, url, err.message)
            raise VylozSmetiResponseError(
                f"HTTP {err.status} {err.message} from {url}"
            ) from err
        except aiohttp.ClientError as err:
            _LOGGER.debug("Connection error calling %s: %s", url, err)
            raise VylozSmetiConnectionError(
                f"Connection error while calling {url}: {err}"
            ) from err
