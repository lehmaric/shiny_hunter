"""Image analysis and processing utilities."""
import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from config import (
    FRAME_WIDTH, FRAME_HEIGHT, CropRegions, ImageThresholds, DetectionThresholds,
    ImageProcessing
)

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Performs image processing for game state detection."""

    @staticmethod
    def crop_frame(
        image: np.ndarray,
        x_min: float, x_max: float,
        y_min: float, y_max: float
    ) -> np.ndarray:
        """Crop frame using normalized coordinates (0-1).

        Args:
            image: Source image frame.
            x_min, x_max: Horizontal bounds (0=left, 1=right).
            y_min, y_max: Vertical bounds (0=top, 1=bottom).

        Returns:
            Cropped image region.
        """
        h, w = image.shape[:2]
        x1 = int(w * x_min)
        x2 = int(w * x_max)
        y1 = int(h * y_min)
        y2 = int(h * y_max)
        return image[y1:y2, x1:x2]

    @staticmethod
    def threshold_process(
        image: np.ndarray,
        threshold_min: int = ImageThresholds.TEXT_BRIGHT
    ) -> np.ndarray:
        """Convert image to binary mask for white text/UI detection.

        Args:
            image: Source image (color or grayscale).
            threshold_min: Brightness threshold for binary conversion.

        Returns:
            Binary mask (white=255, black=0).
        """
        # Convert to grayscale if color
        if len(image.shape) == 3:
            grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            grey = image

        # Denoise
        blurred = cv2.GaussianBlur(grey, ImageProcessing.GAUSSIAN_BLUR_KERNEL, 0)

        # Binary threshold
        _, binary = cv2.threshold(blurred, threshold_min, 255, cv2.THRESH_BINARY)

        # Morphological cleanup
        kernel = np.ones((ImageProcessing.MORPHO_KERNEL_SIZE, ImageProcessing.MORPHO_KERNEL_SIZE), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

        return cleaned

    @staticmethod
    def threshold_detect(
        binary_mask: np.ndarray,
        detection_threshold: float
    ) -> bool:
        """Detect if white pixel percentage exceeds threshold.

        Args:
            binary_mask: Binary image from threshold_process.
            detection_threshold: Required white pixel percentage (0-1).

        Returns:
            True if white pixels exceed threshold.
        """
        white_pixels = cv2.countNonZero(binary_mask)
        total_pixels = binary_mask.shape[0] * binary_mask.shape[1]
        percentage = white_pixels / total_pixels
        return percentage > detection_threshold

    @staticmethod
    def check_encounter_loaded(image: np.ndarray) -> bool:
        """Detect if encounter screen has fully loaded.

        Args:
            image: Current frame.

        Returns:
            True if encounter is loaded and visible.
        """
        crop = ImageAnalyzer.crop_frame(image, *CropRegions.ENCOUNTER_DETECTION)
        binary = ImageAnalyzer.threshold_process(crop, ImageThresholds.ENCOUNTER_BLUE_FILTER)
        # Low white = loaded (screen goes dark)
        loaded = not ImageAnalyzer.threshold_detect(binary, DetectionThresholds.ENCOUNTER_NOT_LOADED)
        return loaded

    @staticmethod
    def check_encounter_in_progress(image: np.ndarray) -> bool:
        """Detect if player is in an active encounter.

        Args:
            image: Current frame.

        Returns:
            True if encounter screen detected.
        """
        crop = ImageAnalyzer.crop_frame(image, *CropRegions.ENCOUNTER_LOAD_CHECK)
        binary = ImageAnalyzer.threshold_process(crop, ImageThresholds.ENCOUNTER_LOAD_CHECK)
        in_encounter = ImageAnalyzer.threshold_detect(binary, DetectionThresholds.ENCOUNTER_LOADED)
        return in_encounter

    @staticmethod
    def check_battle_started(image: np.ndarray) -> bool:
        """Detect if battle UI has appeared.

        Args:
            image: Current frame.

        Returns:
            True if battle screen is loaded.
        """
        crop = ImageAnalyzer.crop_frame(image, *CropRegions.BATTLE_UI)
        binary = ImageAnalyzer.threshold_process(crop, ImageThresholds.UI_ELEMENTS)
        battle_loaded = ImageAnalyzer.threshold_detect(binary, DetectionThresholds.BATTLE_LOADED)
        return battle_loaded

    @staticmethod
    def check_shiny_early_detection(image: np.ndarray, gen: int = 3) -> bool:
        """Detect shiny Pokémon during early encounter animation.

        Args:
            image: Current frame.
            gen: Game generation (3 or 4).

        Returns:
            True if shiny sparkle detected.
        """
        crop_region = CropRegions.SHINY_GEN3 if gen == 3 else CropRegions.SHINY_GEN4
        crop = ImageAnalyzer.crop_frame(image, *crop_region)
        binary = ImageAnalyzer.threshold_process(crop, ImageThresholds.SHINY_INDICATOR)
        # Shiny = low white percentage (sparkle only)
        shiny = not ImageAnalyzer.threshold_detect(binary, DetectionThresholds.SHINY_NOT_DETECTED)
        return shiny

    @staticmethod
    def check_shiny_summary_star(image: np.ndarray) -> bool:
        """Detect shiny star on Pokémon summary screen.

        Args:
            image: Current frame.

        Returns:
            True if shiny star visible.
        """
        crop = ImageAnalyzer.crop_frame(image, *CropRegions.SUMMARY_STAR)
        binary = ImageAnalyzer.threshold_process(crop, ImageThresholds.SHINY_STAR)
        star_visible = ImageAnalyzer.threshold_detect(binary, DetectionThresholds.SUMMARY_STAR_DETECTED)
        return star_visible
