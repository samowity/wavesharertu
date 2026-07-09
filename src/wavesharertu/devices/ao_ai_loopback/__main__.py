"""CLI for AO->AI loopback verification on one RS485 port."""

import argparse
import logging
import sys
from time import sleep

from serial import SerialException
from serial.rs485 import RS485, RS485Settings

from ...config.cli import prompt_user_choice
from ...modbus import ModbusException
from ..analog_input import AnalogInput, AnalogInputMode
from ..analog_output import AnalogOutput


def _parse_address(value: str) -> int:
    address = int(value, 0)
    if not 1 <= address <= 255:
        raise argparse.ArgumentTypeError("Address must be in range 1-255")
    return address


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wavesharertu.devices.ao_ai_loopback",
        description="Interactively control AO and read AI on one RS485 bus.",
    )
    parser.add_argument("port", type=str, help="Serial port address (for example COM3).")
    parser.add_argument("ao_address", type=_parse_address, help="Analog Output Modbus address (1-255).")
    parser.add_argument("ai_address", type=_parse_address, help="Analog Input Modbus address (1-255).")
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
        "--settle-ms",
        type=int,
        default=500,
        help="Wait time after AO write before AI read in milliseconds (default: 500).",
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


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.ao_address == args.ai_address:
        parser.error("ao_address and ai_address must be different")

    if args.settle_ms < 0:
        parser.error("--settle-ms must be >= 0")


def _set_ai_current_mode_for_all_channels(ai_device: AnalogInput) -> None:
    ai_device.set_all_channels_mode(AnalogInputMode.CURRENT_0_20mA)
    logging.info(f"AI channels set to {AnalogInputMode.CURRENT_0_20mA.readable_name()}.")


def _format_channel_values(values: list[int]) -> str:
    return ", ".join(f"CH{index}: {value:>5} uA" for index, value in enumerate(values, start=1))


def _show_ao_values(ao_device: AnalogOutput) -> None:
    ao_values = ao_device.read_channel_outputs()
    logging.info("AO outputs: %s.", _format_channel_values(ao_values))


def _show_ai_values(ai_device: AnalogInput) -> None:
    ai_values = ai_device.read_analog_inputs()
    logging.info("AI inputs:  %s.", _format_channel_values(ai_values))


def _interactive_loop(ao_device: AnalogOutput, ai_device: AnalogInput, settle_ms: int) -> None:
    logging.info("Interactive mode started. Press Ctrl+C to exit.")
    while True:
        selected_channel = prompt_user_choice(
            "Choose channel to set (1-8), 0 for all channels, empty to read AI only",
            range(0, 9),
            allow_empty=True,
        ).strip()

        if selected_channel == "":
            _show_ai_values(ai_device)
            continue

        channel = int(selected_channel)
        value_uA = int(prompt_user_choice("Enter output current in uA", range(0, 20001)))

        if channel == 0:
            ao_device.set_all_channels_output(value_uA)
            logging.info("Set all AO channels to %s uA.", value_uA)
        else:
            ao_device.set_channel_output(channel, value_uA)
            logging.info("Set AO CH%s to %s uA.", channel, value_uA)

        _show_ao_values(ao_device)
        sleep(settle_ms / 1000.0)
        _show_ai_values(ai_device)


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    _validate_args(parser, args)

    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, args.log_level),
        format="%(levelname)s: %(message)s",
    )

    logging.info(
        "Loopback test parameters:\n\tPort=%s,\n\tAO address=%s,\n\tAI address=%s,\n\tBaudrate=%s,\n\tParity=%s," "\n\tSettle ms=%s.",
        args.port,
        args.ao_address,
        args.ai_address,
        args.baudrate,
        args.parity,
        args.settle_ms,
    )

    try:
        with RS485(port=args.port, baudrate=args.baudrate, parity=args.parity) as serial_port:
            serial_port.rs485_mode = RS485Settings(delay_before_rx=0.5)

            ao_device = AnalogOutput(serial_port, address=args.ao_address)
            ai_device = AnalogInput(serial_port, address=args.ai_address)

            _set_ai_current_mode_for_all_channels(ai_device)
            _show_ao_values(ao_device)
            _show_ai_values(ai_device)
            _interactive_loop(ao_device, ai_device, args.settle_ms)
    except (ValueError, SerialException, ModbusException) as exc:
        logging.error("Loopback test failed: %s", exc)
        return 1
    except KeyboardInterrupt:
        print()
        logging.info("Operation interrupted by user (Ctrl+C).")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
