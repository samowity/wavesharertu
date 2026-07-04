import logging
import sys
from serial import SerialException
from serial.rs485 import RS485
import argparse

from . import (
    DEFAULT_BAUDRATES,
    DEFAULT_PARITIES,
    configure_device_address,
    configure_device_baudrate,
    find_device,
    get_baudrate_parity_combinations,
)

parser = argparse.ArgumentParser(
    prog="wavesharemodbusrtu.config",
    description="Program to configure Waveshare Modbus RTU devices.",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""Supported devices:
  - Modbus RTU Analog Input 8CH
  - Modbus RTU Analog Output 8CH
  - Modbus RTU IO 8CH
  
Should work with other Waveshare devices that support the Modbus RTU protocol.""",
)
parser.add_argument("port", type=str, help="Serial port address.")
parser.add_argument("-b", "--baudrate", choices=["?", *(str(x) for x in DEFAULT_BAUDRATES)], type=str, default="?", help="Baud rate.")
parser.add_argument("-p", "--parity", choices=["?", *DEFAULT_PARITIES], type=str.upper, default="?", help="Parity.")
parser.add_argument(
    "-l", "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], type=str.upper, default="INFO", help="Logging level (default: INFO)."
)

args = parser.parse_args()

logging.basicConfig(
    stream=sys.stdout,
    level=getattr(logging, args.log_level.upper()),
    format="%(levelname)s: %(message)s",
)

brs_prs = get_baudrate_parity_combinations(args.baudrate, args.parity)


try:
    with RS485(port=args.port) as ser:
        try:
            device = find_device(ser, brs_prs)
        except RuntimeError as e:
            logging.error("No device found for the provided baudrate and parity. Please check if only one device is connected.")
            sys.exit(1)
        print()
        configure_device_address(device)
        print()
        configure_device_baudrate(device, ser)

except SerialException as e:
    logging.error(e)
