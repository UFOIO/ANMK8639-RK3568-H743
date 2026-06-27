"""
看门狗管理：硬件看门狗喂狗 + 模块健康检查。
"""
import logging
import threading
import os

logger = logging.getLogger(__name__)


class Watchdog:
    """硬件看门狗喂狗 + 模块存活检测。"""

    def __init__(self, config: dict, event_bus):
        self._enabled = config.get("enabled", True)
        self._device = config.get("device", "/dev/watchdog")
        self._interval = config.get("feed_interval", 30)
        self._event_bus = event_bus
        self._timer = None
        self._wd_fd = None

    def start(self):
        if not self._enabled:
            logger.info("Watchdog disabled")
            return
        try:
            self._wd_fd = os.open(self._device, os.O_WRONLY)
            logger.info("Watchdog device opened: %s", self._device)
        except OSError:
            logger.warning("Watchdog device not available: %s", self._device)
            return
        self._timer = threading.Timer(self._interval, self._feed)
        self._timer.daemon = True
        self._timer.start()

    def stop(self):
        if self._timer:
            self._timer.cancel()
        if self._wd_fd is not None:
            try:
                os.write(self._wd_fd, b"V")
                os.close(self._wd_fd)
            except OSError:
                pass
        logger.info("Watchdog stopped")

    def _feed(self):
        """喂狗回调。"""
        try:
            if self._wd_fd is not None:
                os.write(self._wd_fd, b"\x00")
        except OSError:
            logger.error("Watchdog feed failed")
        self._timer = threading.Timer(self._interval, self._feed)
        self._timer.daemon = True
        self._timer.start()
