"""Tests for the calendar entity."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.const import ATTR_FRIENDLY_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import CURRENT_YEAR
from .const import LOCATION_ID

EXPECTED_ENTITY_ID = "calendar.vyloz_smeti_bratislava"


def _patch_now(fake_now: datetime):
    """Patch dt_util.now in both modules that consult it."""
    return (
        patch(
            "custom_components.vyloz_smeti.calendar.dt_util.now", return_value=fake_now
        ),
        patch(
            "custom_components.vyloz_smeti.coordinator.dt_util.now",
            return_value=fake_now,
        ),
    )


@pytest.mark.usefixtures("mock_api")
async def test_entity_registered_with_expected_metadata(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The calendar entity is created with deterministic unique_id and device info."""
    mock_config_entry.add_to_hass(hass)

    fake_now = datetime(CURRENT_YEAR, 4, 14, 9, 0, tzinfo=dt_util.UTC)
    with _patch_now(fake_now)[0], _patch_now(fake_now)[1]:
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(EXPECTED_ENTITY_ID)
    assert state is not None
    assert state.attributes[ATTR_FRIENDLY_NAME] == "Bratislava Schedule"

    registry = er.async_get(hass)
    entry = registry.async_get(EXPECTED_ENTITY_ID)
    assert entry is not None
    # unique_id must NOT be the volatile entry_id
    assert entry.unique_id != mock_config_entry.entry_id
    assert entry.unique_id == f"{LOCATION_ID}_schedule"


@pytest.mark.usefixtures("mock_api")
async def test_event_property_returns_next_upcoming(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """`event` property returns the soonest event whose end is still in the future."""
    mock_config_entry.add_to_hass(hass)

    # Pin "now" to 2026-04-14, just before the first scheduled event 2026-04-15
    fake_now = datetime(CURRENT_YEAR, 4, 14, 9, 0, tzinfo=dt_util.UTC)
    with _patch_now(fake_now)[0], _patch_now(fake_now)[1]:
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get(EXPECTED_ENTITY_ID)
        assert state is not None
        assert state.attributes["start_time"].startswith(f"{CURRENT_YEAR}-04-15")
        assert state.attributes["message"] == "Zmesový odpad"


@pytest.mark.usefixtures("mock_api")
async def test_event_property_returns_event_in_progress(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """When today falls within an event's [start, end), that event is returned."""
    mock_config_entry.add_to_hass(hass)

    # Pin "now" to 2026-04-15 (the event itself runs 04-15 -> 04-16, half-open)
    fake_now = datetime(CURRENT_YEAR, 4, 15, 12, 0, tzinfo=dt_util.UTC)
    with _patch_now(fake_now)[0], _patch_now(fake_now)[1]:
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(EXPECTED_ENTITY_ID)
    assert state is not None
    assert state.attributes["start_time"].startswith(f"{CURRENT_YEAR}-04-15")


@pytest.mark.usefixtures("mock_api")
async def test_async_get_events_filters_range(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """async_get_events returns only events overlapping [start_date, end_date)."""
    mock_config_entry.add_to_hass(hass)
    fake_now = datetime(CURRENT_YEAR, 4, 14, 9, 0, tzinfo=dt_util.UTC)
    with _patch_now(fake_now)[0], _patch_now(fake_now)[1]:
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    response = await hass.services.async_call(
        CALENDAR_DOMAIN,
        "get_events",
        {
            "entity_id": EXPECTED_ENTITY_ID,
            "start_date_time": datetime(
                CURRENT_YEAR, 4, 1, tzinfo=dt_util.UTC
            ).isoformat(),
            "end_date_time": datetime(
                CURRENT_YEAR, 5, 1, tzinfo=dt_util.UTC
            ).isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    events = response[EXPECTED_ENTITY_ID]["events"]
    starts = {ev["start"] for ev in events}
    assert any(s.startswith(f"{CURRENT_YEAR}-04-15") for s in starts)
    assert any(s.startswith(f"{CURRENT_YEAR}-04-22") for s in starts)
    # 2026-05-01 is on the half-open boundary -> excluded
    assert not any(s.startswith(f"{CURRENT_YEAR}-05-01") for s in starts)
    # garbage date row was skipped without raising
    assert not any("garbage" in s for s in starts)


@pytest.mark.usefixtures("mock_api")
async def test_unparseable_date_is_skipped_not_raised(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    schedule_2026_payload: list[dict[str, Any]],
    schedule_2027_payload: list[dict[str, Any]],
) -> None:
    """A row with an unparseable date is skipped — entity stays available."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(EXPECTED_ENTITY_ID)
    assert state is not None
    assert state.state != "unavailable"

    response = await hass.services.async_call(
        CALENDAR_DOMAIN,
        "get_events",
        {
            "entity_id": EXPECTED_ENTITY_ID,
            "start_date_time": datetime(2025, 1, 1, tzinfo=dt_util.UTC).isoformat(),
            "end_date_time": datetime(2028, 1, 1, tzinfo=dt_util.UTC).isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    events = response[EXPECTED_ENTITY_ID]["events"]
    # 5 rows in 2026 fixture (one with bad date) + 2 in 2027 = 7, minus 1 dropped = 6
    parseable_total = len(schedule_2026_payload) + len(schedule_2027_payload) - 1
    assert len(events) == parseable_total


@pytest.mark.usefixtures("mock_api")
async def test_cache_invalidates_on_coordinator_update(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """When the coordinator pushes new data, the entity rebuilds its events."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data
    first_state = hass.states.get(EXPECTED_ENTITY_ID)
    assert first_state is not None

    # Mutate coordinator data and force a push update
    coordinator.data = type(coordinator.data)(schedule=[], waste_types={})
    coordinator.async_update_listeners()
    await hass.async_block_till_done()

    second_state = hass.states.get(EXPECTED_ENTITY_ID)
    assert second_state is not None
    # With no events left, calendar state is "off"
    assert second_state.state == "off"
