"""Frame capture manager using FFmpeg."""
import subprocess
import threading
import time
import logging
from typing import Optional
from pathlib import Path

import numpy as np

from config import FRAME_WIDTH, FRAME_HEIGHT, PREVIEW_FPS, FFMPEG_LOG_FILE
from config import FFMPEG_INPUT_DEVICE, FFMPEG_INPUT_FORMAT, FFMPEG_INPUT_FPS, FFMPEG_INPUT_SIZE

logger = logging.getLogger(__name__)


class FrameCaptureManager:
    """Manages FFmpeg video capture stream with background frame reader."""

    def __init__(self):
        """Initialize capture manager."""
        self._process: Optional[subprocess.Popen] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._reader_running = False
        self._frame_lock = threading.Lock()
        self._start_lock = threading.Lock()
        self._log_file = None
        self._latest_frame: Optional[np.ndarray] = None

        self._frame_size = FRAME_WIDTH * FRAME_HEIGHT * 3

    def start(self) -> bool:
        """Start video capture stream.

        Returns:
            bool: True if started successfully, False if already running.

        Raises:
            RuntimeError: If FFmpeg process fails to start.
        """
        with self._start_lock:
            if self._process and self._process.poll() is None:
                logger.info("Capture already running")
                return False

            try:
                command = self._build_ffmpeg_command()
                self._log_file = open(FFMPEG_LOG_FILE, "w")
                self._process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=self._log_file,
                    stdin=subprocess.DEVNULL,
                    bufsize=0,
                )

                self._reader_running = True
                self._reader_thread = threading.Thread(
                    target=self._frame_reader, daemon=True
                )
                self._reader_thread.start()
                logger.info("Capture started successfully")
                return True
            except Exception as e:
                logger.error(f"Failed to start capture: {e}")
                self.stop()
                raise

    def stop(self) -> None:
        """Stop video capture stream and cleanup resources."""
        logger.info("Stopping capture")
        self._reader_running = False

        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg did not terminate, killing...")
                self._process.kill()
                self._process.wait()
            self._process = None

        if self._reader_thread:
            self._reader_thread.join(timeout=3)
            self._reader_thread = None

        if self._log_file:
            self._log_file.close()
            self._log_file = None

        logger.info("Capture stopped")

    def get_frame(self) -> Optional[np.ndarray]:
        """Get latest captured frame.

        Returns:
            Optional[np.ndarray]: Latest frame as BGR image, or None if unavailable.
        """
        with self._frame_lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def wait_for_first_frame(self, timeout: float = 10.0) -> bool:
        """Block until first frame arrives or timeout expires.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            bool: True if frame arrived, False on timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            with self._frame_lock:
                if self._latest_frame is not None:
                    logger.info("First frame received")
                    return True
            time.sleep(0.1)

        logger.error("Timeout waiting for first frame")
        return False

    def is_running(self) -> bool:
        """Check if capture process is running.

        Returns:
            bool: True if FFmpeg is still running.
        """
        return self._process is not None and self._process.poll() is None

    def _build_ffmpeg_command(self) -> list[str]:
        """Build FFmpeg command for video capture.

        Returns:
            list[str]: Command and arguments for subprocess.
        """
        return [
            "ffmpeg",
            "-fflags", "nobuffer",
            "-flags", "low_delay",
            "-thread_queue_size", "512",
            "-f", "v4l2",
            "-input_format", FFMPEG_INPUT_FORMAT,
            "-video_size", FFMPEG_INPUT_SIZE,
            "-framerate", str(FFMPEG_INPUT_FPS),
            "-i", FFMPEG_INPUT_DEVICE,
            "-vf", f"scale={FRAME_WIDTH}:{FRAME_HEIGHT},fps={PREVIEW_FPS}",
            "-pix_fmt", "bgr24",
            "-f", "rawvideo",
            "pipe:1",
        ]

    def _frame_reader(self) -> None:
        """Background thread that reads frames from FFmpeg stdout."""
        logger.info(f"Frame reader started, expecting {self._frame_size} bytes per frame")
        frames_read = 0

        while self._reader_running:
            raw = self._read_exactly(self._frame_size)
            if raw is None:
                logger.info(f"Frame reader EOF after {frames_read} frames")
                break

            frames_read += 1
            frame = np.frombuffer(raw, np.uint8).reshape(
                (FRAME_HEIGHT, FRAME_WIDTH, 3)
            )

            with self._frame_lock:
                self._latest_frame = frame

        logger.info("Frame reader thread exiting")

    def _read_exactly(self, n: int) -> Optional[bytes]:
        """Read exactly n bytes from FFmpeg pipe.

        Args:
            n: Number of bytes to read.

        Returns:
            Optional[bytes]: Bytes read, or None on EOF/error.
        """
        if not self._process or not self._process.stdout:
            return None

        buf = b""
        while len(buf) < n:
            try:
                chunk = self._process.stdout.read(n - len(buf))
            except (ValueError, OSError) as e:
                logger.error(f"Error reading from pipe: {e}")
                return None

            if not chunk:
                return None

            buf += chunk

        return buf
