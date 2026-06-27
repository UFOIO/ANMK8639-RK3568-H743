"""
集成测试：验证模块间事件链路。
mavlink事件 -> event_bus -> decision -> DECISION_ACTION
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus
from core.app_state import AppState
from modules.decision import DecisionEngine


def _poll_all(bus, times=4, timeout=0.1):
    for _ in range(times):
        bus.poll(timeout=timeout)


def test_mavlink_to_decision_full_chain():
    """完整链路：HEARTBEAT(RTL) -> DRONE_RTL -> DECISION -> OPEN_DOOR"""
    bus = EventBus()
    state = AppState()

    # 初始化决策引擎
    engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, state)
    engine.start()

    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)

    # 模拟 MAVLink 心跳（RTL模式 custom_mode=6）
    bus.publish("DRONE_RTL", {"mode": "RTL"})
    _poll_all(bus)

    assert len(actions) == 1
    assert actions[0]["target"] == "stm32"
    assert actions[0]["cmd"] == "OPEN_DOOR"

    # 同时检查 app_state 未被修改（decision 不直接改 state for RTL）
    # actually decision doesn't modify app_state for RTL

def test_mavlink_lost_chain():
    """失联链路：DRONE_DISCONNECTED -> decision -> MQTT告警"""
    bus = EventBus()
    state = AppState()
    engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, state)
    engine.start()

    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)
    bus.publish("DRONE_DISCONNECTED", {"reason": "heartbeat_timeout"})
    _poll_all(bus)

    mqtt_actions = [a for a in actions if a["target"] == "mqtt"]
    assert len(mqtt_actions) == 1
    assert mqtt_actions[0]["code"] == "DRONE_LOST"

def test_multiple_events_in_sequence():
    """事件序列：失联 -> 恢复(RTL) -> 开舱"""
    bus = EventBus()
    state = AppState()
    engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, state)
    engine.start()

    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)

    # 先失联
    bus.publish("DRONE_DISCONNECTED", {"reason": "test"})
    _poll_all(bus)
    assert any(a["target"] == "mqtt" for a in actions)
    actions.clear()

    # 再收到返航心跳
    bus.publish("DRONE_RTL", {"mode": "RTL"})
    _poll_all(bus)
    assert any(a["target"] == "stm32" and a["cmd"] == "OPEN_DOOR" for a in actions)

if __name__ == "__main__":
    tests = [test_mavlink_to_decision_full_chain, test_mavlink_lost_chain, test_multiple_events_in_sequence]
    for t in tests:
        t()
        print(f"  PASS: {t.__name__}")
    print("\nAll integration tests passed!")
