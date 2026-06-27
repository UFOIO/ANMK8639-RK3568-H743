"""决策引擎单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus
from core.app_state import AppState
from modules.decision import DecisionEngine


def _poll_all(bus, times=3, timeout=0.1):
    """多次 poll 处理级联事件。"""
    for _ in range(times):
        bus.poll(timeout=timeout)


def _make_config(**overrides):
    cfg = {"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}
    cfg.update(overrides)
    return cfg


def test_rtl_opens_door():
    bus = EventBus(); state = AppState()
    engine = DecisionEngine(_make_config(), bus, state); engine.start()
    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)
    bus.publish("DRONE_RTL", {"mode": "RTL"})
    _poll_all(bus)
    assert len(actions) == 1
    assert actions[0]["target"] == "stm32"
    assert actions[0]["cmd"] == "OPEN_DOOR"

def test_battery_low_alarm():
    bus = EventBus(); state = AppState()
    engine = DecisionEngine(_make_config(), bus, state); engine.start()
    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)
    bus.publish("DRONE_BATTERY_LOW", {"remaining": 15})
    _poll_all(bus)
    mqtt_actions = [a for a in actions if a["target"] == "mqtt"]
    assert len(mqtt_actions) == 1

def test_drone_lost_alarm():
    bus = EventBus(); state = AppState()
    engine = DecisionEngine(_make_config(), bus, state); engine.start()
    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)
    bus.publish("DRONE_DISCONNECTED", {"reason": "heartbeat_timeout"})
    _poll_all(bus)
    mqtt_actions = [a for a in actions if a["target"] == "mqtt"]
    assert len(mqtt_actions) == 1
    assert mqtt_actions[0]["code"] == "DRONE_LOST"

def test_hangar_alarm_locks():
    bus = EventBus(); state = AppState()
    engine = DecisionEngine(_make_config(), bus, state); engine.start()
    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)
    bus.publish("HANGAR_ALARM", {"flags": 0x01})
    _poll_all(bus)
    stm32_cmds = [a["cmd"] for a in actions if a["target"] == "stm32"]
    assert "CLOSE_DOOR" in stm32_cmds
    assert "LOCK" in stm32_cmds

def test_mqtt_command_forward():
    bus = EventBus(); state = AppState()
    engine = DecisionEngine(_make_config(), bus, state); engine.start()
    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)
    bus.publish("MQTT_COMMAND", {
        "topic": "hangar/command",
        "data": {"msg_id": "t","ts":0,"type":"command",
                 "payload": {"target":"hangar","action":"OPEN_DOOR","params":{}}}
    })
    _poll_all(bus)
    stm32_cmds = [a for a in actions if a["target"] == "stm32"]
    assert len(stm32_cmds) == 1

def test_rtl_disabled():
    bus = EventBus(); state = AppState()
    engine = DecisionEngine(_make_config(auto_open_on_rtl=False), bus, state)
    engine.start()
    actions = []
    bus.subscribe("DECISION_ACTION", actions.append)
    bus.publish("DRONE_RTL", {"mode": "RTL"})
    _poll_all(bus)
    assert len(actions) == 0

if __name__ == "__main__":
    tests = [test_rtl_opens_door, test_battery_low_alarm, test_drone_lost_alarm,
             test_hangar_alarm_locks, test_mqtt_command_forward, test_rtl_disabled]
    for t in tests:
        t()
        print(f"  PASS: {t.__name__}")
    print("\nAll Decision engine tests passed!")
