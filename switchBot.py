#!/usr/bin/env python3
"""Nintendo Switch Shiny Hunter Bot - Main Entry Point"""
import logging
import signal
import sys
import time
import threading
import datetime
import subprocess
from pathlib import Path

from numpy.typing import NDArray

import cv2

from config import (
    DEBUGGING, OUTPUT_DIR, DEBUG_DIR, Timings, SKIP_BLUETOOTH_SETUP,
    LIVE_PREVIEW, PREVIEW_PORT, FRAME_WIDTH, FRAME_HEIGHT
)
from capture import FrameCaptureManager
from controller import ControllerManager
from processing import ImageAnalyzer
from game import Sequence, SequenceLoader, GameMacroExecutor

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUGGING else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create output directories
Path(OUTPUT_DIR).mkdir(exist_ok=True)
Path(DEBUG_DIR).mkdir(exist_ok=True)

# Global state
QUITTING = False
capture_manager: FrameCaptureManager | None = None
controller_manager: ControllerManager | None = None

# ============================================================================
# Capture Management
# ============================================================================

def start_capture() -> bool:
    """Start video stream capture."""
    global capture_manager
    if capture_manager is None:
        capture_manager = FrameCaptureManager()
    return capture_manager.start()


def stop_capture() -> None:
    """Stop video stream capture."""
    global capture_manager
    if capture_manager:
        capture_manager.stop()


def get_frame() -> NDArray | None:
    """Get latest captured frame."""
    if capture_manager is None:
        return None
    return capture_manager.get_frame()


def watchdog() -> None:
    """Background thread to restart FFmpeg if it crashes."""
    while not QUITTING:
        time.sleep(10)
        if capture_manager and not capture_manager.is_running():
            logger.warning("FFmpeg crashed, restarting...")
            stop_capture()
            time.sleep(2)
            start_capture()


# ============================================================================
# Live Preview (MJPEG over HTTP)
# ============================================================================

def start_preview_server() -> None:
    """Start a background HTTP server that streams MJPEG for live preview.

    Access at http://localhost:{PREVIEW_PORT} in a browser.
    """
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class MJPEGHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                html = f"""
                <html><head><title>SwitchBot Preview</title>
                <style>body{{background:#111;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}}
                img{{max-width:100%;height:auto;}}</style></head>
                <body><img src="/stream" /></body></html>
                """
                self.wfile.write(html.encode())
            elif self.path == "/stream":
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                while not QUITTING:
                    frame = get_frame()
                    if frame is not None:
                        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                        try:
                            self.wfile.write(b"--frame\r\n")
                            self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                            self.wfile.write(jpeg.tobytes())
                            self.wfile.write(b"\r\n")
                        except (BrokenPipeError, ConnectionResetError):
                            break
                    time.sleep(1.0 / 12)  # ~12 FPS
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            pass  # Suppress HTTP logs

    server = HTTPServer(("", PREVIEW_PORT), MJPEGHandler)
    logger.info(f"Live preview available at http://localhost:{PREVIEW_PORT}")
    server.serve_forever()

# ============================================================================
# Frame Saving
# ============================================================================

def save_frame(filename: str, frame=None, stamp: bool = False) -> None:
    """Save a frame to disk.

    Args:
        filename: Base filename (without extension).
        frame: Frame to save (uses latest if None).
        stamp: Whether to add timestamp prefix.
    """
    if frame is None:
        frame = get_frame()

    if frame is None:
        logger.error("No frame available to save")
        return

    if stamp:
        now = datetime.datetime.now()
        filename = now.strftime("%Y-%m-%d_%H-%M-%S") + "_" + filename

    if DEBUGGING:
        path = f"{DEBUG_DIR}/{filename}.png"
    else:
        path = f"{OUTPUT_DIR}/{filename}.png"

    cv2.imwrite(path, frame)
    logger.debug(f"Saved frame: {path}")


def save_highlight() -> None:
    """Save recent video segment as highlight video."""
    logger.info("Saving highlight video...")
    stop_capture()
    time.sleep(2)

    segments = [
        f for f in Path(OUTPUT_DIR).iterdir()
        if f.name.startswith("shinyFound") and f.name.endswith(".ts")
    ]

    if not segments:
        logger.error("No video segments found")
        return

    segments.sort(key=lambda x: x.stat().st_mtime)

    concat_path = Path(OUTPUT_DIR) / "concat.txt"
    with open(concat_path, "w") as f:
        for seg in segments:
            f.write(f"file '{seg.absolute()}'\n")

    now = datetime.datetime.now()
    output_file = Path(OUTPUT_DIR) / f"SHINY_{now.strftime('%Y-%m-%d_%H-%M-%S')}.mp4"

    try:
        subprocess.run([
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
            "-c", "copy",
            "-bsf:a", "aac_adtstoasc",
            str(output_file)
        ], check=True)
        logger.info(f"Highlight saved: {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to create highlight video: {e}")

    start_capture()
    time.sleep(2)

# ============================================================================
# Controller Management
# ============================================================================

