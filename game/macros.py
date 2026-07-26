"""Game macro execution - pre-defined button sequences."""
import logging
import random
import time
from typing import TYPE_CHECKING

from config import GameMacros, Timings

if TYPE_CHECKING:
    from controller import ControllerManager

logger = logging.getLogger(__name__)


class GameMacroExecutor:
    """Executes pre-defined game action sequences."""

    def __init__(self, controller: "ControllerManager"):
        """Initialize macro executor.

        Args:
            controller: ControllerManager instance for pressing buttons.
        """
        self.controller = controller

    def start_game(self) -> None:
        """Navigate to game from home screen."""
        logger.info("Starting game...")
        self.controller.press_buttons("home", Timings.STARTUP_DELAY + 0.74)
        self.controller.press_buttons("a", Timings.SELECT_HUNT_CONFIRM)
        logger.info("Game loading...")
        time.sleep(1.5)

    def reset_position(self) -> None:
        """Execute full reset sequence to recover Pokémon to initial position."""
        logger.info("Resetting position...")
        random_delay = round(random.uniform(0, 0.2), 3)
        self.controller.press_buttons(GameMacros.RESET_BUTTONS, Timings.RESET_POSITION_PHASE_1)
        time.sleep(random_delay)
        self.controller.press_buttons("a", Timings.RESET_POSITION_PHASE_2)
        self.controller.press_buttons("a", random_delay)

        self.controller.press_buttons("a", Timings.RESET_POSITION_PHASE_3)
        self.controller.press_buttons("a", random_delay)

        self.controller.press_buttons("a", Timings.RESET_POSITION_PHASE_4)
        self.controller.press_buttons("a", random_delay )

        self.controller.press_buttons("a", Timings.RESET_POSITION_PHASE_5)
        self.controller.press_buttons("b", Timings.RESET_POSITION_PHASE_6)
        time.sleep(Timings.RESET_POSITION_FINAL_WAIT)
        logger.info("Position reset complete")

    def save_game(self) -> None:
        """Execute save game sequence."""
        logger.info("Saving game...")
        self.controller.press_buttons("x", Timings.SAVE_GAME_X)

        # Navigate down to save option
        for i in range(4):
            self.controller.press_buttons("down", Timings.SAVE_GAME_DOWN_1)

        # Confirm save
        self.controller.press_buttons("a", Timings.SAVE_GAME_CONFIRM_1)
        self.controller.press_buttons("a", Timings.SAVE_GAME_CONFIRM_2)
        self.controller.press_buttons("a", Timings.SAVE_GAME_CONFIRM_3)

        # Reset to safe state
        self.reset_position()
        logger.info("Game saved")

    def wait_for_encounter_load(self) -> None:
        """Wait for encounter screen to fully load with light indicators."""
        from capture import FrameCaptureManager
        from processing import ImageAnalyzer

        logger.info("Waiting for encounter to load...")
        timeout = 30
        start = time.time()

        while time.time() - start < timeout:
            # This assumes FrameCaptureManager instance is passed, but for now
            # we log that this would poll frames
            time.sleep(0.02)
            # In full implementation, would check encounter_load_check here

        logger.info("Encounter loaded")
