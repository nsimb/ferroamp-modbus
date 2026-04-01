"""Ferroamp Modbus TCP hub — manages the connection and raw register I/O."""
from __future__ import annotations

import logging
import struct
import threading
from typing import TYPE_CHECKING

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import DTYPE_FLOAT32, DTYPE_INT16, DTYPE_UINT16, DTYPE_UINT32, REG_INPUT

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_MAX_REGISTERS_PER_READ = 125
_MODBUS_TIMEOUT = 5  # seconds per request


class ModbusNotEnabledError(Exception):
    """Raised when TCP connects but Modbus TCP is not active on the device."""


def _decode_float32_word_swap(regs: list[int]) -> float:
    """Decode Ferroamp float32 (word-swapped / CDAB order: LSW at lower address)."""
    lsw, msw = regs[0], regs[1]
    packed = struct.pack(">HH", msw, lsw)
    return struct.unpack(">f", packed)[0]


def _encode_float32_word_swap(value: float) -> list[int]:
    """Encode float32 for writing to Ferroamp (word-swapped / CDAB order)."""
    packed = struct.pack(">f", value)
    msw = struct.unpack(">H", packed[0:2])[0]
    lsw = struct.unpack(">H", packed[2:4])[0]
    return [lsw, msw]


class FerroampModbusHub:
    """Modbus TCP hub using a synchronous client run in a thread-pool executor.

    Using the synchronous ModbusTcpClient avoids the async-client event-loop
    compatibility issues seen with pymodbus 3.7+ in Home Assistant.  Each
    public method is async (awaitable from HA coroutines) but the actual
    Modbus I/O runs in a background thread via hass.async_add_executor_job.
    A threading.Lock serialises access so only one Modbus transaction runs at
    a time across both coordinators.
    """

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        self._hass = hass
        self._host = host
        self._port = port
        self._client: ModbusTcpClient | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal sync helpers (run inside executor threads)
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        """Open or re-open the Modbus TCP connection (sync, call from executor)."""
        if self._client and self._client.is_socket_open():
            return
        _LOGGER.debug("Connecting to Ferroamp Modbus at %s:%s", self._host, self._port)
        self._client = ModbusTcpClient(
            self._host, port=self._port, timeout=_MODBUS_TIMEOUT
        )
        if not self._client.connect():
            self._client = None
            raise ConnectionError(
                f"Cannot connect to Ferroamp Modbus at {self._host}:{self._port}"
            )

    def _read_registers_sync(
        self, address: int, count: int, input_type: str
    ) -> list[int]:
        """Read registers synchronously (must be called from executor thread).

        The slave / unit-ID parameter is intentionally omitted — newer pymodbus
        removed it from individual method signatures.  Modbus TCP uses IP
        addressing rather than unit IDs for device selection, and Ferroamp
        ignores the MBAP unit-ID field on direct TCP connections.
        """
        with self._lock:
            self._ensure_connected()
            results: list[int] = []
            remaining = count
            offset = 0
            while remaining > 0:
                batch = min(remaining, _MAX_REGISTERS_PER_READ)
                if input_type == REG_INPUT:
                    resp = self._client.read_input_registers(
                        address + offset, count=batch
                    )
                else:
                    resp = self._client.read_holding_registers(
                        address + offset, count=batch
                    )
                if resp.isError():
                    raise ModbusException(
                        f"Modbus exception code for register {address + offset}: {resp}"
                    )
                results.extend(resp.registers)
                offset += batch
                remaining -= batch
            return results

    def _write_registers_sync(self, address: int, values: list[int]) -> None:
        """Write registers synchronously (must be called from executor thread)."""
        with self._lock:
            self._ensure_connected()
            resp = self._client.write_registers(address, values)
            if resp.isError():
                raise ModbusException(f"Write error at {address}: {resp}")

    def _write_register_sync(self, address: int, value: int) -> None:
        """Write a single register synchronously (must be called from executor thread)."""
        with self._lock:
            self._ensure_connected()
            resp = self._client.write_register(address, value)
            if resp.isError():
                raise ModbusException(f"Write error at {address}: {resp}")

    def _close_sync(self) -> None:
        """Close the Modbus connection (sync)."""
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None

    # ------------------------------------------------------------------
    # Public async API (awaitable from HA coroutines)
    # ------------------------------------------------------------------

    async def async_validate_modbus_protocol(self) -> None:
        """Validate TCP reachability on port 502.

        Raises:
            ConnectionError: cannot reach the device.
        """
        await self._hass.async_add_executor_job(self._ensure_connected)
        # Leave connection open for re-use.

    async def async_close(self) -> None:
        """Close the Modbus TCP connection."""
        await self._hass.async_add_executor_job(self._close_sync)

    async def async_read_registers(
        self, address: int, count: int, input_type: str
    ) -> list[int]:
        """Read *count* registers starting at *address* (async wrapper)."""
        return await self._hass.async_add_executor_job(
            self._read_registers_sync, address, count, input_type
        )

    async def async_read_value(
        self, address: int, data_type: str, input_type: str
    ) -> int | float:
        """Read and decode a single value."""
        count = 2 if data_type == DTYPE_FLOAT32 else 1
        regs = await self.async_read_registers(address, count, input_type)

        if data_type == DTYPE_UINT16:
            return regs[0]
        if data_type == DTYPE_INT16:
            val = regs[0]
            return val - 0x10000 if val >= 0x8000 else val
        if data_type == DTYPE_UINT32:
            return (regs[0] << 16) | regs[1]
        if data_type == DTYPE_FLOAT32:
            return _decode_float32_word_swap(regs)

        raise ValueError(f"Unknown data type: {data_type}")

    async def async_write_float32_word_swap(
        self, address: int, value: float, apply_address: int
    ) -> None:
        """Write a float32 value (word-swapped) and pulse the apply register."""
        words = _encode_float32_word_swap(value)
        await self._hass.async_add_executor_job(
            self._write_registers_sync, address, words
        )
        await self._hass.async_add_executor_job(
            self._write_registers_sync, apply_address, [1]
        )
        await self._hass.async_add_executor_job(
            self._write_registers_sync, apply_address, [0]
        )

    async def async_write_register(self, address: int, value: int) -> None:
        """Write a single uint16 register."""
        await self._hass.async_add_executor_job(
            self._write_register_sync, address, value
        )
