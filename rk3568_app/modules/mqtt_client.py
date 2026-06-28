"""
MQTT 通信模块：连接地面站，上报状态，接收指令。
"""
import logging
import threading
import time
import paho.mqtt.client as mqtt

from protocol.mqtt_proto import build_message, parse_message

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT 客户端，负责与地面站双向通信。"""

    def __init__(self, config: dict, event_bus, app_state):
        self._broker = config.get("broker", "localhost")
        self._port = config.get("port", 1883)
        self._client_id = config.get("client_id", "hangar_001")
        self._username = config.get("username", "")
        self._password = config.get("password", "")
        self._keepalive = config.get("keepalive", 30)
        self._status_interval = config.get("status_interval", 5)

        self._event_bus = event_bus
        self._app_state = app_state
        self._running = False
        self._reconnect_delay = 1
        self._reconnect_max = 60

        self._client = mqtt.Client(
            client_id=self._client_id,
            protocol=mqtt.MQTTv311)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def start(self):
        # 跳过占位符配置
        if "请填写" in self._broker or not self._broker:
            logger.info("MQTT disabled: broker not configured")
            return
        self._running = True
        if self._username:
            self._client.username_pw_set(self._username, self._password)

        # 设置遗嘱消息：异常断线时 Broker 自动发布
        will_msg = build_message("alarm", {
            "level": "ERROR", "code": "DEVICE_OFFLINE", "msg": "RK3568 disconnected"
        })
        self._client.will_set("hangar/alarm", will_msg, qos=1, retain=False)

        self._client.connect_async(self._broker, self._port, self._keepalive)
        self._client.loop_start()

        # 状态上报线程
        threading.Thread(target=self._status_loop, daemon=True).start()
        logger.info("MQTT started: %s:%d", self._broker, self._port)

    def stop(self):
        self._running = False
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT stopped")

    def publish_status(self):
        """上报全量状态。"""
        state = self._app_state.to_dict()
        msg = build_message("status", state)
        self._client.publish("hangar/status", msg, qos=1)

    def publish_telemetry(self):
        """上报无人机遥测摘要（高频）。"""
        drone = self._app_state.to_dict().get("drone", {})
        msg = build_message("telemetry", {
            "lat": drone.get("lat", 0),
            "lon": drone.get("lon", 0),
            "alt": drone.get("alt", 0),
            "heading": drone.get("heading", 0),
            "mode": drone.get("flight_mode", "UNKNOWN"),
            "armed": drone.get("armed", False),
            "battery": drone.get("battery_remaining", 0),
            "speed": drone.get("groundspeed", 0),
        })
        self._client.publish("hangar/drone/telemetry", msg, qos=0)

    def publish_alarm(self, level: str, code: str, msg_text: str, data=None):
        msg = build_message("alarm", {
            "level": level, "code": code, "msg": msg_text, "data": data or {}
        })
        self._client.publish("hangar/alarm", msg, qos=1)

    def publish_event(self, event_type: str, data=None):
        msg = build_message("event", {"event": event_type, "data": data or {}})
        self._client.publish("hangar/event", msg, qos=1)

    # ===== 回调 =====

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._app_state.set("system.mqtt_connected", True)
            self._reconnect_delay = 1  # 重置退避
            logger.info("MQTT connected")
            print("MQTT CONNECTED: " + self._broker + ":" + str(self._port, flush=True))
            # 订阅下行topic
            client.subscribe("hangar/command", qos=1)
            client.subscribe("hangar/config/set", qos=1)
            client.subscribe("hangar/upgrade/start", qos=1)
        else:
            logger.warning("MQTT connect failed: rc=%d", rc)

    def _on_disconnect(self, client, userdata, rc):
        self._app_state.set("system.mqtt_connected", False)
        if rc != 0:
            logger.warning("MQTT unexpected disconnect (rc=%d), will retry...", rc)
            print("MQTT DISCONNECTED (retrying, flush=True)", flush=True)
        else:
            logger.info("MQTT disconnected cleanly")
            print("MQTT DISCONNECTED", flush=True)

    def _on_message(self, client, userdata, msg):
        try:
            text = msg.payload.decode("utf-8", errors="replace")
        except Exception:
            return
        parsed = parse_message(text)
        if parsed:
            logger.info("MQTT RX: %s -> %s", msg.topic, parsed.get("type"))
            print("MQTT CMD: " + str(msg.topic, flush=True) + " -> " + str(msg.payload)[:80])
            self._event_bus.publish("MQTT_COMMAND", {
                "topic": msg.topic,
                "data": parsed,
            })

    def _status_loop(self):
        """周期上报：全量状态 + 无人机遥测。"""
        last_status = 0.0
        last_telemetry = 0.0
        while self._running:
            time.sleep(1)
            try:
                now = time.time()
                if now - last_status >= self._status_interval:
                    self.publish_status()
                    last_status = now
                if now - last_telemetry >= 1.0:
                    self.publish_telemetry()
                    last_telemetry = now
            except Exception:
                logger.exception("Status publish error")
