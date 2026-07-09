# Waveshare Modbus RTU Digital IO - Support Documentation

## Overview

This document describes the implementation of support for the **Waveshare Modbus RTU Digital IO** device (IO 8CH) - a digital input/output module with 8 digital inputs (DI) and 8 digital outputs (DO).

**Module Path:** `wavesharertu.devices.digital_io`

## Device Specifications

- **Digital Inputs:** 8 channels (5-36V, passive/active NPN/PNP)
- **Digital Outputs:** 8 channels (5-40V, open-drain, max 500mA per channel)
- **Communication:** RS485 Modbus RTU Protocol
- **Default Address:** 1 (configurable via commands)
- **Default Baudrate:** 9600
- **Default Parity:** None

## Module Components

### 1. `DigitalIO` Class

Main device interface class located in `io.py`.

#### Key Methods

**Reading Status:**
- `read_digital_inputs()` → List[bool]: Read all 8 input channel states
- `read_digital_outputs()` → List[bool]: Read all 8 output channel states
- `read_output_control_modes()` → List[DigitalOutputMode]: Read control modes for all outputs

**Output Control (Single Channel):**
- `set_output_channel(channel: int, state: bool)`: Turn a single output ON/OFF
- `toggle_output_channel(channel: int)`: Toggle a single output

**Output Control (Multiple Channels):**
- `set_all_outputs(state: bool)`: Set all outputs to same state (ON/OFF)
- `set_outputs_by_mask(mask: int)`: Control outputs using 8-bit bitmask (bit 0 = CH1, bit 1 = CH2, etc.)

**Mode Control:**
- `set_output_control_mode(channel: int, mode: DigitalOutputMode)`: Set control mode for single channel
- `set_all_output_control_modes(mode: DigitalOutputMode)`: Set same control mode for all channels

### 2. `DigitalOutputMode` Enum

Control modes for output channels:

- **NORMAL** (0x0000): Direct control via commands
- **LINKAGE** (0x0001): Output follows corresponding input
- **TOGGLE** (0x0002): Output toggles on each input pulse
- **EDGE_TRIGGER** (0x0003): Output changes on input level change

## Modbus Protocol Details

### Function Codes Used

| Code | Name | Usage |
|------|------|-------|
| 0x01 | Read Coils | Read output channel status |
| 0x02 | Read Discrete Inputs | Read input channel status |
| 0x03 | Read Holding Registers | Read output control modes |
| 0x05 | Write Single Coil | Control single output |
| 0x06 | Write Single Register | Set single output mode |
| 0x0F | Write Multiple Coils | Control multiple outputs |
| 0x10 | Write Multiple Registers | Set multiple output modes |

### Register Map

| Address | Function | Range | Description |
|---------|----------|-------|-------------|
| 0x0000-0x0007 | 0x01, 0x05, 0x0F | 8 channels | Output channels 1-8 control |
| 0x00FF | 0x05 | N/A | Control all outputs at once |
| 0x1x0000-0x1x0007 | 0x02 | 8 channels | Input channels 1-8 status |
| 0x4x1000-0x4x1007 | 0x03, 0x06, 0x10 | 8 channels | Output control modes 1-8 |

## Usage Examples

### Basic Usage

```python
from serial.rs485 import RS485, RS485Settings
from wavesharertu.devices.io_8ch import DigitalIO

# Open serial port
with RS485(port='COM3', baudrate=9600, parity='N') as serial_port:
    serial_port.rs485_mode = RS485Settings(delay_before_rx=0.5)
    
    # Initialize device at address 1
    device = DigitalIO(serial_port, address=1)
    
    # Read current status
    inputs = device.read_digital_inputs()
    outputs = device.read_digital_outputs()
    
    print(f"Inputs: {inputs}")
    print(f"Outputs: {outputs}")
    
    # Control outputs
    device.set_output_channel(1, True)   # Turn on CH1
    device.set_output_channel(2, False)  # Turn off CH2
    device.set_all_outputs(False)        # Turn off all
    device.toggle_output_channel(3)      # Toggle CH3
    
    # Control outputs with bitmask (CH1 and CH3 on, others off)
    device.set_outputs_by_mask(0b00000101)
    
    # Set control mode
    from wavesharertu.devices.io_8ch import DigitalOutputMode
    device.set_output_control_mode(1, DigitalOutputMode.LINKAGE)
```

