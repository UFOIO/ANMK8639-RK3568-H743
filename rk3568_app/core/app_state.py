"""
鍏ㄥ眬搴旂敤鐘舵€佺鐞嗭細绾跨▼瀹夊叏鐨勭姸鎬佽鍐欍€佸仴搴峰害璁＄畻銆佷簨浠舵棩蹇椼€?
"""
import threading
import time
import copy
import os
from collections import deque



_prev_cpu_fields = None
_cpu_cached = 0.0
_cpu_last_ts = 0.0
_CPU_INTERVAL = 2.0

def _get_system_info():
    """??????: CPU(??/proc/stat)/RAM/Disk"""
    global _prev_cpu_fields
    info = {"cpu": 0, "ram_pct": 0, "ram_used": "0M", "ram_total": "0M",
            "disk_pct": 0, "disk_used": "0G", "disk_total": "0G",
            "mosquitto": False,
            "cpu_percent": 0, "ram_percent": 0, "disk_percent": 0,
            "cpu_temp": 0, "network": "unknown"}
    try:
        with open("/proc/stat") as f:
            fields = [int(x) for x in f.readline().split()[1:8]]
        if _prev_cpu_fields:
            pt, pi = sum(_prev_cpu_fields), _prev_cpu_fields[3] + _prev_cpu_fields[4]
            ct, ci = sum(fields), fields[3] + fields[4]
            td, id_ = ct - pt, ci - pi
            if td > 0:
                global _cpu_cached, _cpu_last_ts
                now = time.time()
                if now - _cpu_last_ts >= _CPU_INTERVAL:
                    _cpu_cached = round((td - id_) / td * 100, 1)
                    _cpu_last_ts = now
                info["cpu"] = _cpu_cached; info["cpu_percent"] = _cpu_cached
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
        info["ram_pct"] = round(used / total * 100, 1); info["ram_percent"] = info["ram_pct"]
        info["ram_used"] = str(used // 1024) + "M"
        info["ram_total"] = str(total // 1024) + "M"
    except Exception:
        pass
    try:
        st = os.statvfs("/")
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        used = total - free
        info["disk_pct"] = round(used / total * 100, 1); info["disk_percent"] = info["disk_pct"]
        info["disk_used"] = str(round(used / (1024**3), 1)) + "G"
        info["disk_total"] = str(round(total / (1024**3), 1)) + "G"
    except Exception:
        pass
    # Mosquitto Broker 杩涚▼妫€娴?(绔彛1883)
    try:
        with open("/proc/net/tcp", "r") as f:
            for line in f:
                if "00001D8B" in line:
                    info["mosquitto"] = True
                    break
    except Exception:
        pass
    # CPU温度
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            info["cpu_temp"] = round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass
    # 网络连通性检测
    try:
        import socket
        socket.setdefaulttimeout(1)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        s.close()
        info["network"] = "connected"
    except Exception:
        info["network"] = "disconnected"
    return info

def _check_gimbal_wifi_once():
    """检查 4G WiFi (H4T_4G) 当前是否激活. 返回 (connected: bool, ssid: str)"""
    try:
        import subprocess
        # 1) 查所有 active 的 wifi connection
        r = subprocess.run(
            ["nmcli", "-t", "-f", "NAME,STATE", "connection", "show", "--active"],
            capture_output=True, text=True, timeout=3
        )
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                # nmcli -t 输出格式: NAME:STATE
                parts = line.split(":")
                if len(parts) >= 2 and parts[0].startswith("H4T") and parts[1] == "activated":
                    return True, parts[0]
        # 2) fallback: 查 wlan0 是否有 IP
        r2 = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True, text=True, timeout=2
        )
        if r2.returncode == 0 and "inet " in r2.stdout:
            # 提取 SSID (从 iwconfig 拿, 拿不到就用 H4T_4G 占位)
            r3 = subprocess.run(
                ["iwgetid", "-r"],
                capture_output=True, text=True, timeout=2
            )
            ssid = r3.stdout.strip() if r3.returncode == 0 else "H4T_4G"
            return True, ssid
        return False, ""
    except Exception:
        return False, ""


class AppState:
    """
    绾跨▼瀹夊叏鐨勫叏灞€鐘舵€佸瓨鍌ㄣ€?
    浣跨敤鐐瑰彿璺緞璁块棶: state.get("drone.lat")
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
                "data_fresh": False,  # 鏂仈鍚庡彉False锛屾敹鍒颁綅缃洿鏂板悗鍙楾rue
                # Frozen position for dead-reckoning (preserved on disconnect)
                "frozen_lat": 0.0, "frozen_lon": 0.0, "frozen_alt": 0.0,
                "frozen_heading": 0, "frozen_groundspeed": 0.0, "frozen_climb_rate": 0.0,
                "frozen_flight_mode": "UNKNOWN", "frozen_battery_remaining": 0,
                "protection_status": {},
                # IMU
                "accel_x": 0, "accel_y": 0, "accel_z": 0,
                "gyro_x": 0, "gyro_y": 0, "gyro_z": 0,
                # Pressure
                "press_abs": 0.0, "temperature": 0.0,
                # Local NED
                "local_x": 0.0, "local_y": 0.0, "local_z": 0.0,
                "local_vx": 0.0, "local_vy": 0.0, "local_vz": 0.0,
                # Navigation
                "nav_roll": 0.0, "nav_pitch": 0.0, "nav_bearing": 0,
                "wp_distance": 0.0,
                # Terrain
                "terrain_alt": 0.0,
                # Battery 2
                "battery2_remaining": 0, "battery2_voltage": 0.0,
                # AHRS
                "ahrs_omega_x": 0.0, "ahrs_omega_y": 0.0, "ahrs_omega_z": 0.0,
                # Extended state
                "vtol_state": 0, "landed_state": 0,
                # Wind
                "wind_x": 0.0, "wind_y": 0.0, "wind_z": 0.0,
                # EKF
                "ekf_health": 0, "ekf_pos_horiz": 0.0, "ekf_pos_vert": 0.0,
                # Vibration
                "vib_x": 0.0, "vib_y": 0.0, "vib_z": 0.0,
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
                "last_camera_snapshot": 0,
            "gimbal_wifi_connected": False,
            "gimbal_wifi_ssid": "",
                "cpu_temp": 0.0,
                "start_time": time.time(),
            },
        }

        # 启动 4G WiFi 状态后台监控线程 (每 10 秒检查一次)
        self._gimbal_wifi_thread = threading.Thread(target=self._gimbal_wifi_loop, daemon=True)
        self._gimbal_wifi_thread.start()

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

    def _gimbal_wifi_loop(self):
        """每 10 秒检查一次 4G WiFi 状态, 写入 system.gimbal_wifi_*"""
        import logging
        log = logging.getLogger(__name__)
        while True:
            try:
                connected, ssid = _check_gimbal_wifi_once()
                with self._lock:
                    old_c = self._data["system"].get("gimbal_wifi_connected")
                    old_s = self._data["system"].get("gimbal_wifi_ssid", "")
                    self._data["system"]["gimbal_wifi_connected"] = connected
                    self._data["system"]["gimbal_wifi_ssid"] = ssid if connected else ""
                # 状态变化时记日志
                if old_c != connected:
                    log.info("4G WiFi 状态变化: %s -> %s (ssid=%s)", old_c, connected, ssid)
            except Exception:
                pass
            time.sleep(10)
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
                "data_fresh": d["drone"]["data_fresh"],
                "protection": d["drone"].get("protection_status", {}),
                # Extended telemetry
                "airspeed": round(d["drone"]["airspeed"], 1),
                "climb": round(d["drone"]["climb_rate"], 1),
                "yaw": round(d["drone"]["yaw"], 1),
                "temperature": round(d["drone"]["temperature"], 1),
                "nav_bearing": d["drone"]["nav_bearing"],
                "wp_distance": round(d["drone"]["wp_distance"], 1),
                "terrain_alt": round(d["drone"]["terrain_alt"], 1),
                "ekf_health": d["drone"]["ekf_health"],
                "ekf_horiz": round(d["drone"]["ekf_pos_horiz"], 3),
                "ekf_vert": round(d["drone"]["ekf_pos_vert"], 3),
                "vtol_state": d["drone"]["vtol_state"],
                "landed_state": d["drone"]["landed_state"],
                "wind_x": round(d["drone"]["wind_x"], 1),
                "wind_y": round(d["drone"]["wind_y"], 1),
                "vib_x": round(d["drone"]["vib_x"], 2),
                "vib_y": round(d["drone"]["vib_y"], 2),
                "vib_z": round(d["drone"]["vib_z"], 2),
                "battery2": d["drone"]["battery2_remaining"],
            },
            "hangar": {
                "door": d["hangar"]["door_status"],
                "lock": d["hangar"]["lock_status"],
                "temp": round(d["hangar"]["temperature"], 1),
                "humidity": round(d["hangar"]["humidity"], 1),
                "alarm_flags": d["hangar"]["alarm_flags"],
            },
            "system": _get_system_info(),
            "gimbal_wifi": {"connected": d["system"].get("gimbal_wifi_connected", False),
                            "ssid": d["system"].get("gimbal_wifi_ssid", "")},
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