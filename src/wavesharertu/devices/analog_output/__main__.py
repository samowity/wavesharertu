"""CLI for Waveshare Modbus RTU Analog Output 8CH device."""

import argparse
import logging
import sys

from serial import SerialException
from serial.rs485 import RS485, RS485Settings

from ...config.cli import prompt_user_choice
from ...modbus import ModbusException
from .ao import AnalogOutput


def _show_current_channel_outputs(device: AnalogOutput) -> None:
    channel_outputs = device.read_channel_outputs()
    output_details = ",".join(f"\n\tCH{index}: {value} uA" for index, value in enumerate(channel_outputs, start=1))
    logging.info("Current channel outputs:%s", output_details)


def _set_all_channels_output(device: AnalogOutput) -> None:
    value_uA = int(
        prompt_user_choice(
            "Enter output current for all channels in uA",
            range(0, 20001),
        )
    )
    device.set_all_channels_output(value_uA)
    logging.info("All channels set to %s uA.", value_uA)


def _set_single_channel_output(device: AnalogOutput, channel: int) -> None:
    value_uA = int(
        prompt_user_choice(
            f"Enter output current for CH{channel} in uA",
            range(0, 20001),
        )
    )
    device.set_channel_output(channel, value_uA)
    logging.info("CH%s set to %s uA.", channel, value_uA)


def _interactive_control_loop(device: AnalogOutput) -> None:
    logging.info("Interactive control started. Press Ctrl+C to exit.")
    while True:
        channel = int(prompt_user_choice("Choose output channel (1-8) or 0 for all", range(0, 9)))

        if channel == 0:
            _set_all_channels_output(device)
        else:
            _set_single_channel_output(device, channel)

        _show_current_channel_outputs(device)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wavesharertu.devices.analog_output",
        description="Control Waveshare Modbus RTU Analog Output 8CH parameters.",
    )
    parser.add_argument("port", type=str, help="Serial port address (for example COM3).")
    parser.add_argument("address", type=int, help="Device Modbus address (1-255).")
    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=9600,
        help="Serial baudrate (default: 9600).",
    )
    parser.add_argument(
        "-p",
        "--parity",
        choices=["N", "E", "O"],
        type=str.upper,
        default="N",
        help="Serial parity (default: N).",
    )
    parser.add_argument(
        "-l",
        "--log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        type=str.upper,
        default="INFO",
        help="Logging level (default: INFO).",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
    )

    logging.info(
        "Analog Output 8CH connection parameters:\n\tPort=%s,\n\tAddress=%s,\n\tBaudrate=%s,\n\tParity=%s.",
        args.port,
        args.address,
        args.baudrate,
        args.parity,
    )

    try:
        with RS485(port=args.port, baudrate=args.baudrate, parity=args.parity) as serial_port:
            serial_port.rs485_mode = RS485Settings(delay_before_rx=0.5)
            device = AnalogOutput(serial_port, address=args.address)

            try:
                _show_current_channel_outputs(device)
            except ModbusException as exc:
                logging.error("Failed to communicate with device. Check connection and parameters. Error: %s", exc)
                return 1

            _interactive_control_loop(device)

    except (ValueError, SerialException) as exc:
        logging.error(exc)
        return 1
    except KeyboardInterrupt:
        logging.info("Operation interrupted by user (Ctrl+C).")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