def setup_controller() -> int:
    """Initialize Bluetooth (if needed) and create controller.

    Returns:
        int: Controller index.

    Raises:
        RuntimeError: If setup fails.
    """
    global controller_manager
    controller_manager = ControllerManager()
    controller_manager.setup_bluetooth(skip=SKIP_BLUETOOTH_SETUP)
    idx = controller_manager.create_controller()
    return idx


def disconnect_controller() -> None:
    """Disconnect current controller."""
    global controller_manager
    if controller_manager:
        controller_manager.disconnect_controller()


def reconnect_controller() -> int:
    """Reconnect to Switch after disconnection.

    Returns:
        int: New controller index.
    """
    global controller_manager
    if controller_manager is None:
        raise RuntimeError("Controller manager not initialized")
    return controller_manager.reconnect_controller()

# ============================================================================
# Shutdown & Signals
# ============================================================================

def quit_program() -> None:
    """Graceful shutdown."""
    global QUITTING
    if QUITTING:
        return
    QUITTING = True
    logger.info("Shutting down...")

    stop_capture()

    # Full nuxbt cleanup to prevent atexit assertion error
    if controller_manager:
        controller_manager.cleanup()

    logger.info("Goodbye")
    sys.exit(0)


def on_exit_signal(sig, frame):
    """Handle interrupt signals."""
    quit_program()


signal.signal(signal.SIGINT, on_exit_signal)
signal.signal(signal.SIGTERM, on_exit_signal)

# ============================================================================
# Hunt Event Detection
# ============================================================================

def check_if_in_encounter(frame) -> bool:
    """Detect if player is in active encounter.

    Args:
        frame: Current video frame.

    Returns:
        bool: True if in encounter.
    """
    analyzer = ImageAnalyzer()
    in_encounter = analyzer.check_encounter_in_progress(frame)
    if in_encounter:
        save_frame("encounter_original", frame)
        save_frame("encounter_crop", analyzer.crop_frame(frame, *Timings.__dict__["CropRegions.ENCOUNTER_DETECTION"]))
        logger.info("Encounter detected")
    return in_encounter


def check_if_shiny_early(frame, gen: int = 3) -> bool:
    """Detect shiny during early encounter animation.

    Args:
        frame: Current frame.
        gen: Game generation (3 or 4).

    Returns:
        bool: True if shiny detected.
    """
    analyzer = ImageAnalyzer()
    shiny = analyzer.check_shiny_early_detection(frame, gen)
    if shiny:
        save_frame("shiny_raw", frame, stamp=True)
        logger.info("Shiny detected!")
    return shiny


def check_if_summary_shiny(frame) -> bool:
    """Detect shiny on summary screen via star indicator.

    Args:
        frame: Current frame.

    Returns:
        bool: True if shiny star visible.
    """
    analyzer = ImageAnalyzer()
    shiny = analyzer.check_shiny_summary_star(frame)
    if not shiny:
        logger.info("No shiny on summary")
    return shiny


def check_if_battle_loaded(frame) -> bool:
    """Detect if battle interface has appeared.

    Args:
        frame: Current frame.

    Returns:
        bool: True if battle loaded.
    """
    analyzer = ImageAnalyzer()
    return analyzer.check_battle_started(frame)

# ============================================================================
# Hunt Sequence Selection
# ============================================================================

def select_hunt() -> Sequence:
    """Interactively select a game and hunt method.

    Returns:
        Sequence: The selected hunt sequence.

    Raises:
        ValueError: If selection cannot be made.
    """
    loader = SequenceLoader("sequences.csv")

    # Get available games
    games = loader.get_available_games()
    logger.info(f"Available games: {games}")

    while True:
        game = input("Select Game: ").strip()
        if game in games:
            break
        logger.warning(f"Game '{game}' not found")

    # Get available methods
    methods = loader.get_available_methods(game)
    logger.info(f"Available methods for {game}: {methods}")

    while True:
        method = input("Select Method: ").strip()
        if method in methods:
            break
        logger.warning(f"Method '{method}' not found for {game}")

    target = input("Hunt Target (Pokémon name): ").strip()
    block_direction = input("Block direction (optional): ").strip() or None

    # Load and return sequence
    sequence = loader.load_sequence(game, method)
    sequence.target = target
    sequence.block_direction = block_direction

    logger.info(f"Hunt selected: {game} / {method} targeting {target}")
    return sequence


# ============================================================================
# Main Hunt Loop
# ============================================================================

