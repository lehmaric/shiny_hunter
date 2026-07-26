"""
Global configuration and constants for SwitchBot.
"""
from enum import Enum
from typing import Dict, Tuple


class ButtonType(Enum):
    """Available button inputs."""
    A = "a"
    B = "b"
    X = "x"
    Y = "y"
    PLUS = "plus"
    MINUS = "minus"
    HOME = "home"
    CAPTURE = "capture"
    L = "l"
    R = "r"
    ZL = "zl"
    ZR = "zr"
    DPAD_UP = "up"
    DPAD_DOWN = "down"
    DPAD_LEFT = "left"
    DPAD_RIGHT = "right"


class SequenceEventType(Enum):
    """Special sequence event types."""
    LOOP = "loop"
    END = "end"
    BATTLE = "battle"
    CHECK = "check"
    SUMMARY = "summary"
    RESET = "reset"
    ENCOUNTER = "encounter"


# ============================================================================
# STREAM & CAPTURE SETTINGS
# ============================================================================
RTSP_URL = "RTSP STREAM ADDRESS"  # CHANGE THIS

# Frame capture dimensions (after downscaling)
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
PREVIEW_FPS = 12

# FFmpeg input settings
FFMPEG_INPUT_FORMAT = "mjpeg"
FFMPEG_INPUT_SIZE = "1920x1080"
FFMPEG_INPUT_FPS = 60
FFMPEG_INPUT_DEVICE = "/dev/video0"

# ============================================================================
# OUTPUT & LOGGING
# ============================================================================
OUTPUT_DIR = "screenshots"
DEBUG_DIR = "screenshots/debug"
ROLLING_FILE = "shinyFound%01d.ts"
FFMPEG_LOG_FILE = "ffmpeg.log"

# ============================================================================
# DEBUGGING
# ============================================================================
DEBUGGING = False
SKIP_BLUETOOTH_SETUP = False  # Set True to skip Bluetooth setup (dev without Bluetooth)
LIVE_PREVIEW = True           # Enable live MJPEG preview via HTTP
PREVIEW_PORT = 8765           # Port for live preview server

# ============================================================================
# CONTROLLER SETTINGS
# ============================================================================
BUTTON_PRESS_DURATION = 0.2
MIN_BUTTON_DELAY = 0.1
DEFAULT_BUTTON_DELAY = 0.2

# ============================================================================
# TIMING DELAYS (in seconds)
# ============================================================================
class Timings:
    """Game-specific timing constants."""
    STARTUP_DELAY = 0.01
    SELECT_HUNT_INTRO = 0.75
    SELECT_HUNT_CONFIRM = 0.5
    RESET_POSITION_PHASE_1 = 3.8
    RESET_POSITION_PHASE_2 = 1.1
    RESET_POSITION_PHASE_3 = 1.1
    RESET_POSITION_PHASE_4 = 2.7
    RESET_POSITION_PHASE_5 = 1.3
    RESET_POSITION_PHASE_6 = 1.9
    RESET_POSITION_FINAL_WAIT = 3.0
    
    SAVE_GAME_X = 1
    SAVE_GAME_DOWN_1 = 0.5
    SAVE_GAME_DOWN_2 = 0.5
    SAVE_GAME_DOWN_3 = 0.5
    SAVE_GAME_DOWN_4 = 0.5
    SAVE_GAME_CONFIRM_1 = 1
    SAVE_GAME_CONFIRM_2 = 1
    SAVE_GAME_CONFIRM_3 = 2.5
    
    ENCOUNTER_CHECK_INITIAL_WAIT = 1
    ENCOUNTER_CHECK_DELAY = 2.4
    ENCOUNTER_CHECK_POST_DELAY = 1
    
    BATTLE_START_WAIT = 3.5
    BATTLE_CHECK_POLL_INTERVAL = 0.3
    
    ENCOUNTER_LOAD_POLL_INTERVAL = 0.02
    ENCOUNTER_LOAD_WAIT_AFTER = 1.4
    
    SHINY_FOUND_SCREENSHOT_1 = 0.2
    SHINY_FOUND_CONTROLLER_DISCONNECT = 2
    SHINY_FOUND_SCREENSHOT_2 = 0.2
    
    CONTROLLER_RECONNECT_WAIT = 3
    CONTROLLER_RECONNECT_INTRO = 2
    
    FIRST_FRAME_TIMEOUT = 10
    STREAM_READY_WAIT = 0.01


