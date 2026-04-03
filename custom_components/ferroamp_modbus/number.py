"""Number platform for Ferroamp Modbus (import/export threshold control)."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_MAX_VALUE,
    CONF_MIN_VALUE,
    DOMAIN,
    NUMBER_DEFINITIONS,
    NumberDefinition,
)
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
    config = {**entry.data, **entry.options}

    async_add_entities(
        FerroampModbusNumber(fast_coordinator, entry.entry_id, defn, config)
        for defn in NUMBER_DEFINITIONS
    )


class FerroampModbusNumber(FerroampModbusEntity, NumberEntity):
    """A writable number entity backed by a Modbus float32 register.

    Reads its current value from the fast coordinator (which polls the
    *System Value* read-back register).  Writes use HA's built-in modbus
    service (the same hub used by the configuration.yaml templates) to
    avoid TCP connection conflicts with the device.
    """

    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: FerroampModbusFastCoordinator,
        entry_id: str,
        defn: NumberDefinition,
        config: dict[str, float | str | int],
    ) -> None:
        super().__init__(coordinator, entry_id, defn.key, defn.name)
        self._defn = defn
        self._attr_native_unit_of_measurement = defn.unit
        self._attr_device_class = defn.device_class
        self._attr_native_min_value = config.get(CONF_MIN_VALUE, defn.min_value)
        self._attr_native_max_value = config.get(CONF_MAX_VALUE, defn.max_value)
        self._attr_native_step = defn.step
        if defn.icon:
            self._attr_icon = defn.icon

    def _get_other_value(self, key: str) -> float | None:
        """Return a rounded system value from the coordinator by sensor key."""
        raw = (self.coordinator.data or {}).get(key)
        if raw is None:
            return None
        return float(int(round(float(raw))))

    @property
    def native_min_value(self) -> float:
        """Import threshold floor is the current export threshold."""
        base = self._attr_native_min_value
        if self._defn.key == "import_threshold":
            export = self._get_other_value("export_threshold_system_value")
            if export is not None:
                return max(base, export)
        return base

    @property
    def native_max_value(self) -> float:
        """Export threshold ceiling is the current import threshold."""
        base = self._attr_native_max_value
        if self._defn.key == "export_threshold":
            imp = self._get_other_value("import_threshold_system_value")
            if imp is not None:
                return min(base, imp)
        return base

    @property
    def native_value(self) -> float | None:
        """Return the current value read back from the device."""
        if self.coordinator.data is None:
            return None
        sensor_key = f"{self._defn.key}_system_value"
        raw = self.coordinator.data.get(sensor_key)
        if raw is None:
            return None
        if self._defn.as_int:
            return float(int(round(float(raw))))
        return round(float(raw), 1)

    async def async_set_native_value(self, value: float) -> None:
        """Write the new threshold directly via the Ferroamp Modbus hub."""
        value = max(self.native_min_value, min(self.native_max_value, value))
        _LOGGER.debug(
            "ferroamp_modbus: writing %s = %s W (addr=%s apply=%s)",
            self._defn.key, value, self._defn.write_address, self._defn.apply_address,
        )
        try:
            await self.coordinator.hub.async_write_float32_word_swap(
                self._defn.write_address, float(value), self._defn.apply_address
            )
        except Exception as exc:
            _LOGGER.error(
                "ferroamp_modbus: write FAILED %s = %s: %s", self._defn.key, value, exc
            )
            raise
        _LOGGER.debug("ferroamp_modbus: write OK %s = %s", self._defn.key, value)
        await self.coordinator.async_request_refresh()
