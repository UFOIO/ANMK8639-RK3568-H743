"""
MAVLink 无人机通信模块：TCP连接机载4G图数一体模块，解析MAVLink v2消息。
"""
import logging
import socket
import threading
import time
from pymavlink import mavutil

from protocol.mavlink_map import MESSAGE_MAP, mode_name, is_rtl

logger = logging.getLogger(__name__)


class MAVLinkClient:
    """MAVLink TCP 客户端。连接无人机4G图数一体模块。"""

    def __init__(self, config: dict, event_bus, app_state):
        self._host = config.get("host", "127.0.0.1")
        self._port = config.get("port", 5760)
        self._hb_timeout = config.get("heartbeat_timeout", 5)
        self._system_id = config.get("system_id", 255)

        self._event_bus = event_bus
        self._app_state = app_state
        self._mav = None
        self._running = False
        self._last_hb = 0.0
        self._msg_count = 0

    def start(self):
        self._running = True
        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()
        logger.info("MAVLink started -> %s:%d", self._host, self._port)
        self._app_state.log_event("mavlink", "info", "MAVLink模块已启动，等待无人机连接")

    def stop(self):
        self._running = False
        if self._mav:
            self._mav.close()
            self._mav = None
        logger.info("MAVLink stopped")
        self._app_state.log_event("mavlink", "info", "MAVLink模块已停止")

    def _connect(self) -> bool:
        if not self._host or "\u8bf7\u586b" in self._host:
            return False
        try:
            conn_str = f"tcp:{self._host}:{self._port}"
            self._mav = mavutil.mavlink_connection(
                conn_str, source_system=self._system_id
            )
            logger.info("MAVLink TCP connected: %s", conn_str)
            return True
        except Exception:
            logger.error("MAVLink connect failed: %s:%d (will retry)", self._host, self._port)
            return False

    def _recv_loop(self):
        while self._running:
            if self._mav is None:
                if not self._connect():
                    time.sleep(3)
                    continue

            try:
                msg = self._mav.recv_match(blocking=True, timeout=1.0)
                if msg is None:
                    if time.time() - self._last_hb > self._hb_timeout:
                        self._on_lost()
                    continue

                self._msg_count += 1
                msg_id = msg.get_msgId()

                handlers = {
                    0:   self._handle_heartbeat,
                    1:   self._handle_sys_status,
                    24:  self._handle_gps_raw,
                    30:  self._handle_attitude,
                    33:  self._handle_position,
                    42:  self._handle_mission_current,
                    74:  self._handle_vfr,
                    147: self._handle_battery,
                    253: self._handle_statustext,
                }
                handler = handlers.get(msg_id)
                if handler:
                    handler(msg)

            except (socket.timeout, ConnectionError, OSError):
                logger.warning("MAVLink connection lost")
                self._mav = None
                self._app_state.set("drone.connected", False)
                self._event_bus.publish("DRONE_DISCONNECTED", {"reason": "connection_lost"})
                self._app_state.log_event("mavlink", "warn", "MAVLink连接断开，将自动重连")
                print("MAVLink DISCONNECTED", flush=True)
                time.sleep(3)
            except Exception:
                logger.exception("MAVLink recv error")
                time.sleep(1)

    def _handle_heartbeat(self, msg):
        self._last_hb = time.time()
        custom_mode = msg.custom_mode
        flight_mode = mode_name(custom_mode)
        armed = (msg.base_mode & 0x80) != 0

        was_connected = self._app_state.get("drone.connected")
        self._app_state.set("drone.connected", True)
        self._app_state.set("drone.flight_mode", flight_mode)
        self._app_state.set("drone.armed", armed)
        self._app_state.set("drone.last_heartbeat", self._last_hb)

        self._event_bus.publish("DRONE_HEARTBEAT", {"mode": flight_mode, "armed": armed})
        print("MAVLink HB: mode=" + str(flight_mode, flush=True) + " armed=" + str(armed))

        if not was_connected:
            self._app_state.log_event("mavlink", "info",
                                       "无人机已连接: 模式=" + flight_mode + ", 武装=" + str(armed))

        if is_rtl(custom_mode):
            self._event_bus.publish("DRONE_RTL", {"mode": flight_mode})

    def _handle_position(self, msg):
        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        self._app_state.set("drone.lat", lat)
        self._app_state.set("drone.lon", lon)
        self._app_state.set("drone.alt", msg.relative_alt / 1000.0)
        self._app_state.set("drone.heading", msg.hdg // 100)
        self._app_state.set("drone.last_position_update", time.time())
        print("MAVLink GPS: lat=" + str(lat, flush=True)[:8] + " lon=" + str(lon)[:8] + " alt=" + str(round(msg.relative_alt/1000.0,1)) + "m sats=" + str(msg.satellites_visible) + " fix=" + str(msg.fix_type))
        self._event_bus.publish("DRONE_POSITION", {
            "lat": lat, "lon": lon,
            "alt": msg.relative_alt / 1000.0,
            "heading": msg.hdg // 100,
        })

    def _handle_gps_raw(self, msg):
        self._app_state.set("drone.gps_fix", msg.fix_type)
        self._app_state.set("drone.satellites", msg.satellites_visible)
        if msg.fix_type < 3:
            logger.debug("GPS fix degraded: type=%d, sats=%d",
                         msg.fix_type, msg.satellites_visible)

    def _handle_attitude(self, msg):
        self._app_state.set("drone.roll", msg.roll)
        self._app_state.set("drone.pitch", msg.pitch)
        self._app_state.set("drone.yaw", msg.yaw)

    def _handle_battery(self, msg):
        remaining = msg.battery_remaining if msg.battery_remaining != -1 else 0
        voltage = 0.0
        if msg.voltages and len(msg.voltages) > 0:
            voltage = msg.voltages[0] / 1000.0
        self._app_state.set("drone.battery_remaining", remaining)
        self._app_state.set("drone.battery_voltage", voltage)
        print("MAVLink BATT: " + str(remaining, flush=True) + "% " + str(round(voltage/1000.0,1)) + "V")

        threshold = 20
        if 0 < remaining < threshold:
            self._event_bus.publish("DRONE_BATTERY_LOW", {"remaining": remaining, "voltage": voltage})
            self._app_state.log_event("mavlink", "warn", "无人机电池电量低: " + str(remaining) + "%")

    def _handle_vfr(self, msg):
        self._app_state.set("drone.airspeed", msg.airspeed)
        self._app_state.set("drone.groundspeed", msg.groundspeed)
        self._app_state.set("drone.climb_rate", msg.climb)

    def _handle_sys_status(self, msg):
        sensors_health = msg.onboard_control_sensors_health
        if sensors_health != 0:
            logger.debug("SYS_STATUS sensors_health=0x%08X", sensors_health)

    def _handle_mission_current(self, msg):
        self._app_state.set("drone.wp_current", msg.seq)

    def _handle_statustext(self, msg):
        text = msg.text.strip() if msg.text else ""
        logger.info("Drone STATUSTEXT [%d]: %s", msg.severity, text)
        self._app_state.log_event("mavlink",
                                   "warn" if msg.severity >= 3 else "info",
                                   "无人机: " + text)
        if msg.severity >= 4:
            self._event_bus.publish("DRONE_STATUSTEXT", {
                "severity": msg.severity, "text": text,
            })

    def _on_lost(self):
        self._app_state.set("drone.connected", False)
        logger.warning("MAVLink heartbeat timeout (%.1fs)", self._hb_timeout)
        self._event_bus.publish("DRONE_DISCONNECTED", {"reason": "heartbeat_timeout"})
        self._app_state.log_event("mavlink", "error",
                                   "无人机心跳超时(" + str(self._hb_timeout) + "s)，连接丢失")
