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
        """四级健康检查: healthy(绿) / stale(黄) / degraded(橙) / dead(红)
        每个模块返回 status + age, 整体取最差状态。
        """
        now = time.time()
        with self._lock:
            d = self._data
            mqtt_conn = d["system"]["mqtt_connected"]
            mqtt_last = d["system"]["last_mqtt_msg"]
            hb_last = d["drone"]["last_heartbeat"]
            pos_last = d["drone"]["last_position_update"]
            stm32_conn = d["hangar"]["stm32_connected"]
            stm32_last = d["hangar"]["last_status_update"]
            cam_last = d["system"]["last_camera_snapshot"]

        def _status(connected, ts, stale_s=5, dead_s=30):
            """返回 (status, age_sec).
            status: 'healthy' | 'stale' | 'dead'
            """
            if ts is None or ts <= 0:
                return ("dead", None) if not connected else ("dead", None)
            age = round(now - ts, 1)
            if not connected:
                return ("dead", age)
            if age < stale_s:
                return ("healthy", age)
            elif age < dead_s:
                return ("stale", age)
            else:
                return ("dead", age)

        mav_s, mav_age = _status(d["drone"]["connected"], hb_last)
        mqtt_s, mqtt_age = _status(mqtt_conn, mqtt_last)
        stm_s, stm_age = _status(stm32_conn, stm32_last)
        cam_s, cam_age = _status(True, cam_last, 30, 120)  # 摄像头30s/120s阈值放宽

        result = {
            "mavlink": {"status": mav_s, "connected": d["drone"]["connected"], "last_hb_sec": mav_age, "last_pos_sec": round(now - pos_last, 1) if pos_last > 0 else None},
            "mqtt": {"status": mqtt_s, "connected": mqtt_conn, "last_msg_sec": mqtt_age},
            "stm32": {"status": stm_s, "connected": stm32_conn, "last_status_sec": stm_age},
            "camera": {"status": cam_s, "last_snapshot_sec": cam_age},
            "uptime": self.uptime,
        }

        # 整体 = 最差模块状态
        levels = {"healthy": 0, "stale": 1, "degraded": 2, "dead": 3}
        worst_level = 0
        for mod in ["mavlink", "mqtt", "stm32", "camera"]:
            s = result[mod]["status"]
            lv = levels.get(s, 3)
            if lv > worst_level:
                worst_level = lv

        if worst_level == 3:
            result["overall"] = "critical"
        elif worst_level >= 2:
            result["overall"] = "degraded"
        elif worst_level >= 1:
            result["overall"] = "degraded"
        else:
            result["overall"] = "healthy"

        return result
