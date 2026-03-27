"""Hunt sequence management and loading."""
import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from config import SequenceEventType

logger = logging.getLogger(__name__)


@dataclass
class Sequence:
    """Represents a single hunt sequence configuration."""
    game: str                      # Game title
    method: str                    # Hunt method name
    target: str                    # Target Pokémon species
    events: List[str]              # Sequence of events/button presses
    block_direction: Optional[str] # Direction to block (if any)

    def __post_init__(self):
        """Validate sequence after initialization."""
        self._validate_events()

    def _validate_events(self) -> None:
        """Validate that all events are recognized types or button names."""
        valid_events = {e.value for e in SequenceEventType}
        valid_events.update(self._get_valid_buttons())

        for event in self.events:
            # Check if it's a valid event type or button
            if event not in valid_events:
                # Check if it's a float (delay)
                try:
                    float(event)
                except ValueError:
                    logger.warning(f"Unknown event type in sequence: {event}")

    @staticmethod
    def _get_valid_buttons() -> set[str]:
        """Get set of valid button names.

        Returns:
            Set of recognized button names.
        """
        return {
            "a", "b", "x", "y", "plus", "minus", "home", "capture",
            "l", "r", "zl", "zr", "up", "down", "left", "right"
        }


class SequenceLoader:
    """Loads hunt sequences from CSV file."""

    def __init__(self, csv_path: str = "sequences.csv"):
        """Initialize sequence loader.

        Args:
            csv_path: Path to sequences CSV file.

        Raises:
            FileNotFoundError: If CSV file doesn't exist.
        """
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Sequences file not found: {csv_path}")
        logger.info(f"Initialized sequence loader with {csv_path}")

    def get_available_games(self) -> List[str]:
        """Get list of all available games in sequences file.

        Returns:
            List of unique game names.

        Raises:
            csv.Error: If CSV is malformed.
        """
        games = []
        with open(self.csv_path, newline="") as f:
            reader = csv.DictReader(f)
            self._validate_csv_headers(reader)
            for row in reader:
                game = row.get("game", "").strip()
                if game and game not in games:
                    games.append(game)
        return games

    def get_available_methods(self, game: str) -> List[str]:
        """Get available hunt methods for a specific game.

        Args:
            game: Game name.

        Returns:
            List of method names for the game.

        Raises:
            ValueError: If game not found.
        """
        methods = []
        with open(self.csv_path, newline="") as f:
            reader = csv.DictReader(f)
            self._validate_csv_headers(reader)
            for row in reader:
                if row.get("game", "").strip() == game:
                    method = row.get("method", "").strip()
                    if method and method not in methods:
                        methods.append(method)

        if not methods:
            raise ValueError(f"No methods found for game: {game}")
        return methods

    def load_sequence(self, game: str, method: str) -> Sequence:
        """Load a specific hunt sequence.

        Args:
            game: Game name.
            method: Hunt method name.

        Returns:
            Loaded Sequence object.

        Raises:
            ValueError: If game/method combination not found.
        """
        with open(self.csv_path, newline="") as f:
            reader = csv.DictReader(f)
            self._validate_csv_headers(reader)

            for row in reader:
                if row.get("game", "").strip() == game and row.get("method", "").strip() == method:
                    sequence_str = row.get("sequence", "").strip()
                    events = sequence_str.split() if sequence_str else []

                    seq = Sequence(
                        game=game,
                        method=method,
                        target=row.get("target", "").strip(),
                        events=events,
                        block_direction=row.get("block_direction", "").strip() or None,
                    )
                    logger.info(f"Loaded sequence: {game} - {method} ({len(events)} events)")
                    return seq

        raise ValueError(f"Sequence not found: {game} / {method}")

    @staticmethod
    def _validate_csv_headers(reader: csv.DictReader) -> None:
        """Validate that CSV has required columns.

        Args:
            reader: CSV DictReader object.

        Raises:
            ValueError: If required columns missing.
        """
        required = {"game", "method", "sequence"}
        if not reader.fieldnames:
            raise ValueError("CSV file is empty")

        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing required columns: {missing}")
