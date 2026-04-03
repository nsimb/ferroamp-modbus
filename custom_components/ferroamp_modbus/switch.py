"""Switch platform for Ferroamp Modbus (import/export limit control)."""
from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SWITCH_DEFINITIONS, SwitchDefinition
from .coordinator import FerroampModbusFastCoordinator
from .entity import FerroampModbusEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    fast_coordinator: FerroampModbusFastCoordinator = data["fast"]

    async_add_entities(
        FerroampModbusSwitch(fast_coordinator, entry.entry_id, defn)
        for defn in SWITCH_DEFINITIONS
    )


class FerroampModbusSwitch(FerroampModbusEntity, SwitchEntity):
    """Switch entity to enable/disable Ferroamp import or export limiting.

    State is read from the fast coordinator (input register, polled every 5 s).
    Writes use FC06 with the same pre-reset / apply sequence as the threshold
    number entities.
    """

    def __init__(
        self,
        coordinator: FerroampModbusFastCoordinator,
        entry_id: str,
        defn: SwitchDefinition,
    ) -> None:
        super().__init__(coordinator, entry_id, defn.key, defn.name)
        self._defn = defn
        if defn.icon:
            self._attr_icon = defn.icon

    @property
    def is_on(self) -> bool | None:
        """Return True when the limit is active."""
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._defn.status_key)
        if raw is None:
            return None
        return bool(raw)

    async def async_turn_on(self, **kwargs) -> None:
        """Enable the grid limit."""
        _LOGGER.debug("ferroamp_modbus: turning ON %s", self._defn.key)
        try:
            await self.coordinator.hub.async_write_register_with_apply(
                self._defn.write_address, 1, self._defn.apply_address
            )
        except Exception as exc:
            _LOGGER.error(
                "ferroamp_modbus: switch write FAILED %s=on: %s",
                self._defn.key,
                exc,
            )
            raise
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable the grid limit."""
        _LOGGER.debug("ferroamp_modbus: turning OFF %s", self._defn.key)
        try:
            await self.coordinator.hub.async_write_register_with_apply(
                self._defn.write_address, 0, self._defn.apply_address
            )
        except Exception as exc:
            _LOGGER.error(
                "ferroamp_modbus: switch write FAILED %s=off: %s",
                self._defn.key,
                exc,
            )
            raise
        await self.coordinator.async_request_refresh()
