"""CLI for Waveshare Modbus RTU Analog Input 8CH (B) device."""

import argparse
import logging
import sys
from time import monotonic

from serial import SerialException
from serial.rs485 import RS485, RS485Settings

from ...config.cli import prompt_user_choice
from ...modbus import ModbusException
from .ai_b import AnalogInputB, AnalogInputModeB


def _set_mode_for_all_channels(device: AnalogInputB) -> None:
    available_modes = list(AnalogInputModeB)
    print("Available modes:")
    for index, mode in enumerate(available_modes, start=1):
        print(f"  {index}. {mode.readable_name()}")

    selected_index = int(
        prompt_user_choice(
            "Choose mode number for all channels",
            range(1, len(available_modes) + 1),
        )
    )

    mode = available_modes[selected_index - 1]
    device.set_all_channels_mode(mode)
    logging.info("All channels set to %s.", mode.readable_name())


def _set_modes_for_each_channel(device: AnalogInputB) -> None:
    available_modes = list(AnalogInputModeB)
    print("Available modes:")
    for index, mode in enumerate(available_modes, start=1):
        print(f"  {index}. {mode.readable_name()}")

    selected_modes = []
    for channel in range(1, 9):
        selected_index = int(
            prompt_user_choice(
                f"Choose mode number for CH{channel}",
                range(1, len(available_modes) + 1),
            )
        )
        selected_modes.append(available_modes[selected_index - 1])

    device.set_all_channels_mode(selected_modes)
    logging.info("All channel modes set individually.")


def _show_current_channel_modes(device: AnalogInputB) -> None:
    channel_modes = device.read_channel_modes()
    mode_details = ",".join(f"\n\tCH{index}: {mode.readable_name()}" for index, mode in enumerate(channel_modes, start=1))
    logging.info("Current channel modes: %s.", mode_details)


def _fetch_values_in_loop(device: AnalogInputB) -> None:
    logging.info("Starting periodic value fetch. Press Ctrl+C to stop.")
    try:
        last_read_time = None
        while True:
            # fetch interval regulated by RS485Settings delay_before_rx, so no need to sleep here
            current_read_time = monotonic()
            try:
                values = device.read_analog_inputs()
            except ModbusException as exc:
                logging.error("Failed to fetch analog values. Error: %s", exc)
                return

            value_details = ", ".join(f"CH{index}: {value}" for index, value in enumerate(values, start=1))
            if last_read_time is None:
                logging.info("Analog readings: %s", value_details)
            else:
                logging.info("Analog readings: %s ", value_details)
                logging.debug("Time since last read: %.3f s", current_read_time - last_read_time)
            last_read_time = current_read_time
    except KeyboardInterrupt:
        logging.info("Value fetching stopped by user (Ctrl+C).")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wavesharertu.devices.analog_input_B",
        description="Read analog values and configure Waveshare Modbus RTU Analog Input 8CH (B) parameters.",
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
        "Analog Input 8CH (B) connection parameters:\n\tPort=%s,\n\tAddress=%s,\n\tBaudrate=%s,\n\tParity=%s.",
        args.port,
        args.address,
        args.baudrate,
        args.parity,
    )
    try:
        with RS485(port=args.port, baudrate=args.baudrate, parity=args.parity) as serial_port:
            serial_port.rs485_mode = RS485Settings(delay_before_rx=0.5)
            device = AnalogInputB(serial_port, address=args.address)
            try:
                _show_current_channel_modes(device)
            except ModbusException as exc:
                logging.error("Failed to communicate with device. Check connection and parameters. Error: %s", exc)
                return 1

            change_modes = (
                prompt_user_choice(
                    "Do you want to change all channels at once?",
                    ["y", "n"],
                    allow_empty=True,
                )
                .strip()
                .lower()
            )
            if change_modes == "y":
                _set_mode_for_all_channels(device)
            else:
                change_individual_modes = (
                    prompt_user_choice(
                        "Do you want to change individually for each channel?",
                        ["y", "n"],
                        allow_empty=True,
                    )
                    .strip()
                    .lower()
                )
                if change_individual_modes == "y":
                    _set_modes_for_each_channel(device)

            fetch_interval_ms = prompt_user_choice(
                "How often should values be fetched in milliseconds? (leave empty to skip)",
                range(0, 10001),
                allow_empty=True,
            ).strip()
            if fetch_interval_ms:
                interval_s = (int(fetch_interval_ms) - 1) / 1000.0  # Subtract 1 ms include the time taken for the read operation itself.
                serial_port.rs485_mode = RS485Settings(delay_before_rx=interval_s)
                _fetch_values_in_loop(device)

    except (ValueError, SerialException) as exc:
        logging.error(exc)
        return 1
    except KeyboardInterrupt:
        logging.info("Operation interrupted by user (Ctrl+C).")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