### Interactive CLI

The device includes a user-friendly CLI for interactive control:

```bash
# Show help
python -m wavesharertu.devices.digital_io --help

# Connect to device
python -m wavesharertu.devices.digital_io COM3 1 -b 9600 -p N

# Options:
#   -b, --baudrate    Serial baudrate (default: 9600)
#   -p, --parity      Parity: N (None), E (Even), O (Odd)
#   -l, --log_level   Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**CLI Menu Options:**
1. Show current IO status
2. Set single output channel
3. Set all outputs
4. Set outputs by bitmask
5. Toggle output channel
6. Set output control mode
7. Monitor IO in real-time
8. Exit

### Reading Analog Inputs in a Loop

```python
from time import monotonic, sleep

device = DigitalIO(serial_port, address=1)

print("Starting IO monitoring. Press Ctrl+C to stop.")
try:
    while True:
        inputs = device.read_digital_inputs()
        outputs = device.read_digital_outputs()
        
        input_str = ", ".join(f"CH{i+1}: {'ON' if s else 'OFF'}" for i, s in enumerate(inputs))
        output_str = ", ".join(f"CH{i+1}: {'ON' if s else 'OFF'}" for i, s in enumerate(outputs))
        
        print(f"Inputs: {input_str} | Outputs: {output_str}")
        sleep(0.1)
except KeyboardInterrupt:
    print("Monitoring stopped.")
```

## Testing

Unit tests for the device are included in `tests/test_digital_io.py`:

```bash
python -m pytest tests/test_digital_io.py -v
```

Tests cover:
- Enum values and readable names
- Device initialization
- Reading input/output status
- Setting outputs (single, all, by mask)
- Toggling outputs
- Invalid input validation

## Error Handling

The module raises `ModbusException` and its subclasses for communication errors:

```python
from wavesharertu.modbus import ModbusException

try:
    inputs = device.read_digital_inputs()
except ModbusException as e:
    print(f"Device communication error: {e}")
```

## Implementation Notes

- **Channel Numbering:** Channels are 1-indexed (1-8) in the API but 0-indexed internally
- **Bitmask Format:** LSB first (bit 0 = CH1, bit 7 = CH8)
- **Serial Timeout:** Use `RS485Settings(delay_before_rx=0.5)` for reliable communication
- **CRC:** All Modbus commands include CRC16 checksum (handled automatically)
- **Modbus Format:** Standard Modbus RTU Protocol V2

## Device Wiring

### Power Supply
- Voltage: 7-36V DC
- Positive (7-36V) → 7~36V terminal
- Negative (GND) → GND terminal

### RS485 Connection
- Device A+ → RS485 A+
- Device B- → RS485 B-
- Device EARTH → RS485 Shield (if shielded cable)

### Digital Inputs
- Supports dry-contact (passive), NPN (active low), or PNP (active high) inputs
- DI COM terminal configures input type

### Digital Outputs
- Open-drain outputs (max 500mA per channel)
- DO COM connects to positive pole of output power supply

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Device not responding | Check RS485 A/B connections, verify baud rate and address |
| CRC errors | Verify serial cable quality, check for EMI interference |
| Inputs not reading | Check DI COM terminal configuration and wiring |
| Outputs not switching | Verify output load is within 500mA limit per channel |

## Protocol Reference

See the Waveshare wiki for complete protocol documentation:
https://www.waveshare.com/wiki/Modbus_RTU_IO_8CH#Development_Protocol_V2

