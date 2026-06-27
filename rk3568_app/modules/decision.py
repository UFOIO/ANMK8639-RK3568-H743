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

        self._event_bus = event_bus
        self._app_state = app_state

    def start(self):
        self._event_bus.subscribe("DRONE_RTL", self._on_drone_rtl)
        self._event_bus.subscribe("DRONE_BATTERY_LOW", self._on_battery_low)
        self._event_bus.subscribe("DRONE_DISCONNECTED", self._on_drone_lost)
        self._event_bus.subscribe("HANGAR_ALARM", self._on_hangar_alarm)
        self._event_bus.subscribe("MQTT_COMMAND", self._on_mqtt_command)
        logger.info("Decision engine started (%d rules)", 5)

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
        """失联 -> 告警。"""
        reason = data.get("reason", "unknown")
        logger.warning("RULE: Drone lost (%s) -> alarm", reason)
        self._event_bus.publish("DECISION_ACTION", {
            "target": "mqtt",
            "type": "alarm",
            "level": "ERROR",
            "code": "DRONE_LOST",
            "msg": f"Drone disconnected: {reason}",
        })

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
