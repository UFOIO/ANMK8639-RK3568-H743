"""
MQTT 消息格式定义。

消息信封（统一）:
  {"msg_id": "uuid", "ts": 1234567890.123, "type": "status|alarm|event|command|ack", "payload": {...}}

Topic 定义:
  上行: hangar/status | hangar/drone/telemetry | hangar/alarm | hangar/event
  下行: hangar/command | hangar/config/set
"""
import json
import uuid
import time


def build_message(msg_type: str, payload: dict) -> str:
    """构建统一消息信封，返回 JSON 字符串。"""
    envelope = {
        "msg_id": uuid.uuid4().hex[:12],
        "ts": time.time(),
        "type": msg_type,
        "payload": payload,
    }
    return json.dumps(envelope, ensure_ascii=False)


def parse_message(raw: str) -> dict | None:
    """解析 MQTT 消息，返回信封字典或 None。"""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
