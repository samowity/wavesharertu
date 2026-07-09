"""Modbus RTU Digital IO device implementation."""

import logging
from enum import IntEnum

from ...modbus import compute_CRC, validate_response, ModbusException

logger = logging.getLogger(__name__)


class DigitalOutputMode(IntEnum):
    """Control modes for digital outputs."""

    __descriptions = {
        "NORMAL": "Normal mode (direct control)",
        "LINKAGE": "Linkage mode (follows input)",
        "TOGGLE": "Toggle mode (toggles on input pulse)",
        "EDGE_TRIGGER": "Edge trigger mode (changes on input level change)",
    }

    NORMAL = 0x0000
    LINKAGE = 0x0001
    TOGGLE = 0x0002
    EDGE_TRIGGER = 0x0003

    def readable_name(self) -> str:
        """Return a human-readable name for a mode."""
        return self.__descriptions[self.name]


class DigitalIO:
    """Interface for Waveshare Modbus RTU Digital IO device.

    This class provides functionality for reading and controlling 8 digital inputs
    and 8 digital outputs using Modbus RTU protocol.

    Register map (Development Protocol V2):
    - 0x0000-0x0007: Output channels 1-8 (0xFF00=on, 0x0000=off, 0x5500=toggle)
    - 0x00FF: Control all outputs
    - 1x0000-1x0007: Input channels 1-8 status
    - 4x1000-4x1007: Output channel control modes
    """

    _MODES = DigitalOutputMode

    def __init__(self, serial, address: int):
        """Initialize Digital IO device.

        Args:
            serial: RS485 serial port object.
            address: Device Modbus address 1-255 (0x01 - 0xFF).

        Raises:
            ModbusException: If communication with the device fails.
        """
        self.serial = serial
        self._address = address
        logger.debug(f"DigitalIO initialized with address {self._address:02X} and serial port {self.serial.port!r}.")

    def read_digital_inputs(self) -> list[bool]:
        """Read digital input status from all 8 channels.

        Returns:
            List of 8 boolean values for channels 1-8 (True = triggered/on, False = not triggered/off).

        Raises:
            ModbusException: If communication with the device fails.
        """
        # Function code 0x02: Read input status (discrete inputs)
        # Address: 0x0000, Quantity: 8 channels
        msg = bytes.fromhex(f"{self._address:02X} 02 00 00 00 08")
        msg += compute_CRC(msg)
        logger.debug(f"Reading digital inputs: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Digital inputs response: {rsp.hex()}")

        validate_response(rsp)

        # Response format: address(1) + function(1) + byte_count(1) + data(1) + crc(2)
        if len(rsp) < 2 + 1 + 1 + 2:
            raise ModbusException(f"Response too short: {rsp.hex()}")

        # Extract status byte and convert to list of booleans
        status_byte = rsp[3]
        inputs = [(status_byte >> i) & 1 == 1 for i in range(8)]

        logger.debug(f"Digital input status: {inputs}")
        return inputs

    def read_digital_outputs(self) -> list[bool]:
        """Read digital output status from all 8 channels.

        Returns:
            List of 8 boolean values for channels 1-8 (True = on, False = off).

        Raises:
            ModbusException: If communication with the device fails.
        """
        # Function code 0x01: Read output status (coils)
        # Address: 0x0000, Quantity: 8 channels
        msg = bytes.fromhex(f"{self._address:02X} 01 00 00 00 08")
        msg += compute_CRC(msg)
        logger.debug(f"Reading digital outputs: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Digital outputs response: {rsp.hex()}")

        validate_response(rsp)

        # Response format: address(1) + function(1) + byte_count(1) + data(1) + crc(2)
        if len(rsp) < 2 + 1 + 1 + 2:
            raise ModbusException(f"Response too short: {rsp.hex()}")

        # Extract status byte and convert to list of booleans
        status_byte = rsp[3]
        outputs = [(status_byte >> i) & 1 == 1 for i in range(8)]

        logger.debug(f"Digital output status: {outputs}")
        return outputs

    def set_output_channel(self, channel: int, state: bool) -> None:
        """Set the state of a single digital output channel.

        Args:
            channel: Channel number (1-8).
            state: True to turn on, False to turn off.

        Raises:
            ValueError: If channel is out of valid range.
            ModbusException: If communication with the device fails.
        """
        if not 1 <= channel <= 8:
            raise ValueError("Channel must be 1-8")

        register_addr = 0x0000 + (channel - 1)
        command = 0xFF00 if state else 0x0000

        # Function code 0x05: Write single coil
        msg = bytes.fromhex(f"{self._address:02X} 05 {register_addr:04X} {command:04X}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting channel {channel} output to {'on' if state else 'off'}: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set channel output response: {rsp.hex()}")

        validate_response(rsp)
        logger.info(f"Channel {channel} output set to {'on' if state else 'off'}")

    def set_all_outputs(self, state: bool) -> None:
        """Set all digital output channels to the same state.

        Args:
            state: True to turn all on, False to turn all off.

        Raises:
            ModbusException: If communication with the device fails.
        """
        command = 0xFF00 if state else 0x0000

        # Function code 0x05: Write single coil to special address 0x00FF (all outputs)
        msg = bytes.fromhex(f"{self._address:02X} 05 00 FF {command:04X}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting all outputs to {'on' if state else 'off'}: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set all outputs response: {rsp.hex()}")

        validate_response(rsp)
        logger.info(f"All outputs set to {'on' if state else 'off'}")

    def set_outputs_by_mask(self, mask: int) -> None:
        """Set multiple output channels using a bitmask.

        Args:
            mask: 8-bit value where bit i represents channel i+1 (1=on, 0=off).

        Raises:
            ValueError: If mask is out of valid range.
            ModbusException: If communication with the device fails.
        """
        if not 0 <= mask <= 0xFF:
            raise ValueError("Mask must be 0-255")

        # Function code 0x0F: Write multiple coils
        # Address: 0x0000, Quantity: 8 channels
        msg = bytes.fromhex(f"{self._address:02X} 0F 00 00 00 08 01 {mask:02X}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting outputs with mask 0x{mask:02X}: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set outputs response: {rsp.hex()}")

        validate_response(rsp)
        logger.info(f"Output channels set according to mask 0x{mask:02X}")

    def toggle_output_channel(self, channel: int) -> None:
        """Toggle the state of a single digital output channel.

        Args:
            channel: Channel number (1-8).

        Raises:
            ValueError: If channel is out of valid range.
            ModbusException: If communication with the device fails.
        """
        if not 1 <= channel <= 8:
            raise ValueError("Channel must be 1-8")

        register_addr = 0x0000 + (channel - 1)
        command = 0x5500  # Toggle command

        # Function code 0x05: Write single coil
        msg = bytes.fromhex(f"{self._address:02X} 05 {register_addr:04X} {command:04X}")
        msg += compute_CRC(msg)
        logger.debug(f"Toggling channel {channel} output: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Toggle channel output response: {rsp.hex()}")

        validate_response(rsp)
        logger.info(f"Channel {channel} output toggled")

    def read_output_control_modes(self) -> list[DigitalOutputMode]:
        """Read the control mode for each output channel.

        Returns:
            List of 8 DigitalOutputMode values for each channel.

        Raises:
            ModbusException: If communication with the device fails.
        """
        # Function code 0x03: Read holding registers
        # Address: 0x1000, Quantity: 8 registers
        msg = bytes.fromhex(f"{self._address:02X} 03 10 00 00 08")
        msg += compute_CRC(msg)
        logger.debug(f"Reading output control modes: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Output control modes response: {rsp.hex()}")

        validate_response(rsp)

        # Response format: address(1) + function(1) + byte_count(1) + data(16) + crc(2)
        if len(rsp) < 2 + 1 + 16 + 2:
            raise ModbusException(f"Response too short: {rsp.hex()}")

        modes = []
        for i in range(8):
            offset = 3 + i * 2  # Skip address, function code, and byte count
            mode_value = int.from_bytes(rsp[offset : offset + 2], byteorder="big")
            modes.append(self._MODES(mode_value))

        logger.debug(f"Output control modes: {modes}")
        return modes

    def set_output_control_mode(self, channel: int, mode: DigitalOutputMode) -> None:
        """Set the control mode for a single output channel.

        Args:
            channel: Channel number (1-8).
            mode: DigitalOutputMode to set.

        Raises:
            ValueError: If channel is out of valid range.
            ModbusException: If communication with the device fails.
        """
        if not 1 <= channel <= 8:
            raise ValueError("Channel must be 1-8")

        register_addr = 0x1000 + (channel - 1)
        mode_value = int(mode)

        # Function code 0x06: Write single register
        msg = bytes.fromhex(f"{self._address:02X} 06 {register_addr:04X} {mode_value:04X}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting channel {channel} control mode to {mode.name} ({mode.readable_name()}): {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set control mode response: {rsp.hex()}")

        validate_response(rsp)
        logger.info(f"Channel {channel} control mode set to {mode.name} ({mode.readable_name()})")

    def set_all_output_control_modes(self, mode: DigitalOutputMode) -> None:
        """Set the control mode for all output channels to the same mode.

        Args:
            mode: DigitalOutputMode to set for all channels.

        Raises:
            ModbusException: If communication with the device fails.
        """
        mode_value = int(mode)
        # Build command for all 8 channels with the same mode
        # Function code 0x10: Write multiple registers
        # Address: 0x1000, Quantity: 8 registers
        data = b"".join(mode_value.to_bytes(2, byteorder="big") for _ in range(8))
        msg = bytes.fromhex(f"{self._address:02X} 10 10 00 00 08 10") + data
        msg += compute_CRC(msg)
        logger.debug(f"Setting all output control modes to {mode.name} ({mode.readable_name()}): {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set all control modes response: {rsp.hex()}")

        validate_response(rsp)
        logger.info(f"All output control modes set to {mode.name} ({mode.readable_name()})")
