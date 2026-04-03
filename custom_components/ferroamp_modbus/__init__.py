"""Ferroamp Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import FerroampModbusCoordinator, FerroampModbusFastCoordinator
from .hub import FerroampModbusHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ferroamp Modbus from a config entry."""
    config = {**entry.data, **entry.options}
    host = config[CONF_HOST]
    port = config[CONF_PORT]

    hub = FerroampModbusHub(hass, host, port)

    coordinator = FerroampModbusCoordinator(hass, hub)
    fast_coordinator = FerroampModbusFastCoordinator(hass, hub)

    # The coordinator connects on its first read; UpdateFailed here becomes
    # ConfigEntryNotReady and HA will retry automatically.
    await coordinator.async_config_entry_first_refresh()
    await fast_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "hub": hub,
        "standard": coordinator,
        "fast": fast_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data:
        await data["hub"].async_close()
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — reload the entry so the new host/port takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)
