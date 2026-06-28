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
        self._rtsp_url = self._build_rtsp_url(config)
        self._snapshot_timeout = config.get("snapshot_timeout", 10)
        self._ffmpeg_extra = config.get("ffmpeg_extra", "")
        self._interval = config.get("snapshot_interval", 30)
        self._snapshot_dir = config.get("snapshot_dir", "./data/snapshots")
        self._app_state = app_state
        self._running = False
        self._timer = None

    def _build_rtsp_url(self, config):
        """Build RTSP URL from structured fields or use direct override."""
        direct = config.get("rtsp_url", "")
        if direct:
            return direct
        ip = config.get("ip", "192.168.1.64")
        port = config.get("port", 554)
        user = config.get("username", "admin")
        pwd = config.get("password", "")
        ch = config.get("channel", 1)
        stream = config.get("stream", 0)
        # Build standard RTSP URL
        url = f"rtsp://{ip}:{port}/user={user}&password={pwd}&channel={ch}&stream={stream}.sdp?"
        logger.debug("Built RTSP URL: %s", url)
        return url

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
                fsize = os.path.getsize(path)
                print("Camera SNAP: " + os.path.basename(path) + " " + str(fsize//1024) + "KB")
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
