"""Binary sensor platform for Ferroamp Modbus."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BINARY_SENSOR_DEFINITIONS, DOMAIN, BinarySensorDefinition
from .coordinator import FerroampModbusFastCoordinator
from .entity import FerroampModbusEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    fast_coordinator: FerroampModbusFastCoordinator = hass.data[DOMAIN][entry.entry_id][
        "fast"
    ]
    async_add_entities(
        FerroampModbusBinarySensor(fast_coordinator, entry.entry_id, defn)
        for defn in BINARY_SENSOR_DEFINITIONS
    )


class FerroampModbusBinarySensor(FerroampModbusEntity, BinarySensorEntity):
    """A single Ferroamp Modbus binary sensor."""

    def __init__(
        self,
        coordinator: FerroampModbusFastCoordinator,
        entry_id: str,
        defn: BinarySensorDefinition,
    ) -> None:
        super().__init__(coordinator, entry_id, defn.key, defn.name)
        self._defn = defn
        if defn.icon:
            self._attr_icon = defn.icon

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._defn.key)