# ============================================================================
# IMAGE PROCESSING - CROP REGIONS (normalized 0-1)
# ============================================================================
class CropRegions:
    """Normalized crop regions for image analysis (xMin, xMax, yMin, yMax)."""
    # Encounter detection
    ENCOUNTER_DETECTION: Tuple[float, float, float, float] = (0.2, 0.8, 0.4, 0.6)
    ENCOUNTER_LOAD_CHECK: Tuple[float, float, float, float] = (0.4, 0.6, 0.4, 0.6)
    
    # Battle detection
    BATTLE_UI: Tuple[float, float, float, float] = (0.54, 0.72, 0.80, 0.95)
    
    # Shiny detection (Gen 3 Emerald)
    SHINY_GEN3: Tuple[float, float, float, float] = (0.2, 0.4, 0.75, 0.85)
    # Shiny detection (Gen 4 Brilliantdiamondshiningpearl)
    SHINY_GEN4: Tuple[float, float, float, float] = (0.15, 0.4, 0.25, 0.35)
    
    # Summary screen star
    SUMMARY_STAR: Tuple[float, float, float, float] = (0.435, 0.47, 0.215, 0.275)


# ============================================================================
# IMAGE PROCESSING - THRESHOLDS
# ============================================================================
class ImageThresholds:
    """Threshold values for binary image detection."""
    TEXT_BRIGHT = 95          # For bright white text
    UI_ELEMENTS = 120         # For UI detection
    SHINY_INDICATOR = 130     # For early shiny detection
    SHINY_STAR = 240          # For summary screen star
    ENCOUNTER_BLUE_FILTER = 50  # For encounter screen blue
    ENCOUNTER_LOAD_CHECK = 75   # For encounter loaded black check


# ============================================================================
# IMAGE PROCESSING - DETECTION THRESHOLDS (pixel percentage)
# ============================================================================
class DetectionThresholds:
    """Percentage thresholds for pixel-based detection."""
    ENCOUNTER_NOT_LOADED = 0.1          # Low white % = loaded
    BATTLE_LOADED = 0.25                # High white % = UI present
    ENCOUNTER_LOADED = 0.4              # High white % = loaded
    SHINY_NOT_DETECTED = 0.015          # Low white % = shiny
    SUMMARY_STAR_DETECTED = 0.8         # High white % = star visible


# ============================================================================
# CONTROLLER PARAMETERS
# ============================================================================
class ControllerConfig:
    """Nintendo Switch Pro Controller configuration."""
    COLOUR_BODY = None  # Will be randomized at runtime
    COLOUR_BUTTONS = [255, 255, 255]
    RECONNECT_MAX_LOOPS = 50
    RECONNECT_WAIT = 2


# ============================================================================
# GAME MACROS - BUTTON SEQUENCES
# ============================================================================
class GameMacros:
    """Pre-defined button sequences for common game actions."""
    RESET_BUTTONS = ["a", "b", "x", "y"]
    SAVE_GAME_NAVIGATE = ["down", "down", "down", "down"]


# ============================================================================
# MORPHOLOGICAL OPERATIONS
# ============================================================================
class ImageProcessing:
    """Parameters for morphological image processing."""
    GAUSSIAN_BLUR_KERNEL = (3, 3)
    MORPHO_KERNEL_SIZE = 2  # Creates (2,2) kernel
