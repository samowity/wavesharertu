import logging
from itertools import product
from serial.rs485 import RS485
from typing import Iterable, Iterator, Tuple, Union

from .config import WaveshareRTUConfig
from ..modbus import ModbusException

logger = logging.getLogger(__name__)

DEFAULT_BAUDRATES = [4800, 9600, 19200, 38400, 57600, 115200, 128000, 256000]
DEFAULT_PARITIES = ["N", "E", "O"]


def prompt_user_choice(
    prompt_text: str,
    choices: Iterable[Union[str, int]] | range,
    allow_empty: bool = False,
) -> str:
    """Prompt user to select from a list of choices.

    Args:
        prompt_text: The prompt message to display to the user.
        choices: Available choices (can be a range, list, or other iterable).
        allow_empty: If True, allow user to press Enter without selecting anything.

    Returns:
        The selected choice as a string.
    """
    is_range = isinstance(choices, range)
    if is_range:
        prompt_suffix = f"{choices.start}..{choices.stop - 1}"
    else:
        choice_list = [str(choice) for choice in choices]
        prompt_suffix = " / ".join(choice_list)

    if allow_empty:
        prompt_suffix = f"{prompt_suffix} / (empty)"

    prompt_message = f"{prompt_text} [{prompt_suffix}]: "
    response = input(prompt_message)

    while True:
        if allow_empty and response == "":
            return response

        if is_range:
            if response.lstrip("-").isdigit() and int(response) in choices:
                return response
        else:
            if str(response) in choice_list:
                return response

        logger.warning(f"Invalid response. Allowed values: {prompt_suffix}")
        response = input(prompt_message)


def get_baudrate_parity_combinations(baudrate: str, parity: str) -> Iterator[Tuple[int, str]]:
    """Generate all combinations of baudrate and parity to try.

    Args:
        baudrate: Specific baudrate as string, or '?' to try all default baudrates.
        parity: Specific parity ('N', 'E', 'O'), or '?' to try all default parities.

    Returns:
        Iterator yielding tuples of (baudrate: int, parity: str).
    """
    if baudrate == "?":
        baudrates = DEFAULT_BAUDRATES
    else:
        baudrates = [int(baudrate)]

    if parity == "?":
        parities = DEFAULT_PARITIES
    else:
        parities = [parity]

    return __import__("itertools").product(baudrates, parities)


def find_device(serial_port: RS485, combinations: Iterable[Tuple[int, str]]) -> WaveshareRTUConfig:
    """Search for a Modbus RTU device on the serial port.

    Tries different baudrate and parity combinations until a device responds.

    Args:
        serial_port: RS485 serial port object.
        combinations: Iterator of (baudrate, parity) tuples to try.

    Returns:
        WaveshareRTUConfig object representing the found device.

    Raises:
        RuntimeError: If no device is found with any of the provided combinations.
    """
    logger.info(f"Starting device search on serial port {serial_port.port}...")
    device = WaveshareRTUConfig(serial=serial_port)

    for baudrate, parity in combinations:
        logger.debug(f"Checking configuration: baudrate={baudrate!r}, parity={parity!r}...")
        device.serial.baudrate = baudrate
        device.serial.parity = parity
        try:
            address = device.read_address()
            address_hex = f"{address:02X}"
            logger.info(f"Success! Found device at address {address!r} ({address_hex!r}).")
            return device
        except ModbusException as e:
            logger.debug(f"Failure ({e.__class__.__name__}: {e}).")

    raise RuntimeError("No device found for the provided baudrate and parity.")


def configure_device_address(device: WaveshareRTUConfig) -> None:
    """Interactively configure the device's Modbus address.

    Displays the current address and prompts the user to enter a new address.
    If the user enters nothing, the address is not changed.

    Args:
        device: WaveshareRTUConfig object representing the device.
    """
    address = device.read_address()
    address_hex = f"{address:02X}"
    logger.info(f"Current address: {address!r} / {address_hex!r}.")
    new_addr = prompt_user_choice(
        "New address (empty for no change)",
        range(1, 256),
        allow_empty=True,
    )

    if new_addr:
        new_addr = int(new_addr)
        logger.debug(f"Changing address to {new_addr!r}.")
        device.set_address(new_addr)
        address = device.read_address()
        address_hex = f"{address:02X}"
        logger.info(f"Address changed to {address!r} / {address_hex!r}.")
    else:
        logger.info("No changes to address.")


def configure_device_baudrate(device: WaveshareRTUConfig, serial_port: RS485) -> None:
    """Interactively configure the device's baudrate and parity.

    Displays the current settings and prompts the user to enter new values.
    If the user enters nothing for either setting, that setting is not changed.
    After changing the settings, verifies that the device responds with the new settings.

    Args:
        device: WaveshareRTUConfig object representing the device.
        serial_port: RS485 serial port object for reading current settings.
    """
    logger.info(f"Current baudrate and parity: {serial_port.baudrate!r}, {serial_port.parity!r}.")
    new_baudrate = prompt_user_choice(
        "New baudrate (empty for no change)",
        [str(x) for x in DEFAULT_BAUDRATES],
        allow_empty=True,
    )
    new_parity = prompt_user_choice(
        "New parity (empty for no change)",
        DEFAULT_PARITIES,
        allow_empty=True,
    )

    if not new_baudrate and not new_parity:
        logger.info("No changes to baudrate or parity.")
        return

    new_baudrate = serial_port.baudrate if new_baudrate == "" else int(new_baudrate)
    new_parity = serial_port.parity if new_parity == "" else new_parity
    logger.info(f"Changing baudrate and parity to {new_baudrate!r}, {new_parity!r}.")
    try:
        device.set_baudrate(baudrate=int(new_baudrate), parity=new_parity)
    except ModbusException as e:
        logger.error(f"Failed to set baudrate and parity to {new_baudrate!r}, {new_parity!r}.")
        logger.debug(repr(e))
    else:
        logger.info(f"New baudrate and parity: {serial_port.baudrate!r}, {serial_port.parity!r}.")
