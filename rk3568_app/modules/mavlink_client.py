# -*- coding: utf-8 -*-
""" 
MAVLink 无人机通信模块 — 基于 pymavlink (ArduPilot dialect)

参考:
  pymavlink/examples/apmsetrate.py — request_data_stream_send 官方用法
  https://www.ardusub.com/developers/pymavlink.html
  https://github.com/ArduPilot/pymavlink
"""
import logging
import socket
import threading
import time
import math
from pymavlink import mavutil

from protocol.mavlink_map import mode_name, is_rtl

logger = logging.getLogger(__name__)

HANDLERS = {}

def handler(msg_type: str):
    def decorator(fn):
        HANDLERS[msg_type] = fn
        return fn
    return decorator


class MAVLinkClient:

    def __init__(self, config: dict, event_bus, app_state):
        self._connection = config.get("connection", "tcp")
        self._host = config.get("host", "127.0.0.1")
        self._port = config.get("port", 5760)
        self._device = config.get("device", "/dev/ttyACM0")
        self._baudrate = config.get("baudrate", 115200)
        self._telem_rate = min(config.get("telem_rate", 4), 10)
        self._hb_timeout = config.get("heartbeat_timeout", 5)
        self._system_id = config.get("system_id", 255)
        self._event_bus = event_bus
        self._app_state = app_state
        self._mav = None
        self._running = False
        self._last_hb = 0.0
        self._msg_count = 0
        self._lost_reported = False
        self._lost_since = 0.0
        self._home_lat = 0.0
        self._home_lon = 0.0
        self._stream_active = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()
        if self._connection == "serial":
            logger.info("MAVLink started -> serial:%s @ %d", self._device, self._baudrate)
        else:
            logger.info("MAVLink started -> %s:%d", self._host, self._port)

    def stop(self):
        self._running = False
        if self._mav:
            self._mav.close()
            self._mav = None
        logger.info("MAVLink stopped")

    # ── 连接 ──

    def _connect(self) -> bool:
        try:
            if self._connection == "serial":
                self._mav = mavutil.mavlink_connection(
                    self._device, baud=self._baudrate,
                    source_system=self._system_id, dialect='ardupilotmega')
                logger.info("MAVLink serial opened: %s, waiting heartbeat...", self._device)
            else:
                if not self._host or "\u8bf7\u586b" in self._host:
                    return False
                self._mav = mavutil.mavlink_connection(
                    f"tcp:{self._host}:{self._port}",
                    source_system=self._system_id, dialect='ardupilotmega')
                logger.info("MAVLink TCP: %s:%d, waiting heartbeat...", self._host, self._port)

            self._mav.wait_heartbeat(timeout=10)
            logger.info("MAVLink connected: sys=%d comp=%d",
                        self._mav.target_system, self._mav.target_component)
            self._app_state.log_event("mavlink", "info",
                "\u65e0\u4eba\u673a\u5df2\u8fde\u63a5 sys=%d" % self._mav.target_system)
            return True
        except Exception as e:
            logger.error("MAVLink connect failed: %s", str(e))
            if self._mav:
                try: self._mav.close()
                except: pass
                self._mav = None
            return False

    # ── 请求数据流 (官方 apmsetrate.py 方式) ──

    def _request_stream(self, rate_hz=None):
        """request_data_stream_send(MAV_DATA_STREAM_ALL, rate, 1)
        
        ArduPilot 官方标准: 一条指令请求全部标准遥测.
        参考: pymavlink/examples/apmsetrate.py
        """
        if self._mav is None:
            return
        try:
            hz = rate_hz if rate_hz else max(1, min(self._telem_rate, 10))
            self._mav.mav.request_data_stream_send(
                self._mav.target_system, self._mav.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL, hz, 1)
            self._stream_active = True
            logger.info("MAVLink DATA_STREAM_ALL @ %dHz (sys=%d comp=%d)",
                        hz, self._mav.target_system, self._mav.target_component)
        except Exception as e:
            logger.error("MAVLink request stream failed: %s", str(e))

    # ── 主循环 ──

    def _recv_loop(self):
        while self._running:
            if self._mav is None:
                if not self._connect():
                    time.sleep(3)
                    continue
                # 连接成功 → burst 高频刷新
                self._request_stream(rate_hz=min(self._telem_rate * 2, 10))
                # 3秒后恢复正常频率
                def _restore():
                    time.sleep(3)
                    self._request_stream()
                threading.Thread(target=_restore, daemon=True).start()

            try:
                msg = self._mav.recv_match(blocking=True, timeout=1.0)
                if msg is None:
                    if time.time() - self._last_hb > self._hb_timeout:
                        self._on_lost()
                    continue
                self._msg_count += 1
                handler_fn = HANDLERS.get(msg.get_type())
                if handler_fn:
                    handler_fn(self, msg)
            except (socket.timeout, ConnectionError, OSError):
                logger.warning("MAVLink connection lost")
                self._mav = None
                self._stream_active = False
                self._app_state.set("drone.connected", False)
                self._last_hb = 0.0
                print("MAVLink DISCONNECTED", flush=True)
                time.sleep(2)
            except Exception:
                logger.exception("MAVLink recv error")
                time.sleep(1)

    # ═══════════════════════════════════════════════════
    # 消息处理器
    # ═══════════════════════════════════════════════════

    @handler("HEARTBEAT")
    def _on_heartbeat(self, msg):
        self._last_hb = time.time()
        flight_mode = mode_name(msg.custom_mode)
        armed = (msg.base_mode & 0x80) != 0
        was_connected = self._app_state.get("drone.connected")
        self._app_state.set("drone.connected", True)
        self._app_state.set("drone.flight_mode", flight_mode)
        self._app_state.set("drone.armed", armed)
        self._app_state.set("drone.last_heartbeat", self._last_hb)
        self._app_state.set("drone.type", msg.type)
        self._app_state.set("drone.autopilot", msg.autopilot)
        self._event_bus.publish("DRONE_HEARTBEAT", {"mode": flight_mode, "armed": armed})
        print("MAVLink HB: mode=" + str(flight_mode) + " armed=" + str(armed), flush=True)
        if not was_connected:
            self._lost_reported = False
            self._lost_since = 0.0
            for key in ["lat","lon","alt","heading","groundspeed","climb_rate",
                         "flight_mode","battery_remaining"]:
                self._app_state.set("drone.frozen_" + key, 0)
            self._app_state.log_event("mavlink", "info",
                "\u65e0\u4eba\u673a\u5df2\u8fde\u63a5: \u6a21\u5f0f=" + flight_mode)
        if is_rtl(msg.custom_mode):
            self._event_bus.publish("DRONE_RTL", {"mode": flight_mode})

    @handler("GLOBAL_POSITION_INT")
    def _on_global_position(self, msg):
        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        alt = msg.relative_alt / 1000.0
        hdg = msg.hdg // 100
        self._app_state.set("drone.lat", lat)
        self._app_state.set("drone.lon", lon)
        self._app_state.set("drone.alt", alt)
        self._app_state.set("drone.heading", hdg)
        self._app_state.set("drone.last_position_update", time.time())
        if not self._app_state.get("drone.data_fresh"):
            self._app_state.set("drone.data_fresh", True)
        print("MAVLink GPS: lat=" + str(round(lat,6)) + " lon=" + str(round(lon,6)) +
              " alt=" + str(round(alt,1)) + "m hdg=" + str(hdg) + "\u00b0", flush=True)
        self._event_bus.publish("DRONE_POSITION", {
            "lat": lat, "lon": lon, "alt": alt, "heading": hdg})

    @handler("GPS_RAW_INT")
    def _on_gps_raw(self, msg):
        self._app_state.set("drone.gps_fix", msg.fix_type)
        self._app_state.set("drone.satellites", msg.satellites_visible)
        self._app_state.set("drone.gps_hdop", round(msg.eph / 100.0, 1) if msg.eph < 65535 else 99.9)
        self._app_state.set("drone.gps_vdop", round(msg.epv / 100.0, 1) if msg.epv < 65535 else 99.9)

    @handler("ATTITUDE")
    def _on_attitude(self, msg):
        self._app_state.set("drone.roll", round(math.degrees(msg.roll), 1))
        self._app_state.set("drone.pitch", round(math.degrees(msg.pitch), 1))
        self._app_state.set("drone.yaw", round(math.degrees(msg.yaw), 1))
        self._app_state.set("drone.rollspeed", round(math.degrees(msg.rollspeed), 2))
        self._app_state.set("drone.pitchspeed", round(math.degrees(msg.pitchspeed), 2))
        self._app_state.set("drone.yawspeed", round(math.degrees(msg.yawspeed), 2))

    @handler("VFR_HUD")
    def _on_vfr_hud(self, msg):
        self._app_state.set("drone.airspeed", round(msg.airspeed, 1))
        self._app_state.set("drone.groundspeed", round(msg.groundspeed, 1))
        self._app_state.set("drone.climb_rate", round(msg.climb, 1))
        self._app_state.set("drone.throttle_pct", msg.throttle)

    @handler("BATTERY_STATUS")
    def _on_battery(self, msg):
        remaining = msg.battery_remaining if msg.battery_remaining != -1 else 0
        voltage = 0.0
        if msg.voltages and len(msg.voltages) > 0:
            voltage = msg.voltages[0] / 1000.0
        current = msg.current_battery / 100.0 if msg.current_battery != -1 else 0.0
        self._app_state.set("drone.battery_remaining", remaining)
        self._app_state.set("drone.battery_voltage", round(voltage, 2))
        self._app_state.set("drone.battery_current", round(current, 1))
        print("MAVLink BATT: " + str(remaining) + "% " + str(round(voltage,1)) + "V "
              + str(round(current,1)) + "A", flush=True)

    @handler("SYS_STATUS")
    def _on_sys_status(self, msg):
        self._app_state.set("drone.sensors_health", msg.onboard_control_sensors_health)
        self._app_state.set("drone.errors_count1", msg.errors_count1)

    @handler("RAW_IMU")
    def _on_raw_imu(self, msg):
        self._app_state.set("drone.accel_x", msg.xacc)
        self._app_state.set("drone.accel_y", msg.yacc)
        self._app_state.set("drone.accel_z", msg.zacc)
        self._app_state.set("drone.gyro_x", msg.xgyro)
        self._app_state.set("drone.gyro_y", msg.ygyro)
        self._app_state.set("drone.gyro_z", msg.zgyro)

    @handler("SCALED_PRESSURE")
    def _on_scaled_pressure(self, msg):
        self._app_state.set("drone.press_abs", msg.press_abs)
        self._app_state.set("drone.temperature", round(msg.temperature / 100.0, 1))

    @handler("LOCAL_POSITION_NED")
    def _on_local_position(self, msg):
        self._app_state.set("drone.local_x", msg.x)
        self._app_state.set("drone.local_y", msg.y)
        self._app_state.set("drone.local_z", msg.z)
        self._app_state.set("drone.local_vx", msg.vx)
        self._app_state.set("drone.local_vy", msg.vy)
        self._app_state.set("drone.local_vz", msg.vz)

    @handler("NAV_CONTROLLER_OUTPUT")
    def _on_nav_controller(self, msg):
        self._app_state.set("drone.nav_roll", msg.nav_roll)
        self._app_state.set("drone.nav_pitch", msg.nav_pitch)
        self._app_state.set("drone.nav_bearing", msg.nav_bearing)
        self._app_state.set("drone.wp_distance", msg.wp_dist)

    @handler("MISSION_CURRENT")
    def _on_mission_current(self, msg):
        self._app_state.set("drone.wp_current", msg.seq)

    @handler("STATUSTEXT")
    def _on_statustext(self, msg):
        text = msg.text.strip() if msg.text else ""
        logger.info("Drone STATUSTEXT [%d]: %s", msg.severity, text)
        self._app_state.log_event("mavlink",
            "warn" if msg.severity >= 3 else "info", "\u65e0\u4eba\u673a: " + text)

    @handler("EXTENDED_SYS_STATE")
    def _on_extended_state(self, msg):
        self._app_state.set("drone.vtol_state", msg.vtol_state)
        self._app_state.set("drone.landed_state", msg.landed_state)

    @handler("AHRS")
    def _on_ahrs(self, msg):
        self._app_state.set("drone.ahrs_omega_x", msg.omegaIx)
        self._app_state.set("drone.ahrs_omega_y", msg.omegaIy)
        self._app_state.set("drone.ahrs_omega_z", msg.omegaIz)

    @handler("ESTIMATOR_STATUS")
    def _on_estimator(self, msg):
        self._app_state.set("drone.ekf_health", msg.health_flags)
        self._app_state.set("drone.ekf_pos_horiz", msg.pos_horiz_accuracy)
        self._app_state.set("drone.ekf_pos_vert", msg.pos_vert_accuracy)

    @handler("WIND_COV")
    def _on_wind(self, msg):
        self._app_state.set("drone.wind_x", msg.wind_x)
        self._app_state.set("drone.wind_y", msg.wind_y)
        self._app_state.set("drone.wind_z", msg.wind_z)

    @handler("VIBRATION")
    def _on_vibration(self, msg):
        self._app_state.set("drone.vib_x", msg.vibration_x)
        self._app_state.set("drone.vib_y", msg.vibration_y)
        self._app_state.set("drone.vib_z", msg.vibration_z)

    @handler("TERRAIN_REPORT")
    def _on_terrain(self, msg):
        self._app_state.set("drone.terrain_alt", msg.current_height)

    @handler("AUTOPILOT_VERSION")
    def _on_autopilot_version(self, msg):
        self._app_state.set("drone.ap_version", msg.flight_sw_version)
        self._app_state.set("drone.ap_board_version", msg.board_version)

    @handler("HOME_POSITION")
    def _on_home_position(self, msg):
        self._home_lat = msg.latitude / 1e7
        self._home_lon = msg.longitude / 1e7
        self._app_state.set("drone.home_lat", self._home_lat)
        self._app_state.set("drone.home_lon", self._home_lon)
        self._app_state.set("drone.home_alt", msg.altitude / 1000.0)

    @handler("RANGEFINDER")
    def _on_rangefinder(self, msg):
        self._app_state.set("drone.rangefinder", round(msg.distance, 2))

    @handler("RADIO_STATUS")
    def _on_radio_status(self, msg):
        self._app_state.set("drone.rssi", msg.rssi)
        self._app_state.set("drone.radio_rxerrors", msg.rxerrors)
        self._app_state.set("drone.radio_noise", msg.noise)
        self._app_state.set("drone.radio_remrssi", msg.remrssi)

    @handler("POWER_STATUS")
    def _on_power_status(self, msg):
        self._app_state.set("drone.vcc", round(msg.Vcc / 100.0, 2))
        self._app_state.set("drone.vservo", round(msg.Vservo / 100.0, 2))

    @handler("EKF_STATUS_REPORT")
    def _on_ekf_status_report(self, msg):
        self._app_state.set("drone.ekf_flags", msg.flags)
        self._app_state.set("drone.ekf_velocity_variance", round(msg.velocity_variance, 4))
        self._app_state.set("drone.ekf_compass_variance", round(msg.compass_variance, 4))

    @handler("SMART_BATTERY_INFO")
    def _on_smart_battery(self, msg):
        self._app_state.set("drone.battery_capacity", msg.capacity_remaining)
        self._app_state.set("drone.battery_cycles", msg.cycle_count)

    @handler("PARAM_VALUE")
    def _on_param_value(self, msg):
        key = msg.param_id.strip('\x00')
        self._app_state.set("drone.param_" + key, msg.param_value)

    # ── 断联 ──

    def _on_lost(self):
        now = time.time()
        self._app_state.set("drone.connected", False)
        if self._lost_since == 0.0:
            self._lost_since = now
        elapsed = now - self._last_hb
        if elapsed < self._hb_timeout + 3:
            return
        if not self._lost_reported:
            self._lost_reported = True
            self._app_state.set("drone.data_fresh", False)
            frozen = {}
            for key in ["lat","lon","alt","heading","groundspeed","climb_rate",
                         "flight_mode","battery_remaining"]:
                val = self._app_state.get("drone." + key)
                frozen[key] = val
                self._app_state.set("drone.frozen_" + key, val if val else 0)
            logger.warning("MAVLink LOST (%.1fs)", elapsed)
            self._event_bus.publish("DRONE_LOST", {
                "reason": "heartbeat_timeout", "elapsed": round(elapsed,1), "frozen": frozen})