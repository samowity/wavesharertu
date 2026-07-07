"""Modbus RTU Analog Input 8CH (B) device implementation."""

import logging
from collections.abc import Sequence
from enum import IntEnum

from ..analog_input.ai import AnalogInput

logger = logging.getLogger(__name__)


class AnalogInputModeB(IntEnum):
    """Input range modes for Analog Input 8CH (B)."""

    __descriptions = {
        "VOLTAGE_0_10V": "0-10 V",
        "VOLTAGE_2_10V": "2-10 V",
        "CURRENT_0_20mA": "0-20 mA",
        "CURRENT_4_20mA": "4-20 mA",
        "RAW_CODE": "Raw Code",
    }

    VOLTAGE_0_10V = 0x0000
    VOLTAGE_2_10V = 0x0001
    CURRENT_0_20mA = 0x0002
    CURRENT_4_20mA = 0x0003
    RAW_CODE = 0x0004

    def readable_name(self) -> str:
        """Return a human-readable name for a mode."""
        return self.__descriptions[self.name]


class AnalogInputB(AnalogInput):
    """Interface for Waveshare Modbus RTU Analog Input 8CH (B) device.

    Version B differs from version A in voltage ranges:
    - mode 0: 0-10V
    - mode 1: 2-10V

    Current modes and Modbus register layout remain the same.
    """

    _MODES = AnalogInputModeB

    def __init__(
        self,
        serial,
        address: int,
        modes: AnalogInputModeB | Sequence[AnalogInputModeB] | None = None,
    ):
        """Initialize Analog Input 8CH (B) device.

        Args:
            serial: RS485 serial port object.
            address: Device Modbus address 1-255 (0x01 - 0xFF).
            mode: Optional AnalogInputModeB or sequence of 8 AnalogInputModeB values
                to set on channels during initialization.

        Raises:
            ModbusException: If communication with the device fails when setting mode.
        """
        self.serial = serial
        self._address = address
        logger.debug(f"AnalogInputB initialized with address {self._address:02X} " f"and serial port {self.serial.port!r}.")

        if modes is not None:
            self._check_modes_on_init(modes)

    def read_analog_inputs(self) -> list[int]:
        """Read analog input values from all 8 channels.

        Returns:
            List of 8 analog input values. The meaning of values depends on the
            configured mode for each channel.

        Raises:
            ModbusException: If communication with the device fails.
        """
        return super().read_analog_inputs()

    def read_channel_modes(self) -> list[AnalogInputModeB]:
        """Read the configured input mode for each channel.

        Returns:
            List of 8 AnalogInputModeB values for each channel.

        Raises:
            ModbusException: If communication with the device fails.
        """
        return super().read_channel_modes()

    def set_channel_mode(self, channel: int, mode: AnalogInputModeB) -> None:
        """Set the input mode for a single channel.

        Args:
            channel: Channel number (1-8).
            mode: AnalogInputMode to set.

        Raises:
            ValueError: If channel is out of valid range.
            ModbusException: If communication with the device fails.
        """
        super().set_channel_mode(channel, mode)

    def set_all_channels_mode(self, modes: AnalogInputModeB | Sequence[AnalogInputModeB]) -> None:
        """Set input mode for all channels.

        Args:
            modes: Single AnalogInputModeB for all channels or list of 8
                AnalogInputModeB values for channels 1-8.

        Raises:
            ValueError: If modes sequence does not contain exactly 8 values.
            TypeError: If modes is not AnalogInputModeB or Sequence[AnalogInputModeB].
            ModbusException: If communication with the device fails.
        """
        super().set_all_channels_mode(modes)
