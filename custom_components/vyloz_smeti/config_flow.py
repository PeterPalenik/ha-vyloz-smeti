"""Config flow for the Vyloz Smeti integration."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .api import VylozSmetiClient, VylozSmetiError
from .const import (
    CONF_LOCATION_ID,
    CONF_LOCATION_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    MAX_UPDATE_INTERVAL_HOURS,
    MIN_UPDATE_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)


class VylozSmetiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the user-driven setup flow for Vyloz Smeti."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._locations: dict[int, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where the user picks a municipality."""
        errors: dict[str, str] = {}

        if not self._locations:
            try:
                self._locations = await self._async_load_locations()
            except VylozSmetiError as err:
                _LOGGER.warning("Could not load Vyloz Smeti locations: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error while loading locations")
                errors["base"] = "unknown"

            if not errors and not self._locations:
                errors["base"] = "no_locations"

            if errors:
                return self.async_show_form(
                    step_id="user",
                    errors=errors,
                )

        if user_input is not None:
            location_id = int(user_input[CONF_LOCATION_ID])
            location_name = self._locations[location_id]

            await self.async_set_unique_id(str(location_id))
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=location_name,
                data={
                    CONF_LOCATION_ID: location_id,
                    CONF_LOCATION_NAME: location_name,
                },
            )

        schema = vol.Schema({vol.Required(CONF_LOCATION_ID): vol.In(self._locations)})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_load_locations(self) -> dict[int, str]:
        """Fetch and format the location dropdown."""
        session = async_get_clientsession(self.hass)
        client = VylozSmetiClient(session)
        locations = await client.async_get_locations()

        city_counts = Counter(loc.city for loc in locations)
        formatted: dict[int, str] = {}
        for loc in locations:
            label = (
                f"{loc.city} ({loc.code})" if city_counts[loc.city] > 1 else loc.city
            )
            formatted[loc.location_id] = label

        return dict(sorted(formatted.items(), key=lambda item: item[1].casefold()))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return VylozSmetiOptionsFlow()


class VylozSmetiOptionsFlow(OptionsFlow):
    """Allow the user to tune the polling interval after install."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            # NumberSelector returns float; coerce to int so type stays stable.
            return self.async_create_entry(
                title="",
                data={CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL])},
            )

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL_HOURS
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL, default=current_interval
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_UPDATE_INTERVAL_HOURS,
                        max=MAX_UPDATE_INTERVAL_HOURS,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="h",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