def hunt_shiny(sequence: Sequence) -> None:
    """Execute a hunt sequence until shiny is found.

    Args:
        sequence: Hunt sequence to execute.
    """
    global controller_manager

    if controller_manager is None:
        raise RuntimeError("Controller not initialized")

    logger.info(f"Starting hunt: {sequence.method}")
    time.sleep(3)

    macros = GameMacroExecutor(controller_manager)
    analyzer = ImageAnalyzer()

    encounter_count = 1
    shiny_found = False

    macros.start_game()
    while not shiny_found:
        for event_idx, event in enumerate(sequence.events):
            if event == "loop":
                # Find matching end
                end_idx = None
                for j in range(event_idx, len(sequence.events)):
                    if sequence.events[j] == "end":
                        end_idx = j
                        break

                if end_idx is None:
                    logger.error("Malformed sequence: 'loop' without 'end'")
                    return

                # Execute loop until encounter
                loop_events = sequence.events[event_idx + 1 : end_idx]
                encounter_started = False
                max_loops = 50
                loop_count = 0

                while not encounter_started and loop_count < max_loops:
                    for loop_event in loop_events:
                        if loop_event == sequence.block_direction:
                            continue  # Skip blocked directions

                        if controller_manager._button_map.get(loop_event):
                            controller_manager.press_buttons(loop_event, 0.1)
                        else:
                            try:
                                delay = float(loop_event)
                                time.sleep(delay)
                            except ValueError:
                                if loop_event == "encounter":
                                    frame = get_frame()
                                    encounter_started = check_if_in_encounter(frame)
                                    if encounter_started:
                                        break

                        if encounter_started:
                            break

                    loop_count += 1

                if loop_count >= max_loops:
                    logger.warning("Max loops exceeded, attempting reconnect...")
                    try:
                        reconnect_controller()
                        macros.reset_position()
                        loop_count = 0
                    except Exception as e:
                        logger.error(f"Reconnect failed: {e}")
                        quit_program()

                # Wait for encounter to load with light indicators
                time.sleep(Timings.ENCOUNTER_LOAD_WAIT_AFTER)
                logger.debug("Encounter loaded, continuing...")

            elif event == "battle":
                logger.info("Waiting for battle UI...")
                time.sleep(Timings.BATTLE_START_WAIT)
                battle_loaded = False
                while not battle_loaded:
                    frame = get_frame()
                    battle_loaded = check_if_battle_loaded(frame)
                    time.sleep(Timings.BATTLE_CHECK_POLL_INTERVAL)
                logger.info("Battle started")

            elif event == "check":
                time.sleep(Timings.ENCOUNTER_CHECK_INITIAL_WAIT)
                save_frame("shiny_precheck")
                time.sleep(Timings.ENCOUNTER_CHECK_DELAY - Timings.ENCOUNTER_CHECK_INITIAL_WAIT)
                frame = get_frame()
                shiny_found = check_if_shiny_early(frame, gen=3)
                if not shiny_found:
                    logger.info("Not shiny, continuing...")

            elif event == "summary":
                frame = get_frame()
                save_frame("shiny_summary", frame, stamp=False)
                shiny_found = check_if_summary_shiny(frame)
                if not shiny_found:
                    logger.info("Not shiny on summary, continuing...")

            elif event == "reset":
                macros.reset_position()

            else:
                # Treat as button or delay
                if controller_manager._button_map.get(event):
                    controller_manager.press_buttons(event, 0.1)
                else:
                    try:
                        delay = float(event)
                        time.sleep(delay)
                    except ValueError:
                        logger.warning(f"Unknown event: {event}")

            if DEBUGGING:
                frame = get_frame()
                if frame is not None:
                    save_frame(f"After_{event}", frame, stamp=True)

            if shiny_found:
                break

        if shiny_found:
            break

        encounter_count += 1
        logger.info(f"Encounter {encounter_count}, continuing...")

    logger.info(f"SHINY FOUND AFTER {encounter_count} ENCOUNTERS!")
    save_frame("Shiny0", stamp=True)
    time.sleep(Timings.SHINY_FOUND_SCREENSHOT_1)
    save_frame("Shiny1", stamp=True)

    # Disconnect to allow player to catch
    disconnect_controller()
    time.sleep(Timings.SHINY_FOUND_CONTROLLER_DISCONNECT)

    save_highlight()

    while True:
        caught = input("Type Y when shiny caught: ").strip().upper()
        if caught == "Y":
            break

    reconnect_controller()


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> None:
    """Main application loop."""
    logger.info("Nintendo Switch Shiny Hunter starting...")
    time.sleep(Timings.STARTUP_DELAY)

    # Setup controller
    try:
        setup_controller()
        controller_manager.press_buttons("a", 1)
    except Exception as e:
        logger.error(f"Controller setup failed: {e}")
        quit_program()

    # Start video capture
    start_capture()
    threading.Thread(target=watchdog, daemon=True).start()

    if not capture_manager.wait_for_first_frame(Timings.FIRST_FRAME_TIMEOUT):
        logger.error("Stream failed, check ffmpeg.log")
        quit_program()
    else:
        logger.info("Video stream ready")

    # Start live preview if enabled
    if LIVE_PREVIEW:
        threading.Thread(target=start_preview_server, daemon=True).start()

    # Main hunt loop
    while not QUITTING:
        try:
            time.sleep(Timings.STREAM_READY_WAIT)
            sequence = select_hunt()
            hunt_shiny(sequence)
        except KeyboardInterrupt:
            quit_program()
        except Exception as e:
            logger.error(f"Hunt error: {e}", exc_info=True)
            if not input("Retry? (y/n): ").strip().lower().startswith("y"):
                quit_program()


if __name__ == "__main__":
    main()

