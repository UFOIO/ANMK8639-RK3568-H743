"""事件总线单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus


def test_subscribe_and_publish():
    bus = EventBus()
    received = []

    def callback(data):
        received.append(data)

    bus.subscribe("TEST_EVENT", callback)
    bus.publish("TEST_EVENT", {"msg": "hello"})
    bus.poll(timeout=0.5)
    assert len(received) == 1
    assert received[0]["msg"] == "hello"

def test_multiple_subscribers():
    bus = EventBus()
    results = []

    bus.subscribe("E", lambda d: results.append("A"))
    bus.subscribe("E", lambda d: results.append("B"))
    bus.publish("E", None)
    bus.poll(timeout=0.5)
    assert results == ["A", "B"]

def test_no_subscriber():
    """没有订阅者不应崩溃。"""
    bus = EventBus()
    bus.publish("NO_ONE_LISTENS", None)
    bus.poll(timeout=0.5)  # 不应抛异常

def test_callback_exception():
    """回调异常不应影响其他回调。"""
    bus = EventBus()
    ok = []

    def bad_cb(data):
        raise RuntimeError("intentional")

    bus.subscribe("E", bad_cb)
    bus.subscribe("E", lambda d: ok.append("ok"))
    bus.publish("E", None)
    bus.poll(timeout=0.5)
    assert ok == ["ok"]

def test_poll_empty():
    """空队列poll返回False。"""
    bus = EventBus()
    assert bus.poll(timeout=0.01) is False



if __name__ == "__main__":
    tests = [test_subscribe_and_publish, test_multiple_subscribers,
             test_no_subscriber, test_callback_exception, test_poll_empty]
    for t in tests:
        t()
        print(f"  PASS: {t.__name__}")
    print("\nAll EventBus tests passed!")
