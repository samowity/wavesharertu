"""Modbus RTU Analog Input 8CH device implementation."""

import logging
from collections.abc import Sequence
from enum import IntEnum
from time import sleep

from ...modbus import compute_CRC, validate_response, ModbusException

logger = logging.getLogger(__name__)


class AnalogInputMode(IntEnum):
    """Input range modes for Analog Input 8CH."""

    __descriptions = {
        "VOLTAGE_0_5V": "0-5V",
        "VOLTAGE_1_5V": "1-5V",
        "CURRENT_0_20mA": "0-20mA",
        "CURRENT_4_20mA": "4-20mA",
        "RAW_CODE": "Raw Code",
    }

    VOLTAGE_0_5V = 0x0000
    VOLTAGE_1_5V = 0x0001
    CURRENT_0_20mA = 0x0002
    CURRENT_4_20mA = 0x0003
    RAW_CODE = 0x0004

    def readable_name(self) -> str:
        """Return a human-readable name for a mode."""
        return self.__descriptions[self.name]


class ModbusRTUAnalogInput:
    """Interface for Waveshare Modbus RTU Analog Input 8CH device.

    This class provides specific functionality for reading analog input values
    and configuring input modes for individual channels of the Analog Input 8CH device.

    The device has 8 analog input channels that can be configured with different
    measurement ranges (voltage or current modes).
    """

    _MODES = AnalogInputMode

    def __init__(
        self,
        serial,
        address: int,
        modes: AnalogInputMode | Sequence[AnalogInputMode] | None = None,
    ):
        """Initialize Analog Input 8CH device.

        Args:
            serial: RS485 serial port object.
            address: Device Modbus address 1- 255 (0x01 - 0xFF).
            mode: Optional AnalogInputMode or sequence of 8 AnalogInputMode values
                to set on channels during initialization.

        Raises:
            ModbusException: If communication with the device fails when setting mode.
        """
        self.serial = serial
        self._address = address
        logger.debug(f"ModbusRTUAnalogInput8CH initialized with address {self._address:02X} " f"and serial port {self.serial.port!r}.")

        if modes is not None:
            self._check_modes_on_init(modes)

    def _check_modes_on_init(self, modes):
        """Check current channel modes during initialization and update if needed."""
        resolved_modes, mode_names = self._validate_modes(modes)

        current_modes = self.read_channel_modes()
        logger.info(f"Current channel modes: {[m.readable_name() for m in current_modes]}")

        if current_modes == resolved_modes:
            logger.info(f"All channels already set to {mode_names}")
        else:
            logger.info(f"Setting all channels to {mode_names}")
            self.set_all_channels_mode(resolved_modes)

    def _validate_modes(self, modes):
        """Validate mode input and return resolved modes with readable descriptions."""
        if isinstance(modes, self._MODES):
            resolved_modes = [modes] * 8
        elif isinstance(modes, Sequence) and not isinstance(modes, (str, bytes, bytearray)):
            if len(modes) != 8:
                raise ValueError("Modes must contain exactly 8 values")

            if not all(isinstance(mode, self._MODES) for mode in modes):
                raise TypeError(f"All modes must be {self._MODES.__name__} values")

            resolved_modes = list(modes)
        else:
            raise TypeError(f"Modes must be {self._MODES.__name__} or Sequence[{self._MODES.__name__}]")

        mode_names = [mode.readable_name() for mode in resolved_modes]
        return resolved_modes, mode_names

    def read_analog_inputs(self) -> list[int]:
        """Read analog input values from all 8 channels.

        Returns:
            List of 8 analog input values. The meaning of values depends on the
            configured mode for each channel.

        Raises:
            ModbusException: If communication with the device fails.
        """
        msg = bytes.fromhex(f"{self._address:02X} 04 00 00 00 08")
        msg += compute_CRC(msg)
        logger.debug(f"Reading analog inputs: {msg.hex()}")
        self.serial.write(msg)
        sleep(0.5)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Analog input response: {rsp.hex()}")

        validate_response(rsp)

        # Response format: address(1) + function(1) + byte_count(1) + data(16) + crc(2)
        # Each channel is 2 bytes, big-endian
        if len(rsp) < 2 + 1 + 16 + 2:  # Min valid response
            raise ModbusException(f"Response too short: {rsp.hex()}")

        values = []
        for i in range(8):
            offset = 3 + i * 2  # Skip address, function code, and byte count
            value = int.from_bytes(rsp[offset : offset + 2], byteorder="big")
            values.append(value)

        logger.debug(f"Analog input values: {values}")
        return values

    def read_channel_modes(self) -> list[AnalogInputMode]:
        """Read the configured input mode for each channel.

        Returns:
            List of 8 AnalogInputMode values for each channel.

        Raises:
            ModbusException: If communication with the device fails.
        """
        msg = bytes.fromhex(f"{self._address:02X} 03 10 00 00 08")
        msg += compute_CRC(msg)
        logger.debug(f"Reading channel modes: {msg.hex()}")
        self.serial.write(msg)
        sleep(0.5)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Channel modes response: {rsp.hex()}")

        validate_response(rsp)

        # Response format: address(1) + function(1) + byte_count(1) + data(16) + crc(2)
        if len(rsp) < 2 + 1 + 16 + 2:
            raise ModbusException(f"Response too short: {rsp.hex()}")

        modes = []
        for i in range(8):
            offset = 3 + i * 2  # Skip address, function code, and byte count
            mode_value = int.from_bytes(rsp[offset : offset + 2], byteorder="big")
            modes.append(self._MODES(mode_value))

        logger.debug(f"Channel modes: {modes}")
        return modes

    def set_channel_mode(self, channel: int, mode: AnalogInputMode) -> None:
        """Set the input mode for a single channel.

        Args:
            channel: Channel number (1-8).
            mode: AnalogInputMode to set.

        Raises:
            ValueError: If channel is out of valid range.
            ModbusException: If communication with the device fails.
        """
        if not 1 <= channel <= 8:
            raise ValueError("Channel must be 1-8")

        register_addr = 0x1000 + (channel - 1)
        msg = bytes.fromhex(f"{self._address:02X} 06 {register_addr:04X} 00 {int(mode):02X}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting channel {channel} mode to {mode.name} ({mode.readable_name()}): {msg.hex()}")
        self.serial.write(msg)
        sleep(0.5)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set channel mode response: {rsp.hex()}")

        validate_response(rsp)

        logger.info(f"Channel {channel} mode set to {mode.name} ({mode.readable_name()})")

    def set_all_channels_mode(self, modes: AnalogInputMode | Sequence[AnalogInputMode]) -> None:
        """Set input mode for all channels.

        Args:
            modes: Single AnalogInputMode for all channels or list of 8
                AnalogInputMode values for channels 1-8.

        Raises:
            ValueError: If modes sequence does not contain exactly 8 values.
            TypeError: If modes is not AnalogInputMode or Sequence[AnalogInputMode].
            ModbusException: If communication with the device fails.
        """
        resolved_modes, mode_names = self._validate_modes(modes)

        # Build command to set all 8 channels (channel 1 -> first list item, etc.)
        mode_bytes = " ".join(f"00 {int(mode):02X}" for mode in resolved_modes)
        msg = bytes.fromhex(f"{self._address:02X} 10 10 00 00 08 10 {mode_bytes}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting all channel modes: {msg.hex()}")
        self.serial.write(msg)
        sleep(0.5)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set all channels mode response: {rsp.hex()}")

        validate_response(rsp)

        logger.info(f"All channel modes set (ch1-ch8): {mode_names}")
