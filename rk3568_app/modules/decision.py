"""
决策引擎：订阅事件 -> 规则匹配 -> 产出动作。
"""
import logging

logger = logging.getLogger(__name__)


class DecisionEngine:
    """事件驱动的规则引擎。"""

    def __init__(self, config: dict, event_bus, app_state):
        self._auto_open_on_rtl = config.get("auto_open_on_rtl", True)
        self._low_battery_threshold = config.get("low_battery_threshold", 20)
        self._lost_timeout = config.get("lost_timeout", 30)

        # Dead-reckoning safety params
        self._hangar_lat = config.get("hangar_lat", 0.0)
        self._hangar_lon = config.get("hangar_lon", 0.0)
        self._lost_grace = config.get("lost_grace_period", 8)
        self._default_rtl_speed = config.get("default_rtl_speed", 8.0)
        self._door_margin = config.get("door_eta_margin", 15)
        self._door_open_timeout = config.get("door_open_timeout", 300)
        self._min_alt_for_protection = config.get("min_alt_for_protection", 5.0)
        self._min_battery_for_auto_open = config.get("min_battery_for_auto_open", 5)

        self._event_bus = event_bus
        self._app_state = app_state
        self._dead_reckon_timer = None  # ETA countdown timer

    def start(self):
        self._event_bus.subscribe("DRONE_RTL", self._on_drone_rtl)
        self._event_bus.subscribe("DRONE_BATTERY_LOW", self._on_battery_low)
        self._event_bus.subscribe("DRONE_DISCONNECTED", self._on_drone_lost)
        self._event_bus.subscribe("DRONE_LOST", self._on_drone_lost_protection)
        self._event_bus.subscribe("HANGAR_ALARM", self._on_hangar_alarm)
        self._event_bus.subscribe("MQTT_COMMAND", self._on_mqtt_command)
        logger.info("Decision engine started (%d rules)", 6)

    def stop(self):
        logger.info("Decision engine stopped")

    # ===== 规则 =====

    def _on_drone_rtl(self, data):
        if data is None: data = {}
        """无人机返航 -> 自动开舱门。"""
        if self._auto_open_on_rtl:
            logger.info("RULE: RTL detected -> open door")
            self._event_bus.publish("DECISION_ACTION", {
                "target": "stm32",
                "cmd": "OPEN_DOOR",
            })

    def _on_battery_low(self, data):
        if data is None: data = {}
        """低电量 -> 告警。"""
        remaining = data.get("remaining", 0)
        logger.warning("RULE: Battery low (%d%%) -> alarm", remaining)
        self._event_bus.publish("DECISION_ACTION", {
            "target": "mqtt",
            "type": "alarm",
            "level": "WARNING",
            "code": "DRONE_BATTERY_LOW",
            "msg": f"Drone battery low: {remaining}%",
        })

    def _on_drone_lost(self, data):
        if data is None: data = {}
        """失联 -> 告警 + 启动断联保护计时。"""
        reason = data.get("reason", "unknown")
        logger.warning("RULE: Drone lost (%s) -> alarm + dead-reckoning", reason)
        self._event_bus.publish("DECISION_ACTION", {
            "target": "mqtt",
            "type": "alarm",
            "level": "ERROR",
            "code": "DRONE_LOST",
            "msg": f"Drone disconnected: {reason}",
        })

    def _on_drone_lost_protection(self, data):
        """断联保护 - 4阶段闭环:
        P1: 校验(高度/电量/坐标) -> P2: 倒计时开舱 -> P3: 等待到达 -> P4: 超时关舱
        """
        if data is None: data = {}
        frozen = data.get("frozen", {})

        if self._hangar_lat == 0.0 and self._hangar_lon == 0.0:
            logger.warning("PROTECT: hangar position not configured, skip")
            return

        mode = frozen.get("flight_mode", "UNKNOWN")
        lat = frozen.get("lat", 0)
        lon = frozen.get("lon", 0)
        gs = frozen.get("groundspeed", 0) or self._default_rtl_speed
        alt = frozen.get("alt", 0)
        batt = frozen.get("battery_remaining", 0)

        if lat == 0 and lon == 0:
            logger.warning("PROTECT: no frozen position, skip")
            return

        # === Phase 1: Validate ===
        reject_reason = None
        min_alt = self._app_state._data.get("hangar", {}).get("_min_alt", 5.0) if hasattr(self._app_state, "_data") else 5.0
        # Use config values (read at init)
        min_alt_cfg = getattr(self, "_min_alt_for_protection", 5.0)
        min_batt = getattr(self, "_min_battery_for_auto_open", 5)
        door_timeout = getattr(self, "_door_open_timeout", 300)

        if alt < min_alt_cfg:
            reject_reason = "高度为0/负，可能在地面"
        elif batt > 0 and batt < min_batt:
            reject_reason = "电量仅%d%%，大概率无法返航" % batt

        if reject_reason:
            logger.warning("PROTECT ABORT: %s (alt=%.1f batt=%d%% mode=%s)", reject_reason, alt, batt, mode)
            self._app_state.log_event("decision", "warn",
                "断联保护取消: %s" % reject_reason)
            self._event_bus.publish("DEAD_RECKON_STATUS", {
                "active": False, "aborted": True,
                "reason": reject_reason, "mode": mode, "batt": batt, "alt": round(alt, 1),
            })
            # Still alarm but don't open door
            self._event_bus.publish("DECISION_ACTION", {
                "target": "mqtt", "type": "alarm", "level": "WARNING",
                "code": "PROTECTION_ABORTED",
                "msg": "断联保护未执行: %s (模式=%s 电池=%d%% 高度=%.1fm)" % (
                    reject_reason, mode, batt, alt),
            })
            return

        # === Phase 2: ETA countdown ===
        dist = self._haversine(self._hangar_lat, self._hangar_lon, lat, lon)
        eta = dist / gs if gs > 0 else 9999
        open_at = max(0, eta - self._door_margin)

        logger.warning(
            "PROTECT START: mode=%s dist=%.0fm gs=%.1fm/s eta=%.0fs open_in=%.0fs batt=%d%% alt=%.1fm",
            mode, dist, gs, eta, open_at, batt, alt
        )
        self._app_state.log_event("decision", "warn",
            "断联保护启动: 距离%.0fm ETA=%.0fs 提前%.0fs开舱" % (dist, eta, open_at))
        ps = {
            "active": True, "phase": "countdown",
            "dist": round(dist, 1), "gs": round(gs, 1),
            "eta": round(eta, 1), "open_at": round(open_at, 1),
            "mode": mode, "batt": batt, "alt": round(alt, 1),
        }
        self._event_bus.publish("DEAD_RECKON_STATUS", ps)
        self._app_state.set("drone.protection_status", ps)
        self._event_bus.publish("DECISION_ACTION", {
            "target": "mqtt", "type": "alarm", "level": "WARNING",
            "code": "PROTECTION_STARTED",
            "msg": "断联保护启动: 距离%.0fm ETA=%.0fs 模式=%s 电池=%d%%" % (dist, eta, mode, batt),
        })

        if self._dead_reckon_timer:
            self._dead_reckon_timer.cancel()

        def _protection_worker(wait_open, frozen_info, dt):
            # --- Phase 2: Wait then open ---
            if wait_open > 0:
                logger.info("PROTECT: waiting %.0fs to open door...", wait_open)
                # Sleep in chunks so we can check for reconnect
                slept = 0
                while slept < wait_open:
                    chunk = min(5, wait_open - slept)
                    time.sleep(chunk)
                    slept += chunk
                    if self._app_state.get("drone.connected"):
                        logger.info("PROTECT CANCEL: drone reconnected during countdown")
                        self._event_bus.publish("DEAD_RECKON_STATUS", {"active": False, "cancelled": True})
                        self._app_state.log_event("decision", "info",
                            "断联保护取消: 无人机已重连")
                        return

            if self._app_state.get("drone.connected"):
                logger.info("PROTECT CANCEL: drone reconnected before door open")
                ps_data = {"active": False, "cancelled": True}
            self._event_bus.publish("DEAD_RECKON_STATUS", ps_data)
            self._app_state.set("drone.protection_status", ps_data)
            return

            # --- Phase 3: Open door ---
            logger.warning("PROTECT: opening door (ETA expired)")
            self._event_bus.publish("DECISION_ACTION", {"target": "stm32", "cmd": "OPEN_DOOR"})
            ps_data = {
                "active": True, "phase": "door_open",
                "door_open_time": time.time(),
                "timeout_at": time.time() + dt,
                "mode": frozen_info.get("flight_mode", "?"),
            }
            self._event_bus.publish("DEAD_RECKON_STATUS", ps_data)
            self._app_state.set("drone.protection_status", ps_data)
            self._app_state.log_event("decision", "error",
                "断联保护: 舱门已自动打开，等待无人机到达(%d分钟超时)" % (dt // 60))
            self._event_bus.publish("DECISION_ACTION", {
                "target": "mqtt", "type": "alarm", "level": "ERROR",
                "code": "DOOR_AUTO_OPENED",
                "msg": "断联保护: 舱门已自动打开。无人机断联位置: %.6f,%.6f 电池=%d%%" % (
                    frozen_info.get("lat", 0), frozen_info.get("lon", 0),
                    frozen_info.get("battery_remaining", 0)),
            })

            # --- Phase 4: Door open timeout ---
            logger.info("PROTECT: door open timeout %ds started", dt)
            slept = 0
            while slept < dt:
                chunk = min(10, dt - slept)
                time.sleep(chunk)
                slept += chunk
                # Check reconnect periodically
                if self._app_state.get("drone.connected"):
                    logger.info("PROTECT RESOLVED: drone reconnected after door opened")
                    self._event_bus.publish("DEAD_RECKON_STATUS", {
                        "active": False, "phase": "resolved",
                        "msg": "无人机已重连，保护流程结束",
                    })
                    self._app_state.log_event("decision", "info",
                        "断联保护完成: 无人机已重连，舱门保持打开")
                    return
                # Update remaining time in status
                remaining = dt - slept
                if remaining % 60 < 10:  # update roughly every minute
                    self._event_bus.publish("DEAD_RECKON_STATUS", {
                        "active": True, "phase": "door_open",
                        "timeout_remaining": round(remaining, 1),
                    })

            # --- Phase 4b: Timeout - close door ---
            logger.warning("PROTECT TIMEOUT: %ds elapsed, drone did not arrive. Closing door.", dt)
            self._event_bus.publish("DECISION_ACTION", {"target": "stm32", "cmd": "CLOSE_DOOR"})
            time.sleep(1)
            self._event_bus.publish("DECISION_ACTION", {"target": "stm32", "cmd": "LOCK"})
            ps_data = {
                "active": False, "phase": "timeout_closed",
                "msg": "超时未到达，舱门已自动关闭+锁止。请人工检查无人机状态",
            }
            self._event_bus.publish("DEAD_RECKON_STATUS", ps_data)
            self._app_state.set("drone.protection_status", ps_data)
            self._app_state.log_event("decision", "error",
                "断联保护超时: 舱门已关闭+锁止。无人机可能失事，请人工检查")
            self._event_bus.publish("DECISION_ACTION", {
                "target": "mqtt", "type": "alarm", "level": "CRITICAL",
                "code": "PROTECTION_TIMEOUT_CLOSED",
                "msg": "断联保护超时: 舱门已关闭。无人机可能失事。断联位置: %.6f,%.6f 电池=%d%% 请人工检查" % (
                    frozen_info.get("lat", 0), frozen_info.get("lon", 0),
                    frozen_info.get("battery_remaining", 0)),
            })

        self._dead_reckon_timer = threading.Thread(
            target=_protection_worker,
            args=(open_at, frozen, door_timeout),
            daemon=True
        )
        self._dead_reckon_timer.start()

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2):
        """计算两点间距离(米)。"""
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _on_hangar_alarm(self, data):
        if data is None: data = {}
        """机库告警 -> 关舱+上锁+上报。"""
        flags = data.get("flags", 0)
        logger.warning("RULE: Hangar alarm (flags=0x%04X) -> lock+report", flags)
        self._event_bus.publish("DECISION_ACTION", {
            "target": "stm32",
            "cmd": "CLOSE_DOOR",
        })
        self._event_bus.publish("DECISION_ACTION", {
            "target": "stm32",
            "cmd": "LOCK",
        })
        self._event_bus.publish("DECISION_ACTION", {
            "target": "mqtt",
            "type": "alarm",
            "level": "ERROR",
            "code": "HANGAR_ALARM",
            "msg": f"Hangar alarm flags=0x{flags:04X}",
        })

    def _on_mqtt_command(self, data):
        if data is None: return
        """地面站 MQTT 指令 -> 转发到对应模块。"""
        payload = data.get("data", {}).get("payload", {})
        target = payload.get("target", "")
        action = payload.get("action", "")
        params = payload.get("params", {})

        logger.info("RULE: MQTT command: target=%s action=%s", target, action)

        if target == "hangar":
            cmd_map = {
                "OPEN_DOOR": "OPEN_DOOR",
                "CLOSE_DOOR": "CLOSE_DOOR",
                "LOCK": "LOCK",
                "UNLOCK": "UNLOCK",
            }
            stm32_cmd = cmd_map.get(action)
            if stm32_cmd:
                self._event_bus.publish("DECISION_ACTION", {
                    "target": "stm32",
                    "cmd": stm32_cmd,
                })
