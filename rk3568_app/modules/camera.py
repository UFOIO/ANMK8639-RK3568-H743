"""
摄像头模块：RTSP 拉流 + 定时截图。方案A: subprocess + ffmpeg（最简单）
"""
import logging
import os
import subprocess
import threading
import time

logger = logging.getLogger(__name__)


class CameraCapture:
    """RTSP 摄像头截图。"""

    def __init__(self, config: dict, app_state=None):
        self._enabled = config.get("enabled", True)
        self._rtsp_url = config.get("rtsp_url", "")
        self._interval = config.get("snapshot_interval", 30)
        self._snapshot_dir = config.get("snapshot_dir", "./data/snapshots")
        self._app_state = app_state
        self._running = False
        self._timer = None

    def start(self):
        if not self._enabled or not self._rtsp_url:
            logger.info("Camera disabled or no RTSP URL")
            return
        os.makedirs(self._snapshot_dir, exist_ok=True)
        self._running = True
        self._schedule_next()
        logger.info("Camera started: %s", self._rtsp_url)
        if self._app_state:
            self._app_state.log_event("camera", "info", "摄像头模块已启动")

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
        logger.info("Camera stopped")
        if self._app_state:
            self._app_state.log_event("camera", "info", "摄像头模块已停止")

    def capture_snapshot(self) -> str | None:
        ts = int(time.time())
        path = os.path.join(self._snapshot_dir, f"snap_{ts}.jpg")
        cmd = [
            "ffmpeg",
            "-rtsp_transport", "tcp",
            "-i", self._rtsp_url,
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            path,
        ]
        try:
            subprocess.run(cmd, timeout=10, capture_output=True, check=False)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                if self._app_state:
                    self._app_state.set("system.last_camera_snapshot", time.time())
                logger.debug("Snapshot saved: %s", path)
                return path
            else:
                logger.debug("Snapshot empty or failed")
                return None
        except subprocess.TimeoutExpired:
            logger.debug("Snapshot timeout")
            return None
        except FileNotFoundError:
            logger.error("ffmpeg not found, install: sudo apt install ffmpeg")
            return None

    def _schedule_next(self):
        if not self._running:
            return
        self._timer = threading.Timer(self._interval, self._snapshot_and_reschedule)
        self._timer.daemon = True
        self._timer.start()

    def _snapshot_and_reschedule(self):
        try:
            self.capture_snapshot()
        except Exception:
            logger.exception("Snapshot error")
        self._schedule_next()
