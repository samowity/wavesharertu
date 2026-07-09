"""CLI for Waveshare Modbus RTU Digital IO device."""

import argparse
import logging
import sys
from time import monotonic

from serial import SerialException
from serial.rs485 import RS485, RS485Settings

from ...config.cli import prompt_user_choice
from ...modbus import ModbusException
from .io import DigitalIO, DigitalOutputMode


def _show_current_io_status(device: DigitalIO) -> None:
    """Display current status of inputs and outputs."""
    try:
        inputs = device.read_digital_inputs()
        outputs = device.read_digital_outputs()
        modes = device.read_output_control_modes()

        input_details = ", ".join(f"CH{i+1}: {'ON' if state else 'OFF'}" for i, state in enumerate(inputs))
        output_details = ", ".join(f"CH{i+1}: {'ON' if state else 'OFF'}" for i, state in enumerate(outputs))
        mode_details = ", ".join(f"CH{i+1}: {mode.readable_name()}" for i, mode in enumerate(modes))

        logging.info(f"Digital Inputs: {input_details}")
        logging.info(f"Digital Outputs: {output_details}")
        logging.info(f"Output Control Modes: {mode_details}")
    except ModbusException as exc:
        logging.error(f"Failed to read IO status. Error: {exc}")
        raise


def _set_control_mode_all_channels(device: DigitalIO) -> None:
    """Set the same control mode for all output channels."""
    available_modes = list(DigitalOutputMode)
    print("Available output control modes:")
    for index, mode in enumerate(available_modes, start=1):
        print(f"  {index}. {mode.readable_name()}")

    selected_index = int(
        prompt_user_choice(
            "Choose mode number for all output channels",
            range(1, len(available_modes) + 1),
        )
    )

    mode = available_modes[selected_index - 1]
    device.set_all_output_control_modes(mode)
    logging.info(f"All output channels set to {mode.readable_name()} mode.")


def _set_output_channel_state(device: DigitalIO) -> None:
    """Set the state of a single output channel."""
    channel = int(
        prompt_user_choice(
            "Which channel to control? (1-8)",
            range(1, 9),
        )
    )

    state_choice = (
        prompt_user_choice(
            f"Set channel {channel} to ON or OFF?",
            ["on", "off"],
            allow_empty=False,
        )
        .strip()
        .lower()
    )

    state = state_choice == "on"
    device.set_output_channel(channel, state)
    logging.info(f"Channel {channel} set to {'ON' if state else 'OFF'}.")


def _set_all_outputs(device: DigitalIO) -> None:
    """Set all output channels to the same state."""
    state_choice = (
        prompt_user_choice(
            "Set all channels to ON or OFF?",
            ["on", "off"],
            allow_empty=False,
        )
        .strip()
        .lower()
    )

    state = state_choice == "on"
    device.set_all_outputs(state)
    logging.info(f"All output channels set to {'ON' if state else 'OFF'}.")


def _set_outputs_by_mask(device: DigitalIO) -> None:
    """Set output channels using a bitmask."""
    mask_input = prompt_user_choice(
        "Enter bitmask as decimal (0-255) or hex (0x00-0xFF)",
        range(0, 256),
        allow_empty=False,
    ).strip()

    try:
        if mask_input.lower().startswith("0x"):
            mask = int(mask_input, 16)
        else:
            mask = int(mask_input)
    except ValueError:
        logging.error("Invalid mask value")
        return

    if not 0 <= mask <= 255:
        logging.error("Mask must be 0-255")
        return

    device.set_outputs_by_mask(mask)
    channels_on = [i + 1 for i in range(8) if (mask >> i) & 1]
    logging.info(f"Output channels set. Channels ON: {channels_on if channels_on else 'none'}")


def _toggle_output_channel(device: DigitalIO) -> None:
    """Toggle a single output channel."""
    channel = int(
        prompt_user_choice(
            "Which channel to toggle? (1-8)",
            range(1, 9),
        )
    )

    device.toggle_output_channel(channel)
    logging.info(f"Channel {channel} toggled.")


def _monitor_io_in_loop(device: DigitalIO) -> None:
    """Monitor input and output status periodically."""
    logging.info("Starting periodic IO monitoring. Press Ctrl+C to stop.")
    try:
        last_read_time = None
        while True:
            current_read_time = monotonic()
            try:
                inputs = device.read_digital_inputs()
                outputs = device.read_digital_outputs()
            except ModbusException as exc:
                logging.error(f"Failed to fetch IO status. Error: {exc}")
                return

            input_details = ", ".join(f"CH{i+1}: {'ON' if state else 'OFF'}" for i, state in enumerate(inputs))
            output_details = ", ".join(f"CH{i+1}: {'ON' if state else 'OFF'}" for i, state in enumerate(outputs))

            if last_read_time is None:
                logging.info(f"Inputs: {input_details} | Outputs: {output_details}")
            else:
                logging.info(f"Inputs: {input_details} | Outputs: {output_details}")
                logging.debug(f"Time since last read: {current_read_time - last_read_time:.3f} s")
            last_read_time = current_read_time
    except KeyboardInterrupt:
        logging.info("IO monitoring stopped by user (Ctrl+C).")


def _interactive_menu(device: DigitalIO) -> None:
    """Show interactive menu for device control."""
    while True:
        print("\n" + "=" * 50)
        print("Digital IO Control Menu")
        print("=" * 50)
        print("1. Show current IO status")
        print("2. Set single output channel")
        print("3. Set all outputs")
        print("4. Set outputs by bitmask")
        print("5. Toggle output channel")
        print("6. Set output control mode (all channels)")
        print("7. Monitor IO in real-time")
        print("8. Exit")
        print("=" * 50)

        choice = (
            prompt_user_choice(
                "Select an option",
                range(1, 9),
            )
            .strip()
        )

        try:
            if choice == "1":
                _show_current_io_status(device)
            elif choice == "2":
                _set_output_channel_state(device)
            elif choice == "3":
                _set_all_outputs(device)
            elif choice == "4":
                _set_outputs_by_mask(device)
            elif choice == "5":
                _toggle_output_channel(device)
            elif choice == "6":
                _set_control_mode_all_channels(device)
            elif choice == "7":
                _monitor_io_in_loop(device)
            elif choice == "8":
                logging.info("Exiting...")
                break
        except (ValueError, ModbusException) as exc:
            logging.error(f"Operation failed: {exc}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wavesharertu.devices.digital_io",
        description="Read and control Waveshare Modbus RTU Digital IO device (8 Digital Inputs + 8 Digital Outputs).",
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
        "Digital IO connection parameters:\n\tPort=%s,\n\tAddress=%s,\n\tBaudrate=%s,\n\tParity=%s.",
        args.port,
        args.address,
        args.baudrate,
        args.parity,
    )
    try:
        with RS485(port=args.port, baudrate=args.baudrate, parity=args.parity) as serial_port:
            serial_port.rs485_mode = RS485Settings(delay_before_rx=0.5)
            device = DigitalIO(serial_port, address=args.address)
            try:
                _show_current_io_status(device)
            except ModbusException as exc:
                logging.error("Failed to communicate with device. Check connection and parameters. Error: %s", exc)
                return 1

            _interactive_menu(device)

    except (ValueError, SerialException) as exc:
        logging.error(exc)
        return 1
    except KeyboardInterrupt:
        print()
        logging.info("Operation interrupted by user (Ctrl+C).")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
