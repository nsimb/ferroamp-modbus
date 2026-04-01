"""Number platform for Ferroamp Modbus (import/export threshold control)."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUMBER_DEFINITIONS, NumberDefinition
from .coordinator import FerroampModbusFastCoordinator
from .entity import FerroampModbusEntity
from .hub import FerroampModbusHub

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    fast_coordinator: FerroampModbusFastCoordinator = data["fast"]
    hub: FerroampModbusHub = data["hub"]

    async_add_entities(
        FerroampModbusNumber(fast_coordinator, hub, entry.entry_id, defn)
        for defn in NUMBER_DEFINITIONS
    )


class FerroampModbusNumber(FerroampModbusEntity, NumberEntity):
    """A writable number entity backed by a Modbus float32 register.

    Reads its current value from the fast coordinator (which polls the
    *System Value* read-back register).  Writes encode the new value as
    a word-swapped float32 and pulse the apply register, exactly mirroring
    the original Jinja2 template in configuration.yaml.
    """

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FerroampModbusFastCoordinator,
        hub: FerroampModbusHub,
        entry_id: str,
        defn: NumberDefinition,
    ) -> None:
        super().__init__(coordinator, entry_id, defn.key, defn.name)
        self._defn = defn
        self._hub = hub
        self._attr_native_unit_of_measurement = defn.unit
        self._attr_device_class = defn.device_class
        self._attr_native_min_value = defn.min_value
        self._attr_native_max_value = defn.max_value
        self._attr_native_step = defn.step
        if defn.icon:
            self._attr_icon = defn.icon

    @property
    def native_value(self) -> float | None:
        """Return the current value read back from the device."""
        # The fast coordinator stores the system-value sensor keyed by the
        # sensor definition key (import_threshold_system_value /
        # export_threshold_system_value).  The number entity shares the same
        # read address so we look up the matching sensor key.
        if self.coordinator.data is None:
            return None
        sensor_key = f"{self._defn.key}_system_value"
        raw = self.coordinator.data.get(sensor_key)
        if raw is None:
            return None
        return round(float(raw), 1)

    async def async_set_native_value(self, value: float) -> None:
        """Write the new threshold to the device and refresh."""
        await self._hub.async_write_float32_word_swap(
            self._defn.write_address,
            value,
            self._defn.apply_address,
        )
        await self.coordinator.async_request_refresh()
