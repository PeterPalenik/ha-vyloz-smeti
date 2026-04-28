"""The Vyloz Smeti integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import VylozSmetiClient
from .const import PLATFORMS
from .coordinator import VylozSmetiCoordinator

__all__ = ["VylozSmetiConfigEntry", "async_setup_entry", "async_unload_entry"]

type VylozSmetiConfigEntry = ConfigEntry[VylozSmetiCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VylozSmetiConfigEntry) -> bool:
    """Set up Vyloz Smeti from a config entry."""
    session = async_get_clientsession(hass)
    client = VylozSmetiClient(session)
    coordinator = VylozSmetiCoordinator(hass, entry, client)

    # Raises ConfigEntryNotReady on first-fetch failure.
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VylozSmetiConfigEntry) -> bool:
    """Unload a Vyloz Smeti config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: VylozSmetiConfigEntry
) -> None:
    """Reload entry when its options change (e.g. update_interval)."""
    await hass.config_entries.async_reload(entry.entry_id)
