"""Tests for the VylozSmetiCoordinator."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.vyloz_smeti.api import (
    VylozSmetiClient,
    VylozSmetiConnectionError,
)
from custom_components.vyloz_smeti.const import (
    API_OPTIONS_URL,
    API_SCHEDULE_URL,
    CONF_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL_HOURS,
)
from custom_components.vyloz_smeti.coordinator import VylozSmetiCoordinator
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .conftest import CURRENT_YEAR


@pytest.mark.usefixtures("mock_api")
async def test_update_merges_two_years(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    schedule_2026_payload: list[dict[str, Any]],
    schedule_2027_payload: list[dict[str, Any]],
) -> None:
    """Coordinator merges current and next year schedules into one list."""
    mock_config_entry.add_to_hass(hass)
    client = VylozSmetiClient(async_get_clientsession(hass))

    fake_now = datetime(CURRENT_YEAR, 6, 1, 12, 0, tzinfo=dt_util.UTC)
    with patch(
        "custom_components.vyloz_smeti.coordinator.dt_util.now", return_value=fake_now
    ):
        coordinator = VylozSmetiCoordinator(hass, mock_config_entry, client)
        data = await coordinator._async_update_data()

    expected_count = len(schedule_2026_payload) + len(schedule_2027_payload)
    assert len(data.schedule) == expected_count

    dates = {ev.date for ev in data.schedule}
    # at least one entry from each year survived the merge
    assert any(d.startswith(f"{CURRENT_YEAR}-") for d in dates)
    assert any(d.startswith(f"{CURRENT_YEAR + 1}-") for d in dates)
    assert data.waste_types[1] == "Zmesový odpad"


async def test_update_failed_on_response_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    options_payload: dict[str, Any],
) -> None:
    """An HTTP 5xx during refresh is wrapped as UpdateFailed."""
    aioclient_mock.get(API_OPTIONS_URL, json=options_payload)
    aioclient_mock.get(API_SCHEDULE_URL, status=500)
    mock_config_entry.add_to_hass(hass)

    client = VylozSmetiClient(async_get_clientsession(hass))
    coordinator = VylozSmetiCoordinator(hass, mock_config_entry, client)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_update_failed_propagates_client_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A direct VylozSmetiError from the client surfaces as UpdateFailed."""
    mock_config_entry.add_to_hass(hass)
    client = VylozSmetiClient(async_get_clientsession(hass))
    client.async_get_waste_types = AsyncMock(  # type: ignore[method-assign]
        side_effect=VylozSmetiConnectionError("boom")
    )
    coordinator = VylozSmetiCoordinator(hass, mock_config_entry, client)

    with pytest.raises(UpdateFailed, match="boom"):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    ("stored", "expected_hours"),
    [(0, 1), (-5, 1), (1000, MAX_UPDATE_INTERVAL_HOURS), (12, 12)],
)
async def test_update_interval_clamped(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    stored: int,
    expected_hours: int,
) -> None:
    """Out-of-range intervals stored in options are clamped to the safe band."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_UPDATE_INTERVAL: stored}
    )
    client = VylozSmetiClient(async_get_clientsession(hass))
    coordinator = VylozSmetiCoordinator(hass, mock_config_entry, client)
    assert coordinator.update_interval == timedelta(hours=expected_hours)
