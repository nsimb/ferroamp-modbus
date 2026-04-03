"""DataUpdateCoordinators for Ferroamp Modbus."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BINARY_SENSOR_DEFINITIONS,
    DOMAIN,
    FAST_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    SENSOR_DEFINITIONS,
)
from .hub import FerroampModbusHub

_LOGGER = logging.getLogger(__name__)


class FerroampModbusCoordinator(DataUpdateCoordinator[dict[str, int | float]]):
    """Coordinator that polls all standard-interval (30 s) registers."""

    def __init__(self, hass: HomeAssistant, hub: FerroampModbusHub) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_standard",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self._hub = hub
        self._sensor_defs = [
            s for s in SENSOR_DEFINITIONS if s.scan_interval == DEFAULT_SCAN_INTERVAL
        ]

    @property
    def hub(self) -> FerroampModbusHub:
        return self._hub

    async def _async_update_data(self) -> dict[str, int | float]:
        data: dict[str, int | float] = {}
        first_error: Exception | None = None

        for defn in self._sensor_defs:
            try:
                value = await self._hub.async_read_value(
                    defn.address, defn.data_type, defn.input_type
                )
                data[defn.key] = value
            except Exception as exc:  # noqa: BLE001
                if first_error is None:
                    first_error = exc
                _LOGGER.error(
                    "ferroamp_modbus: failed to read %s (addr %s, type %s): %s — %s",
                    defn.key,
                    defn.address,
                    defn.input_type,
                    type(exc).__name__,
                    exc,
                )
                if self.data and defn.key in self.data:
                    data[defn.key] = self.data[defn.key]

        if not data:
            raise UpdateFailed(
                f"No data could be read from Ferroamp Modbus: {first_error}"
            )
        return data


class FerroampModbusFastCoordinator(DataUpdateCoordinator[dict[str, int | float | bool]]):
    """Coordinator that polls fast-interval (5 s) registers.

    Covers sensors at addresses 8000-8016 (import/export limits and thresholds)
    plus the binary sensors.
    """

    def __init__(self, hass: HomeAssistant, hub: FerroampModbusHub) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_fast",
            update_interval=timedelta(seconds=FAST_SCAN_INTERVAL),
        )
        self._hub = hub
        self._sensor_defs = [
            s for s in SENSOR_DEFINITIONS if s.scan_interval == FAST_SCAN_INTERVAL
        ]
        self._binary_defs = BINARY_SENSOR_DEFINITIONS

    @property
    def hub(self) -> FerroampModbusHub:
        return self._hub

    async def _async_update_data(self) -> dict[str, int | float | bool]:
        data: dict[str, int | float | bool] = {}
        first_error: Exception | None = None

        for defn in self._sensor_defs:
            try:
                value = await self._hub.async_read_value(
                    defn.address, defn.data_type, defn.input_type
                )
                data[defn.key] = value
            except Exception as exc:
                if first_error is None:
                    first_error = exc
                _LOGGER.warning(
                    "Could not read %s (addr %s): %s", defn.key, defn.address, exc
                )
                if self.data and defn.key in self.data:
                    data[defn.key] = self.data[defn.key]

        for defn in self._binary_defs:
            try:
                regs = await self._hub.async_read_registers(
                    defn.address, 1, defn.input_type
                )
                data[defn.key] = bool(regs[0])
            except Exception as exc:
                if first_error is None:
                    first_error = exc
                _LOGGER.warning(
                    "Could not read binary sensor %s (addr %s): %s",
                    defn.key,
                    defn.address,
                    exc,
                )
                if self.data and defn.key in self.data:
                    data[defn.key] = self.data[defn.key]

        if not data:
            raise UpdateFailed(
                f"No fast data could be read from Ferroamp Modbus: {first_error}"
            )

        return data
