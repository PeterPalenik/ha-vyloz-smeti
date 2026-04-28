"""Tests for the Vyloz Smeti config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
import voluptuous as vol
from custom_components.vyloz_smeti.const import (
    API_LOCATIONS_URL,
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .const import LOCATION_ID


async def test_user_flow_happy_path(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    locations_payload: list[dict[str, Any]],
) -> None:
    """User selects a location and the entry is created."""
    aioclient_mock.get(API_LOCATIONS_URL, json=locations_payload)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    # The schema accepts known location ids and rejects unknown ones.
    schema = result["data_schema"]
    assert schema is not None
    schema({CONF_LOCATION_ID: 22222})  # Košice — must validate
    schema({CONF_LOCATION_ID: 12345})  # one of the duplicate Bratislavas
    with pytest.raises(vol.Invalid):
        schema({CONF_LOCATION_ID: 99999})

    with patch(
        "custom_components.vyloz_smeti.async_setup_entry", return_value=True
    ) as mock_setup:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_LOCATION_ID: 22222}
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Košice"
    assert result2["data"] == {
        CONF_LOCATION_ID: 22222,
        CONF_LOCATION_NAME: "Košice",
    }
    assert len(mock_setup.mock_calls) == 1


async def test_duplicate_city_names_get_code_suffix(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    locations_payload: list[dict[str, Any]],
) -> None:
    """When two municipalities share a name, the FCC code disambiguates them."""
    aioclient_mock.get(API_LOCATIONS_URL, json=locations_payload)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch("custom_components.vyloz_smeti.async_setup_entry", return_value=True):
        # 12345 + 12346 are both Bratislava → both must show the (code) suffix
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_LOCATION_ID: 12345}
        )
        await hass.async_block_till_done()
    assert result2["title"] == "Bratislava (BA-01)"


async def test_user_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A network error surfaces as a form error."""
    aioclient_mock.get(API_LOCATIONS_URL, exc=TimeoutError)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_no_locations(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """An empty location list is reported as no_locations."""
    aioclient_mock.get(API_LOCATIONS_URL, json=[])

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "no_locations"}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    locations_payload: list[dict[str, Any]],
    mock_config_entry: MockConfigEntry,
) -> None:
    """Configuring the same location twice aborts."""
    mock_config_entry.add_to_hass(hass)
    aioclient_mock.get(API_LOCATIONS_URL, json=locations_payload)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LOCATION_ID: LOCATION_ID}
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_api")
async def test_options_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The options flow updates the polling interval."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # NumberSelector emits a float — the flow must coerce it back to int.
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_INTERVAL: 12.0}
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    stored = mock_config_entry.options[CONF_UPDATE_INTERVAL]
    assert stored == 12
    assert isinstance(stored, int)
