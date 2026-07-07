# WaveshareRTU

## Description

A Python library and tools for working with Waveshare devices supporting the Modbus RTU protocol. WaveshareRTU provides functionality for configuring device connection parameters (Modbus address, baud rate, parity) as well as communicating with and controlling Waveshare devices.

The program automatically scans available baud rate and parity combinations to find connected devices and can be integrated into other projects for practical device utilization.

## Supported Devices

- [Modbus RTU Analog Input 8CH](https://www.waveshare.com/wiki/Modbus_RTU_Analog_Input_8CH)
- [Modbus RTU Analog Output 8CH](https://www.waveshare.com/wiki/Modbus_RTU_Analog_Output_8CH)
- [Modbus RTU IO 8CH](https://www.waveshare.com/wiki/Modbus_RTU_IO_8CH)

The program should work with other Waveshare devices that support the Modbus RTU protocol.

## Installation

### Prerequisites

- Python 3.14 or higher
- [Poetry](https://python-poetry.org/) for package management
- Serial port connection to a Waveshare device

### Install with Poetry (recommended)

Clone the repository and install the package using Poetry:

```bash
git clone <repository-url>
cd wavesharertu
poetry install
```

### Install from source with pip

Clone the repository and install the package with pip:

```bash
git clone <repository-url>
cd wavesharertu
pip install -e .
```

## Tools

The WaveshareRTU package includes several command-line tools that serve as both practical utilities and examples of how to use the library in your own projects:

- [wavesharertu.config](src/wavesharertu/config/__main__.py) - Configure Modbus address, baud rate, and parity settings
- [wavesharertu.devices.analog_input](src/wavesharertu/devices/analog_input/__main__.py) - Read analog values and configure channel modes for Analog Input 8CH
- [wavesharertu.devices.analog_input_B](src/wavesharertu/devices/analog_input_B/__main__.py) - Read analog values and configure channel modes for Analog Input 8CH (B)

**Important:** Run the following commands in the Python environment where the module is installed.

### Activating the Poetry environment

If you installed the package with Poetry, activate the virtual environment:

**On Linux/macOS:**

```bash
eval $(poetry env activate)
```

**On Windows (PowerShell):**

```powershell
Invoke-Expression (poetry env activate)
```

Alternatively, you can prefix commands with `poetry run`:

```bash
poetry run python -m <tool_name> <params>
```

### Configuration Tool

Run the configuration tool with:

```bash
python -m wavesharertu.config <port>
```

Replace `<port>` with your serial port (e.g., `/dev/ttyUSB0` on Linux, `COM3` on Windows).

For more information, use the help option:

```bash
python -m wavesharertu.config -h
```

### Analog Input 8CH Tool

Run the Analog Input 8CH tool with:

```bash
python -m wavesharertu.devices.analog_input <port> <address>
```

Example:

```bash
python -m wavesharertu.devices.analog_input COM3 10 -b 9600 -p N
```

### Analog Input 8CH (B) Tool

Run the Analog Input 8CH (B) tool with:

```bash
python -m wavesharertu.devices.analog_input_B <port> <address>
```

Example:

```bash
python -m wavesharertu.devices.analog_input_B COM3 10 -b 9600 -p N
```
