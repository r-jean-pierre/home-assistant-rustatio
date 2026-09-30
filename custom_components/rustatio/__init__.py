"""Rustatio integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RustatioApi
from .const import CONF_BASE_URL, CONF_TOKEN
from .coordinator import RustatioCoordinator

PLATFORMS = (Platform.SENSOR, Platform.BINARY_SENSOR)

type RustatioConfigEntry = ConfigEntry[RustatioCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RustatioConfigEntry,
) -> bool:
    """Set up Rustatio from a config entry."""
    api = RustatioApi(
        async_get_clientsession(hass),
        entry.data[CONF_BASE_URL],
        entry.data.get(CONF_TOKEN),
    )

    coordinator = RustatioCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: RustatioConfigEntry,
) -> bool:
    """Unload a Rustatio config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
