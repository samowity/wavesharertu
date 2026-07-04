import logging
from time import sleep
from typing import Literal


from ..modbus import compute_CRC, validate_response, ModbusException, InvalidResponseException, CRCException

logger = logging.getLogger(__name__)


class WaveshareRTUConfig:
    """Manages configuration of Waveshare Modbus RTU devices via serial port.

    This class provides methods to read and write device configuration parameters
    such as address, baudrate, and parity settings using Modbus RTU protocol.

    Tested with:
        - Modbus RTU Analog Input 8CH
        - Modbus RTU Analog Output 8CH
        - Modbus RTU IO 8CH

    Should work with other Waveshare devices that support the Modbus RTU protocol.
    """

    baudrate_codes = {
        4800: 0x00,
        9600: 0x01,
        19200: 0x02,
        38400: 0x03,
        57600: 0x04,
        115200: 0x05,
        128000: 0x06,
        256000: 0x07,
    }

    parity_codes = {
        "N": 0x00,
        "E": 0x01,
        "O": 0x02,
    }

    def __init__(self, serial, address=0x00):
        """Initialize WaveshareRTUConfig.

        Args:
            serial: RS485 serial port object.
            address: Device Modbus address (default: 0x00).
        """
        self.serial = serial
        self._address = address
        logger.debug(f"WaveshareRTUConfig initialized with address {self._address!r} and serial port {self.serial.port!r}.")

    def read_address(self) -> int:
        """Read the device's Modbus address.

        Returns:
            The current Modbus address of the device.

        Raises:
            ModbusException: If communication with the device fails.
        """
        msg = bytes.fromhex(f"{self._address:02X} 03 40 00 00 01")
        msg += compute_CRC(msg)
        logger.debug(f"Sending read address command: {msg.hex()}.")
        self.serial.write(msg)
        sleep(0.5)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Received response for read address: {rsp.hex()}.")
        validate_response(rsp)
        self._address = int.from_bytes(rsp[3:5], byteorder="big", signed=False)
        logger.debug(f"Device address read as {self._address!r}.")
        return self._address

    def set_address(self, address: int) -> int:
        """Set the device's Modbus address.

        Args:
            address: New Modbus address (1-255).

        Returns:
            The address that was set on the device.

        Raises:
            ModbusException: If communication with the device fails.
        """
        if address == 0:
            self._address = 0
            return 0
        msg = bytes.fromhex(f"{self._address:02X} 06 40 00 {address:04X}")
        msg += compute_CRC(msg)
        logger.debug(f"Sending set address command: {msg.hex()}.")
        self.serial.write(msg)
        sleep(0.5)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Received response for set address: {rsp.hex()}.")
        validate_response(rsp)
        self._address = int.from_bytes(rsp[4:6], byteorder="big", signed=False)
        logger.debug(f"Device address set to {self._address!r}.")

        return self._address

    def read_software_version(self) -> str:
        """Read the device's software version.

        Returns:
            Software version string in format 'VX.XX'.

        Raises:
            ModbusException: If communication with the device fails.
        """
        msg = bytes.fromhex(f"{self._address:02X} 03 80 00 00 01")
        msg += compute_CRC(msg)
        logger.debug(f"Sending read software version command: {msg.hex()}.")
        self.serial.write(msg)
        sleep(0.5)
        rsp = self.serial.read(self.serial.in_waiting)
        logger.debug(f"Received response for read software version: {rsp.hex()}.")
        validate_response(rsp)
        ver = int.from_bytes(rsp[3:5], byteorder="big", signed=False)
        ver = f"V{ver//100}.{ver%100}"
        logger.debug(f"Software version read as {ver!r}.")
        return ver

    def set_baudrate(self, baudrate: Literal[4800, 9600, 19200, 38400, 57600, 115200, 128000, 256000], parity: Literal["N", "E", "O"] = "N"):
        """Set the device's baudrate and parity.

        Args:
            baudrate: Desired baudrate (4800, 9600, 19200, 38400, 57600, 115200, 128000, or 256000).
            parity: Desired parity ('N' for none, 'E' for even, 'O' for odd). Default is 'N'.

        Raises:
            ValueError: If invalid baudrate or parity is provided.
            ModbusException: If communication with the device fails or verification fails.
        """
        try:
            br_code = self.baudrate_codes[baudrate]
        except KeyError:
            raise ValueError(f"Invalid baudrate: {baudrate!r}. Valid options are: {list(self.baudrate_codes.keys())}.")
        try:
            p_code = self.parity_codes[parity]
        except KeyError:
            raise ValueError(f"Invalid parity: {parity!r}. Valid options are: {list(self.parity_codes.keys())}.")

        msg = bytes.fromhex(f"{self._address:02X} 06 20 00 {p_code:02X} {br_code:02X}")
        msg += compute_CRC(msg)

        old_baudrate = self.serial.baudrate
        old_parity = self.serial.parity
        logger.debug(f"Sending set baudrate/parity command: {msg.hex()}.")
        self.serial.write(msg)
        sleep(0.25)
        rsp = self.serial.read(self.serial.in_waiting)
        try:
            validate_response(rsp)
        except (InvalidResponseException, CRCException) as e:
            logger.debug("Expected unreadable response after changing baudrate/parity on device %s: %s", self._address, e)
            pass
        except ModbusException as e:
            logger.error("Modbus error while setting baudrate/parity: %s", e)
            raise

        # Change baudrate and parity to the new values so we can verify the device responds.
        logger.debug(f"Changing serial port settings to baudrate={baudrate!r}, parity={parity!r}.")
        self.serial.baudrate = baudrate
        self.serial.parity = parity
        # Wait a moment to allow the device to switch to the new baudrate/parity.
        sleep(0.25)

        try:
            self.read_software_version()
        except ModbusException as e:
            logger.error("Failed to verify device after baudrate/parity change: %s", e)
            # restore old baudrate and parity
            self.serial.baudrate = old_baudrate
            self.serial.parity = old_parity
            raise
