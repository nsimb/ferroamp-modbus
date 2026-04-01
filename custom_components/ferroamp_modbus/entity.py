"""Base entity for Ferroamp Modbus."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FerroampModbusCoordinator, FerroampModbusFastCoordinator


class FerroampModbusEntity(
    CoordinatorEntity[FerroampModbusCoordinator | FerroampModbusFastCoordinator]
):
    """Base class for all Ferroamp Modbus entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FerroampModbusCoordinator | FerroampModbusFastCoordinator,
        entry_id: str,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Ferroamp Energy Hub",
            manufacturer="Ferroamp",
            model="Energy Hub",
        )
