"""Calendar platform for the Vyloz Smeti integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from . import VylozSmetiConfigEntry
from .const import (
    ATTRIBUTION,
    CONF_LOCATION_NAME,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import VylozSmetiCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VylozSmetiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Vyloz Smeti calendar from a config entry."""
    async_add_entities([VylozSmetiCalendar(entry.runtime_data, entry)])


class VylozSmetiCalendar(CoordinatorEntity[VylozSmetiCoordinator], CalendarEntity):
    """Calendar entity exposing the upcoming waste collection events."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_translation_key = "schedule"
    _attr_icon = "mdi:trash-can"

    def __init__(
        self,
        coordinator: VylozSmetiCoordinator,
        entry: VylozSmetiConfigEntry,
    ) -> None:
        """Initialize the calendar entity."""
        super().__init__(coordinator)
        # Deterministic unique_id survives entry recreation; entry_id does not.
        self._attr_unique_id = f"{coordinator.location_id}_schedule"
        self._events: list[CalendarEvent] = []

        location_name = entry.data.get(CONF_LOCATION_NAME, entry.title)
        # Pin entity_id to vyloz_smeti_<location> for compatibility with the
        # legacy unofficial integration that some users may have run before.
        # has_entity_name=True forces suggested_object_id to None internally,
        # so we override entity_id directly for the initial registration.
        self.entity_id = f"calendar.{slugify(f'vyloz_smeti {location_name}')}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(coordinator.location_id))},
            name=location_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url="https://vylozsmeti.kabernet.sk/",
        )

    async def async_added_to_hass(self) -> None:
        """Build the initial event list when the entity is registered."""
        await super().async_added_to_hass()
        self._rebuild_events()

    def _rebuild_events(self) -> None:
        """Translate coordinator data into HA CalendarEvents."""
        data = self.coordinator.data
        if data is None:
            self._events = []
            return

        events: list[CalendarEvent] = []
        for waste_event in data.schedule:
            parsed = dt_util.parse_datetime(waste_event.date)
            if parsed is None:
                _LOGGER.warning(
                    "Skipping event with unparseable date: %s", waste_event.date
                )
                continue
            event_date = parsed.date()
            summary = data.waste_types.get(
                waste_event.waste_id, f"Unknown waste type ({waste_event.waste_id})"
            )
            events.append(
                CalendarEvent(
                    summary=summary,
                    start=event_date,
                    end=event_date + timedelta(days=1),
                )
            )
        events.sort(key=lambda ev: ev.start)
        self._events = events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming collection event."""
        today = dt_util.now().date()
        for ev in self._events:
            if ev.end > today:
                return ev
        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return events that overlap [start_date, end_date)."""
        start = start_date.date()
        end = end_date.date()
        return [ev for ev in self._events if ev.start < end and ev.end > start]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Rebuild the event list and push a state update."""
        self._rebuild_events()
        super()._handle_coordinator_update()
