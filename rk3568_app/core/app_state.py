"""
全局应用状态管理：线程安全的状态读写、健康度计算、事件日志。
"""
import threading
import time
import copy
import os
from collections import deque



_prev_cpu_fields = None

def _get_system_info():
    """??????: CPU(??/proc/stat)/RAM/Disk"""
    global _prev_cpu_fields
    info = {"cpu": 0, "ram_pct": 0, "ram_used": "0M", "ram_total": "0M",
            "disk_pct": 0, "disk_used": "0G", "disk_total": "0G"}
    try:
        with open("/proc/stat") as f:
            fields = [int(x) for x in f.readline().split()[1:8]]
        if _prev_cpu_fields:
            pt, pi = sum(_prev_cpu_fields), _prev_cpu_fields[3] + _prev_cpu_fields[4]
            ct, ci = sum(fields), fields[3] + fields[4]
            td, id_ = ct - pt, ci - pi
            if td > 0:
                info["cpu"] = round((td - id_) / td * 100, 1)
        _prev_cpu_fields = fields
    except Exception:
        pass
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                p = line.split(":")
                if len(p) == 2:
                    mem[p[0].strip()] = int(p[1].strip().split()[0])
        total = mem.get("MemTotal", 1)
        avail = mem.get("MemAvailable", 1)
        used = total - avail
        info["ram_pct"] = round(used / total * 100, 1)
        info["ram_used"] = str(used // 1024) + "M"
        info["ram_total"] = str(total // 1024) + "M"
    except Exception:
        pass
    try:
        st = os.statvfs("/")
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        used = total - free
        info["disk_pct"] = round(used / total * 100, 1)
        info["disk_used"] = str(round(used / (1024**3), 1)) + "G"
        info["disk_total"] = str(round(total / (1024**3), 1)) + "G"
    except Exception:
        pass
    return info

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
        """Health check + full telemetry for Web UI dashboard."""
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
            if ts is None or ts <= 0:
                return ("dead", None)
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
        cam_s, cam_age = _status(True, cam_last, 30, 120)

        result = {
            "mavlink": {"status": mav_s, "connected": d["drone"]["connected"], "last_hb_sec": mav_age, "last_pos_sec": round(now - pos_last, 1) if pos_last > 0 else None},
            "mqtt": {"status": mqtt_s, "connected": mqtt_conn, "last_msg_sec": mqtt_age},
            "stm32": {"status": stm_s, "connected": stm32_conn, "last_status_sec": stm_age},
            "camera": {"status": cam_s, "last_snapshot_sec": cam_age},
            "uptime": self.uptime,
            "drone": {
                "mode": d["drone"]["flight_mode"],
                "armed": d["drone"]["armed"],
                "satellites": d["drone"]["satellites"],
                "gps_fix": d["drone"]["gps_fix"],
                "alt_rel": round(d["drone"]["alt"], 1),
                "groundspeed": round(d["drone"]["groundspeed"], 1),
                "battery": d["drone"]["battery_remaining"],
                "voltage": round(d["drone"]["battery_voltage"], 2),
                "lat": round(d["drone"]["lat"], 6),
                "lon": round(d["drone"]["lon"], 6),
                "heading": d["drone"]["heading"],
                "roll": round(d["drone"]["roll"], 1),
                "pitch": round(d["drone"]["pitch"], 1),
                "wp_current": d["drone"]["wp_current"],
            },
            "hangar": {
                "door": d["hangar"]["door_status"],
                "lock": d["hangar"]["lock_status"],
                "temp": round(d["hangar"]["temperature"], 1),
                "humidity": round(d["hangar"]["humidity"], 1),
                "alarm_flags": d["hangar"]["alarm_flags"],
            },
            "system": _get_system_info(),
            "events": list(self._event_log)[-20:],
        }

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
