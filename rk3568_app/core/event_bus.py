"""
内部事件总线：模块间解耦通信，发布-订阅模式。
"""
import logging
from collections import defaultdict
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class EventBus:
    """线程安全的事件总线。"""

    def __init__(self):
        self._subscribers = defaultdict(list)
        self._queue = Queue()

    def subscribe(self, event_type: str, callback):
        """订阅事件。callback 接收一个参数 data。"""
        self._subscribers[event_type].append(callback)
        logger.debug("Subscribed to %s: %s", event_type, callback.__name__)

    def publish(self, event_type: str, data=None):
        """发布事件（线程安全，放入队列异步处理）。"""
        self._queue.put((event_type, data))

    def poll(self, timeout: float = 0.05):
        """
        轮询处理事件队列。在主循环中周期调用。
        """
        try:
            event_type, data = self._queue.get(timeout=timeout)
            callbacks = self._subscribers.get(event_type, [])
            for cb in callbacks:
                try:
                    cb(data)
                except Exception:
                    logger.exception("Callback error for event %s", event_type)
            return True
        except Empty:
            return False
