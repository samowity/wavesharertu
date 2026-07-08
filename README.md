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
- [wavesharertu.devices.analog_output](src/wavesharertu/devices/analog_output/__main__.py) - Interactively control output current values for Analog Output 8CH
- [wavesharertu.devices.ao_ai_loopback](src/wavesharertu/devices/ao_ai_loopback/__main__.py) - Interactively set AO outputs and read AI inputs on one RS485 bus

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

The tool scans baudrate/parity combinations to find a device, then lets you interactively read and update Modbus address and communication settings.
You can narrow the number of tested combinations by providing baudrate and/or parity values.

### Analog Input 8CH Tool

Run the Analog Input 8CH tool with:

```bash
python -m wavesharertu.devices.analog_input <port> <address>
```

Example:

```bash
python -m wavesharertu.devices.analog_input COM3 10 -b 9600 -p N
```

After startup, the tool connects to the device, displays current channel modes, and offers interactive mode configuration (all channels at once or channel-by-channel).

### Analog Input 8CH (B) Tool

Run the Analog Input 8CH (B) tool with:

```bash
python -m wavesharertu.devices.analog_input_B <port> <address>
```

Example:

```bash
python -m wavesharertu.devices.analog_input_B COM3 10 -b 9600 -p N
```

This tool works the same way as the Analog Input 8CH tool described above.

### Analog Output 8CH Tool

Run the Analog Output 8CH interactive tool with:

```bash
python -m wavesharertu.devices.analog_output <port> <address>
```

Example:

```bash
python -m wavesharertu.devices.analog_output COM3 10 -b 9600 -p N
```

After startup, the tool reads and displays the current output values for channels 1-8, then enters an interactive loop where you can set a single value for all channels or set a value for an individual channel.

### AO->AI Loopback Interactive Tool

Run the interactive loopback tool with:

```bash
python -m wavesharertu.devices.ao_ai_loopback <port> <ao_address> <ai_address>
```

Example:

```bash
python -m wavesharertu.devices.ao_ai_loopback COM3 25 10 -b 115200 -p N --settle-ms 500
```

This tool is intended for a hardware loopback setup where analog outputs are physically connected to analog inputs (for example AO CH1 -> AI CH1).
After startup the script sets all AI channels to 0-20 mA mode, shows current AO and AI values, and enters an interactive loop:

- Enter `1-8` to choose a single AO channel and set its value.
- Enter `0` to set the same value for all AO channels.
- Press Enter on an empty prompt to only read and display current AI values.

After each value change, the script displays AO outputs, reads AI inputs, and prompts again.
