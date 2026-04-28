"""Tests for the integration setup / unload."""

from __future__ import annotations

from datetime import timedelta

import pytest
from custom_components.vyloz_smeti.const import API_LOCATIONS_URL, CONF_UPDATE_INTERVAL
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker


@pytest.mark.usefixtures("mock_api")
async def test_setup_and_unload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """A successful setup transitions the entry to LOADED, unload to NOT_LOADED."""
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data is not None

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retry_on_api_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """When the API is down at setup, the entry enters SETUP_RETRY."""
    aioclient_mock.get(API_LOCATIONS_URL, exc=TimeoutError)
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.usefixtures("mock_api")
async def test_options_change_triggers_reload(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Updating options triggers a reload that picks up the new interval."""
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.runtime_data.update_interval == timedelta(hours=6)

    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_UPDATE_INTERVAL: 12}
    )
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data.update_interval == timedelta(hours=12)
