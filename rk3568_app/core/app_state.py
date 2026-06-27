"""
全局应用状态管理：线程安全的状态读写、健康度计算、事件日志。
"""
import threading
import time
import copy
from collections import deque


class AppState:
    """
    线程安全的全局状态存储。
    使用点号路径访问: state.get("drone.lat")
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._event_log = deque(maxlen=200)
        self._data = {
            "drone": {
                "connected": False,
                "flight_mode": "UNKNOWN",
                "armed": False,
                "lat": 0.0,
                "lon": 0.0,
                "alt": 0.0,
                "heading": 0,
                "battery_voltage": 0.0,
                "battery_remaining": 0,
                "last_heartbeat": 0.0,
                "last_position_update": 0.0,
                "gps_fix": 0,
                "satellites": 0,
                "roll": 0.0,
                "pitch": 0.0,
                "yaw": 0.0,
                "airspeed": 0.0,
                "groundspeed": 0.0,
                "climb_rate": 0.0,
                "wp_current": 0,
            },
            "hangar": {
                "stm32_connected": False,
                "door_status": "UNKNOWN",
                "lock_status": "UNKNOWN",
                "temperature": 0.0,
                "humidity": 0.0,
                "alarm_flags": 0,
                "last_status_update": 0.0,
            },
            "system": {
                "mqtt_connected": False,
                "last_mqtt_msg": 0.0,
                "last_camera_snapshot": 0.0,
                "cpu_temp": 0.0,
                "start_time": time.time(),
            },
        }

    def get(self, path: str):
        with self._lock:
            parts = path.split(".")
            node = self._data
            for p in parts:
                if isinstance(node, dict):
                    node = node.get(p)
                else:
                    return None
            return node

    def set(self, path: str, value):
        with self._lock:
            parts = path.split(".")
            node = self._data
            for p in parts[:-1]:
                if p not in node:
                    node[p] = {}
                node = node[p]
            node[parts[-1]] = value

    def log_event(self, source: str, level: str, message: str):
        with self._lock:
            self._event_log.append({
                "ts": time.time(),
                "source": source,
                "level": level,
                "message": message,
            })

    def get_events(self, count: int = 50) -> list:
        with self._lock:
            events = list(self._event_log)
            events.reverse()
            return events[:count]

    @property
    def uptime(self) -> float:
        return time.time() - self._data["system"]["start_time"]

    def to_dict(self) -> dict:
        with self._lock:
            result = copy.deepcopy(self._data)
            result["system"]["uptime"] = self.uptime
            return result

    def health(self) -> dict:
        now = time.time()
        with self._lock:
            d = self._data
            mqtt_last = d["system"]["last_mqtt_msg"]
            hb_last = d["drone"]["last_heartbeat"]
            pos_last = d["drone"]["last_position_update"]
            stm32_last = d["hangar"]["last_status_update"]
            cam_last = d["system"]["last_camera_snapshot"]

        def age(ts):
            return round(now - ts, 1) if ts > 0 else None

        result = {
            "mqtt": {"connected": d["system"]["mqtt_connected"], "last_msg_sec": age(mqtt_last)},
            "mavlink": {"connected": d["drone"]["connected"], "last_hb_sec": age(hb_last), "last_pos_sec": age(pos_last)},
            "stm32": {"connected": d["hangar"]["stm32_connected"], "last_status_sec": age(stm32_last)},
            "camera": {"last_snapshot_sec": age(cam_last)},
            "uptime": self.uptime,
        }

        issues = 0
        if not result["mavlink"]["connected"]:
            issues += 1
        if not result["stm32"]["connected"]:
            issues += 1

        if issues >= 2:
            result["overall"] = "critical"
        elif issues >= 1:
            result["overall"] = "degraded"
        else:
            result["overall"] = "healthy"

        return result
