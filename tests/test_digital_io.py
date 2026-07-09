"""Tests for Waveshare Modbus RTU Digital IO device."""

import pytest
from unittest.mock import Mock, MagicMock

from wavesharertu.devices.digital_io import DigitalIO, DigitalOutputMode
from wavesharertu.modbus import ModbusException, compute_CRC


def test_digital_output_mode_enum():
    """Test that DigitalOutputMode enum has correct values."""
    assert DigitalOutputMode.NORMAL == 0x0000
    assert DigitalOutputMode.LINKAGE == 0x0001
    assert DigitalOutputMode.TOGGLE == 0x0002
    assert DigitalOutputMode.EDGE_TRIGGER == 0x0003


def test_digital_output_mode_readable_names():
    """Test that DigitalOutputMode has readable names."""
    assert DigitalOutputMode.NORMAL.readable_name() == "Normal mode (direct control)"
    assert DigitalOutputMode.LINKAGE.readable_name() == "Linkage mode (follows input)"
    assert DigitalOutputMode.TOGGLE.readable_name() == "Toggle mode (toggles on input pulse)"
    assert DigitalOutputMode.EDGE_TRIGGER.readable_name() == "Edge trigger mode (changes on input level change)"


def test_digital_io_initialization():
    """Test DigitalIO initialization."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    device = DigitalIO(mock_serial, address=1)

    assert device.serial == mock_serial
    assert device._address == 1


def test_read_digital_inputs_valid_response():
    """Test reading digital inputs with valid response."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    # Mock response: address(01) + function(02) + byte_count(01) + status(55) + crc(2 bytes)
    status_byte = 0x55  # Binary: 01010101 (alternating on/off pattern)
    response = bytes([0x01, 0x02, 0x01, status_byte])
    response += compute_CRC(response)

    mock_serial.read.return_value = response
    mock_serial.in_waiting = len(response)

    device = DigitalIO(mock_serial, address=1)
    inputs = device.read_digital_inputs()

    # Status byte 0x55 = 01010101: CH1=ON, CH2=OFF, CH3=ON, CH4=OFF, CH5=ON, CH6=OFF, CH7=ON, CH8=OFF
    expected = [True, False, True, False, True, False, True, False]
    assert inputs == expected


def test_read_digital_outputs_valid_response():
    """Test reading digital outputs with valid response."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    # Mock response: address(01) + function(01) + byte_count(01) + status(AA) + crc(2 bytes)
    status_byte = 0xAA  # Binary: 10101010 (alternating off/on pattern)
    response = bytes([0x01, 0x01, 0x01, status_byte])
    response += compute_CRC(response)

    mock_serial.read.return_value = response
    mock_serial.in_waiting = len(response)

    device = DigitalIO(mock_serial, address=1)
    outputs = device.read_digital_outputs()

    # Status byte 0xAA = 10101010: CH1=OFF, CH2=ON, CH3=OFF, CH4=ON, CH5=OFF, CH6=ON, CH7=OFF, CH8=ON
    expected = [False, True, False, True, False, True, False, True]
    assert outputs == expected


def test_set_output_channel_on():
    """Test setting a single output channel to ON."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    # Mock response for successful command
    response = bytes([0x01, 0x05, 0x00, 0x00, 0xFF, 0x00])
    response += compute_CRC(response)
    mock_serial.read.return_value = response
    mock_serial.in_waiting = len(response)

    device = DigitalIO(mock_serial, address=1)
    device.set_output_channel(1, True)

    # Verify write was called
    assert mock_serial.write.called
    written_msg = mock_serial.write.call_args[0][0]
    # Message should be: 01 05 00 00 FF 00 + CRC
    assert written_msg[:6] == bytes.fromhex("01 05 00 00 FF 00")


def test_set_output_channel_off():
    """Test setting a single output channel to OFF."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    # Mock response for successful command
    response = bytes([0x01, 0x05, 0x00, 0x00, 0x00, 0x00])
    response += compute_CRC(response)
    mock_serial.read.return_value = response
    mock_serial.in_waiting = len(response)

    device = DigitalIO(mock_serial, address=1)
    device.set_output_channel(1, False)

    # Verify write was called
    assert mock_serial.write.called
    written_msg = mock_serial.write.call_args[0][0]
    # Message should be: 01 05 00 00 00 00 + CRC
    assert written_msg[:6] == bytes.fromhex("01 05 00 00 00 00")


def test_set_output_channel_invalid_channel():
    """Test that invalid channel number raises ValueError."""
    mock_serial = Mock()
    device = DigitalIO(mock_serial, address=1)

    with pytest.raises(ValueError, match="Channel must be 1-8"):
        device.set_output_channel(0, True)

    with pytest.raises(ValueError, match="Channel must be 1-8"):
        device.set_output_channel(9, True)


def test_toggle_output_channel():
    """Test toggling a single output channel."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    # Mock response for successful command
    response = bytes([0x01, 0x05, 0x00, 0x00, 0x55, 0x00])
    response += compute_CRC(response)
    mock_serial.read.return_value = response
    mock_serial.in_waiting = len(response)

    device = DigitalIO(mock_serial, address=1)
    device.toggle_output_channel(1)

    # Verify write was called
    assert mock_serial.write.called
    written_msg = mock_serial.write.call_args[0][0]
    # Message should be: 01 05 00 00 55 00 + CRC
    assert written_msg[:6] == bytes.fromhex("01 05 00 00 55 00")


def test_set_all_outputs():
    """Test setting all outputs to same state."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    # Mock response for successful command
    response = bytes([0x01, 0x05, 0x00, 0xFF, 0xFF, 0x00])
    response += compute_CRC(response)
    mock_serial.read.return_value = response
    mock_serial.in_waiting = len(response)

    device = DigitalIO(mock_serial, address=1)
    device.set_all_outputs(True)

    # Verify write was called
    assert mock_serial.write.called
    written_msg = mock_serial.write.call_args[0][0]
    # Message should be: 01 05 00 FF FF 00 + CRC
    assert written_msg[:6] == bytes.fromhex("01 05 00 FF FF 00")


def test_set_outputs_by_mask():
    """Test setting outputs using a bitmask."""
    mock_serial = Mock()
    mock_serial.port = "COM3"

    # Mock response for successful command
    response = bytes([0x01, 0x0F, 0x00, 0x00, 0x00, 0x08])
    response += compute_CRC(response)
    mock_serial.read.return_value = response
    mock_serial.in_waiting = len(response)

    device = DigitalIO(mock_serial, address=1)
    device.set_outputs_by_mask(0x0F)  # First 4 channels on

    # Verify write was called
    assert mock_serial.write.called
    written_msg = mock_serial.write.call_args[0][0]
    # Message should start with: 01 0F 00 00 00 08 01 0F
    assert written_msg[:8] == bytes.fromhex("01 0F 00 00 00 08 01 0F")


def test_set_outputs_by_mask_invalid():
    """Test that invalid mask raises ValueError."""
    mock_serial = Mock()
    device = DigitalIO(mock_serial, address=1)

    with pytest.raises(ValueError, match="Mask must be 0-255"):
        device.set_outputs_by_mask(256)

    with pytest.raises(ValueError, match="Mask must be 0-255"):
        device.set_outputs_by_mask(-1)
