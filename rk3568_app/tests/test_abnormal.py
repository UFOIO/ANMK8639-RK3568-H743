"""
异常场景测试：模块断开、超时、边界条件。
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus
from core.app_state import AppState
from modules.decision import DecisionEngine


def _poll_all(bus, times=5, timeout=0.1):
    for _ in range(times):
        bus.poll(timeout=timeout)


class TestAbnormal:
    """异常场景集合。"""

    def test_event_flood(self):
        """事件洪泛：短时间内大量事件不崩溃。"""
        bus = EventBus()
        state = AppState()
        engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, state)
        engine.start()
        actions = []
        bus.subscribe("DECISION_ACTION", actions.append)

        # 快速连续发布 100 个事件
        for i in range(100):
            bus.publish("DRONE_RTL", {"mode": "RTL", "seq": i})
        _poll_all(bus, times=250, timeout=0.01)

        # 不应崩溃，且至少处理了事件
        assert len(actions) > 0
        assert all(a["cmd"] == "OPEN_DOOR" for a in actions)

    def test_no_subscriber_no_crash(self):
        """无人订阅的事件不崩溃。"""
        bus = EventBus()
        state = AppState()
        engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, state)
        engine.start()

        # 发布无人订阅的事件
        for _ in range(50):
            bus.publish("NONEXISTENT_EVENT", {"data": "x" * 1000})
        _poll_all(bus, times=20, timeout=0.05)
        # 不崩溃即通过

    def test_rapid_state_transition(self):
        """状态快速切换：RTL -> DISCONNECTED -> RTL -> DISCONNECTED"""
        bus = EventBus()
        state = AppState()
        engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, state)
        engine.start()
        actions = []
        bus.subscribe("DECISION_ACTION", actions.append)

        for _ in range(10):
            bus.publish("DRONE_RTL", {"mode": "RTL"})
            bus.publish("DRONE_DISCONNECTED", {"reason": "test"})
        _poll_all(bus, times=50, timeout=0.05)

        # RTL 触发 OPEN_DOOR，DISCONNECTED 触发 alarm
        stm32_cmds = [a for a in actions if a["target"] == "stm32"]
        mqtt_cmds = [a for a in actions if a["target"] == "mqtt"]
        assert len(stm32_cmds) == 10  # 每次 RTL 一次
        assert len(mqtt_cmds) == 10   # 每次 DISCONNECTED 一次

    def test_empty_event_data(self):
        """空数据事件不应崩溃。"""
        bus = EventBus()
        state = AppState()
        engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, state)
        engine.start()

        bus.publish("DRONE_RTL", None)
        bus.publish("DRONE_BATTERY_LOW", None)
        bus.publish("DRONE_DISCONNECTED", None)
        bus.publish("HANGAR_ALARM", None)
        _poll_all(bus)
        # 不崩溃即通过

    def test_large_event_data(self):
        """大数据事件不崩溃。"""
        bus = EventBus()
        engine = DecisionEngine({"auto_open_on_rtl": True, "low_battery_threshold": 20, "lost_timeout": 30}, bus, AppState())
        engine.start()

        bus.publish("DRONE_RTL", {"data": "x" * 100000})
        _poll_all(bus, times=10, timeout=0.1)
        # 不崩溃即通过


if __name__ == "__main__":
    t = TestAbnormal()
    tests = [
        t.test_event_flood, t.test_no_subscriber_no_crash,
        t.test_rapid_state_transition, t.test_empty_event_data, t.test_large_event_data,
    ]
    for fn in tests:
        fn()
        print(f"  PASS: {fn.__name__}")
    print("\nAll abnormal tests passed!")
