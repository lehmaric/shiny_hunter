"""Nintendo Switch Pro Controller manager."""
import subprocess
import time
import random
import logging
from typing import Optional, List, Union

import nuxbt
from nuxbt import Buttons

from config import ButtonType, BUTTON_PRESS_DURATION, MIN_BUTTON_DELAY, ControllerConfig

logger = logging.getLogger(__name__)


class ControllerManager:
    """Manages Bluetooth connection and button presses for Nintendo Switch Pro Controller."""

    def __init__(self):
        """Initialize controller manager."""
        self._nx = nuxbt.Nuxbt()
        self._controller_idx: Optional[int] = None
        self._button_map = self._build_button_map()

    def cleanup(self) -> None:
        """Full cleanup of nuxbt resources to prevent atexit errors."""
        self.disconnect_controller()
        try:
            # Suppress the atexit assertion by cleaning up nuxbt internals
            if hasattr(self._nx, 'controllers') and self._nx.controllers.is_alive():
                self._nx.controllers.terminate()
                self._nx.controllers.join(timeout=2)
            if hasattr(self._nx, 'agent') and self._nx.agent.is_alive():
                self._nx.agent.terminate()
                self._nx.agent.join(timeout=2)
        except (AssertionError, AttributeError, Exception) as e:
            logger.debug(f"Cleanup note: {e}")

    def setup_bluetooth(self, skip: bool = False) -> None:
        """Initialize and configure Bluetooth for Switch controller pairing.

        Args:
            skip: If True, skip Bluetooth setup (useful for dev environments).
        """
        if skip:
            logger.info("Skipping Bluetooth setup (dev mode)")
            return

        logger.info("Configuring Bluetooth...")
        bt_commands = """
agent NoInputNoOutput
default-agent
power on
discoverable on
pairable on
exit
"""
        try:
            subprocess.run(
                ["bluetoothctl"], 
                input=bt_commands, 
                text=True, 
                check=True,
                timeout=5
            )
            logger.info("Bluetooth configured successfully")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Bluetooth configuration warning: {e}")
            logger.info("Proceeding with controller creation...")

    def create_controller(self) -> int:
        """Create a new Pro Controller instance and wait for connection.

        Returns:
            int: Controller index for future button presses.

        Raises:
            RuntimeError: If no adapters available or connection fails.
        """
        adapters = self._nx.get_available_adapters()
        if not adapters:
            raise RuntimeError(
                "No Bluetooth adapters detected. "
                "Ensure Bluetooth is running and you have sudo privileges."
            )

        adapter = adapters[0]
        logger.info(f"Using Bluetooth adapter: {adapter}")

        colour_body = ControllerConfig.COLOUR_BODY or self._random_colour()
        idx = self._nx.create_controller(
            nuxbt.PRO_CONTROLLER,
            adapter_path=adapter,
            colour_body=colour_body,
            colour_buttons=ControllerConfig.COLOUR_BUTTONS,
        )
        logger.info(f"Controller created with index: {idx}")

        logger.info("Put your Switch in 'Pair New Controllers' mode now...")
        self._nx.wait_for_connection(idx)
        logger.info("Controller connected successfully")
        time.sleep(1)

        self._controller_idx = idx
        return idx

    def reconnect_controller(self) -> int:
        """Disconnect current controller and create a new connection.

        Returns:
            int: New controller index.

        Raises:
            RuntimeError: If reconnection fails.
        """
        self.disconnect_controller()
        time.sleep(3)
        logger.info("Reconnecting controller...")

        try:
            switch_addresses = self._nx.get_switch_addresses()
            new_idx = self._nx.create_controller(
                nuxbt.PRO_CONTROLLER,
                reconnect_address=switch_addresses,
            )
            self._nx.wait_for_connection(new_idx)
            logger.info(f"Reconnected successfully. New controller index: {new_idx}")
            self._controller_idx = new_idx
            return new_idx
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            raise

    def disconnect_controller(self) -> None:
        """Disconnect the current controller."""
        if self._controller_idx is None:
            logger.warning("No controller to disconnect")
            return

        logger.info("Disconnecting controller")
        try:
            self._nx.remove_controller(self._controller_idx)
            self._controller_idx = None
        except Exception as e:
            logger.debug(f"Controller disconnect error (may be normal): {e}")

    def press_buttons(
        self,
        buttons: Union[str, List[str]],
        delay: float = MIN_BUTTON_DELAY,
    ) -> None:
        """Press one or more buttons.

        Args:
            buttons: Single button name or list of button names.
            delay: Delay in seconds after pressing (minimum 0.2s).

        Raises:
            ValueError: If button name is invalid.
            RuntimeError: If no controller connected.
        """
        if self._controller_idx is None:
            raise RuntimeError("No controller connected")

        # Normalize to list
        if isinstance(buttons, str):
            buttons = [buttons]

        # Validate and map buttons
        try:
            button_codes = [self._button_map[b] for b in buttons]
        except KeyError as e:
            raise ValueError(f"Unknown button: {e}")

        # Apply minimum delay
        delay = max(float(delay), MIN_BUTTON_DELAY)

        # Press buttons
        self._nx.press_buttons(
            self._controller_idx, button_codes, BUTTON_PRESS_DURATION, block=False
        )
        time.sleep(delay)
        logger.debug(f"Pressed buttons: {buttons}")

    def is_connected(self) -> bool:
        """Check if controller is connected and active.

        Returns:
            bool: True if controller is ready for input.
        """
        return self._controller_idx is not None

    def _build_button_map(self) -> dict[str, Buttons]:
        """Build mapping from button names to nuxbt button codes.

        Returns:
            dict: Button name to Buttons enum mapping.
        """
        return {
            "a": Buttons.A,
            "b": Buttons.B,
            "x": Buttons.X,
            "y": Buttons.Y,
            "plus": Buttons.PLUS,
            "minus": Buttons.MINUS,
            "home": Buttons.HOME,
            "capture": Buttons.CAPTURE,
            "l": Buttons.L,
            "r": Buttons.R,
            "zl": Buttons.ZL,
            "zr": Buttons.ZR,
            "up": Buttons.DPAD_UP,
            "down": Buttons.DPAD_DOWN,
            "left": Buttons.DPAD_LEFT,
            "right": Buttons.DPAD_RIGHT,
        }

    @staticmethod
    def _random_colour() -> List[int]:
        """Generate random RGB colour for controller.

        Returns:
            list: [R, G, B] values 0-255.
        """
        return [random.randint(0, 255) for _ in range(3)]
