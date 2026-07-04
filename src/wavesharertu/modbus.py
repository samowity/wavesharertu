from enum import Enum


class FunctionCode(Enum):
    ReadHoldingRegister = 0x03
    ReadInputRegister = 0x04
    WriteSingleHoldingRegister = 0x06
    WriteMultipleHoldingRegister = 0x10


class ExceptionCode(Enum):
    Illegal_Function = 0x01
    Illegal_Data_Address = 0x02
    Illegal_Data_Value = 0x03
    Server_Failure = 0x04
    Response = 0x05
    Device_Busy = 0x06


class ModbusException(Exception):
    """Base exception for all Modbus-related errors"""

    pass


class IllegalFunctionException(ModbusException):
    """Exception code 0x01 - Illegal Function"""

    pass


class IllegalDataAddressException(ModbusException):
    """Exception code 0x02 - Illegal Data Address"""

    pass


class IllegalDataValueException(ModbusException):
    """Exception code 0x03 - Illegal Data Value"""

    pass


class ServerFailureException(ModbusException):
    """Exception code 0x04 - Server Failure"""

    pass


class ResponseException(ModbusException):
    """Exception code 0x05 - Response"""

    pass


class DeviceBusyException(ModbusException):
    """Exception code 0x06 - Device Busy"""

    pass


class CRCException(ModbusException):
    """Exception for CRC (Cyclic Redundancy Check) errors"""

    pass


class InvalidResponseException(ModbusException):
    """Exception for malformed or invalid Modbus responses"""

    pass


def generate_crc16_table() -> list[int]:
    """Generate a crc16 lookup table.

    .. note:: This will only be generated once
    .. note:: Based on pymodbus library version 3.6.5 and earlier
    .. note:: https://github.com/pymodbus-dev/pymodbus/blob/779967e0f7c1438c37cf74a4a85bf8597486b23a/pymodbus/utilities.py#L155
    """
    result = []
    for byte in range(256):
        crc = 0x0000
        for _ in range(8):
            if (byte ^ crc) & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            byte >>= 1
        result.append(crc)
    return result


__crc16_table = generate_crc16_table()


def compute_CRC(message: bytes) -> bytes:
    """Compute a crc16 on the passed in bytes.

    The difference between modbus's crc16 and a normal crc16
    is that modbus starts the crc value out at 0xffff.

    .. note:: Based on pymodbus library version 3.6.5 and earlier
    .. note:: https://github.com/pymodbus-dev/pymodbus/blob/779967e0f7c1438c37cf74a4a85bf8597486b23a/pymodbus/utilities.py#L176

    :param data: The data to create a crc16 of
    :returns: The calculated CRC
    """
    crc = 0xFFFF
    for data_byte in message:
        idx = __crc16_table[(crc ^ int(data_byte)) & 0xFF]
        crc = ((crc >> 8) & 0xFF) ^ idx
    swapped = ((crc << 8) & 0xFF00) | ((crc >> 8) & 0x00FF)
    return swapped.to_bytes(2, "big")


def validate_response(response: bytes) -> None:
    """Validate a device response by checking CRC and error code.

    First validates the CRC checksum, then checks for error codes.
    If the response is valid, returns None. Otherwise raises appropriate exception.

    :param response: The complete response message from the device
    :raises CRCException: If CRC checksum is invalid
    :raises IllegalFunctionException: If exception code 0x01
    :raises IllegalDataAddressException: If exception code 0x02
    :raises IllegalDataValueException: If exception code 0x03
    :raises ServerFailureException: If exception code 0x04
    :raises ResponseException: If exception code 0x05
    :raises DeviceBusyException: If exception code 0x06
    :returns: None if response is valid
    """
    if not response:
        raise InvalidResponseException("Empty response received.")
    elif len(response) < 3:
        raise InvalidResponseException(f"Response too short: response {response.hex()!r}.")

    # Check CRC (last 2 bytes)
    message_data = response[:-2]
    received_crc = response[-2:]
    calculated_crc = compute_CRC(message_data)

    if received_crc != calculated_crc:
        raise CRCException(f"CRC mismatch: received {received_crc.hex()}, calculated {calculated_crc.hex()}, response {response.hex()!r}.")

    # Check for error code (bit 7 set in function code)
    function_code = response[1]
    if function_code & 0x80:  # Error flag set
        if len(response) < 5:  # Need at least: slave_id, func_code|0x80, exception_code, crc(2)
            raise InvalidResponseException(f"Invalid error response length: response {response.hex()!r}.")

        exception_code = response[2]

        exception_map = {
            0x01: (IllegalFunctionException, "Illegal Function"),
            0x02: (IllegalDataAddressException, "Illegal Data Address"),
            0x03: (IllegalDataValueException, "Illegal Data Value"),
            0x04: (ServerFailureException, "Server Failure"),
            0x05: (ResponseException, "Response"),
            0x06: (DeviceBusyException, "Device Busy"),
        }

        exception_class, exception_name = exception_map.get(exception_code, (ModbusException, "Unknown Exception"))
        raise exception_class(f"Device returned exception code 0x{exception_code:02x} ({exception_name}), response {response.hex()!r}.")
