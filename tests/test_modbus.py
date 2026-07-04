import pytest

from wavesharertu.modbus import (
    CRCException,
    InvalidResponseException,
    IllegalFunctionException,
    compute_CRC,
    validate_response,
)


def test_validate_response_valid():
    message_data = bytes([0x01, 0x03, 0x02, 0x00, 0x01])
    response = message_data + compute_CRC(message_data)

    assert validate_response(response) is None


def test_validate_response_invalid_crc_raises_crc_exception():
    response = bytes([0x01, 0x03, 0x02, 0x00, 0x01, 0x00, 0x00])

    with pytest.raises(CRCException) as excinfo:
        validate_response(response)

    assert "CRC mismatch" in str(excinfo.value)
    assert "response" in str(excinfo.value)
    assert response.hex() in str(excinfo.value)


def test_validate_response_error_response_raises_specific_exception():
    error_payload = bytes([0x01, 0x83, 0x01])
    response = error_payload + compute_CRC(error_payload)

    with pytest.raises(IllegalFunctionException) as excinfo:
        validate_response(response)

    assert "exception code 0x01" in str(excinfo.value)
    assert "response" in str(excinfo.value)
    assert response.hex() in str(excinfo.value)


def test_validate_response_invalid_error_response_length_raises_invalid_response_exception():
    response = bytes([0x01, 0x83, 0x41, 0x81])

    with pytest.raises(InvalidResponseException) as excinfo:
        validate_response(response)

    assert "Invalid error response length" in str(excinfo.value)
    assert "response" in str(excinfo.value)
    assert response.hex() in str(excinfo.value)
