"""Modbus RTU Analog Output 8CH device implementation."""

import logging
from collections.abc import Sequence

from ...modbus import compute_CRC, validate_response, ModbusException

logger = logging.getLogger(__name__)


class AnalogOutput:
    """Interface for Waveshare Modbus RTU Analog Output 8CH device.

    This class provides functionality for reading and setting analog output values
    for all 8 output channels.

    Register map (Development Protocol V2):
    - 0x0000-0x0007: channels 1-8 output values
    - Function 0x03: read output values
    - Function 0x06: write single output value
    - Function 0x10: write multiple output values
    """

    def __init__(
        self,
        serial,
        address: int,
    ):
        """Initialize Analog Output 8CH device.

        Args:
            serial: RS485 serial port object.
            address: Device Modbus address 1-255 (0x01 - 0xFF).

        Raises:
            ModbusException: If communication with the device fails when setting outputs.
        """
        self.serial = serial
        self._address = address
        logger.debug(f"AnalogOutput initialized with address {self._address:02X} and serial port {self.serial.port!r}.")


    def _validate_output(self, value_uA: int) -> None:
        """Validate a single channel output value."""
        if not isinstance(value_uA, int):
            raise TypeError("Output value must be an integer")

        if not 0 <= value_uA <= 20_000:
            raise ValueError(
                f"Output value {value_uA} out of range (0-20 000 uA)"
            )

    def read_channel_outputs(self) -> list[int]:
        """Read analog output values from all 8 channels.

        Returns:
            List of 8 output values for channels 1-8.

        Raises:
            ModbusException: If communication with the device fails.
        """
        msg = bytes.fromhex(f"{self._address:02X} 03 00 00 00 08")
        msg += compute_CRC(msg)
        logger.debug(f"Reading channel outputs: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Channel outputs response: {rsp.hex()}")

        validate_response(rsp)

        # Response format: address(1) + function(1) + byte_count(1) + data(16) + crc(2) = 21 bytes
        if len(rsp) < 21:
            raise ModbusException(f"Response too short: {rsp.hex()}")

        outputs = []
        for i in range(8):
            offset = 3 + i * 2
            value = int.from_bytes(rsp[offset : offset + 2], byteorder="big")
            outputs.append(value)

        logger.debug(f"Channel outputs (uA): {outputs}")
        return outputs

    def set_channel_output(self, channel: int, value_uA: int) -> None:
        """Set the analog output value for a single channel.

        Args:
            channel: Channel number (1-8).
            value_uA: Output value in microamperes (uA).

        Raises:
            ValueError: If channel or value_uA is out of valid range.
            ModbusException: If communication with the device fails.
        """
        if not 1 <= channel <= 8:
            raise ValueError("Channel must be 1-8")

        self._validate_output(value_uA)

        register_addr = 0x0000 + (channel - 1)
        msg = bytes.fromhex(f"{self._address:02X} 06 {register_addr:04X} {value_uA:04X}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting channel {channel} output to {value_uA} uA: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set channel output response: {rsp.hex()}")

        validate_response(rsp)

        logger.info(f"Channel {channel} output set to {value_uA} uA")

    def set_all_channels_output(self, value_uA: int | Sequence[int]) -> None:
        """Set analog output values for all channels.

        Args:
            value_uA: Single output value for all channels or list of 8 values
                for channels 1-8.

        Raises:
            ValueError: If output values are out of range or list length is invalid.
            TypeError: If value_uA is not int or Sequence[int].
            ModbusException: If communication with the device fails.
        """
        if isinstance(value_uA, int):
            self._validate_output(value_uA)
            resolved_outputs = [value_uA] * 8
        elif isinstance(value_uA, Sequence) and not isinstance(value_uA, (str, bytes, bytearray)):
            if len(value_uA) != 8:
                raise ValueError("Outputs must contain exactly 8 values")

            for value in value_uA:
                self._validate_output(value)
            resolved_outputs = list(value_uA)
        else:
            raise TypeError("value_uA must be int or Sequence[int]")

        output_bytes = " ".join(f"{value:04X}" for value in resolved_outputs)
        msg = bytes.fromhex(f"{self._address:02X} 10 00 00 00 08 10 {output_bytes}")
        msg += compute_CRC(msg)
        logger.debug(f"Setting all channel outputs: {msg.hex()}")
        self.serial.write(msg)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Set all channels output response: {rsp.hex()}")

        validate_response(rsp)

        logger.info(f"All channel outputs set (ch1-ch8, uA): {resolved_outputs}")