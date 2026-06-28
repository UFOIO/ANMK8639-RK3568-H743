"""
ANMK8639 机库智能控制系统 — 主入口 (Linux Daemon 标准)。
支持: SIGHUP热重载 / SIGTERM优雅退出 / PID文件 / 命令行参数
"""
import argparse
import logging
import os
import signal
import sys
import threading
import time

from utils.config import ConfigLoader
from utils.logger import setup_logger
from core.event_bus import EventBus
from core.app_state import AppState
from core.watchdog import Watchdog
from modules.mqtt_client import MQTTClient
from modules.mavlink_client import MAVLinkClient
from modules.stm32_comm import STM32Comm
from modules.camera import CameraCapture
from modules.decision import DecisionEngine
from modules.upgrade_mgr import UpgradeManager
from modules.web_ui import WebUI

logger = logging.getLogger(__name__)


# 全局引用（信号处理器需要访问）
_modules = []
_app_state = None
_running = False


def main():
    global _modules, _app_state, _running

    parser = argparse.ArgumentParser(description="ANMK8639 Hangar Control System")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("-p", "--pidfile", default="/run/hangar.pid", help="PID 文件路径")
    parser.add_argument("--nodaemon", action="store_true", help="前台运行（不写PID，日志到stdout）")
    args = parser.parse_args()

    config = ConfigLoader(args.config)
    setup_logger(config.log)

    # PID 文件 (systemd 管理时不写)
    if not args.nodaemon:
        try:
            os.makedirs(os.path.dirname(args.pidfile), exist_ok=True)
            with open(args.pidfile, "w") as f:
                f.write(str(os.getpid()))
        except PermissionError:
            logger.warning("Cannot write PID file: %s", args.pidfile)

    logger.info("=" * 50)
    logger.info("ANMK8639 Hangar Control System v1.0")
    logger.info("PID: %d | Config: %s", os.getpid(), args.config)
    logger.info("=" * 50)

    event_bus = EventBus()
    _app_state = AppState()

    # 创建模块
    mqtt = MQTTClient(config.mqtt, event_bus, _app_state)
    mavlink = MAVLinkClient(config.mavlink, event_bus, _app_state)
    stm32 = STM32Comm(config.stm32, event_bus, _app_state)
    camera = CameraCapture(config.camera, app_state=_app_state)
    decision = DecisionEngine(config.decision, event_bus, _app_state)
    upgrade = UpgradeManager({}, stm32, event_bus)
    web_ui = WebUI(config.get("web_ui", {}), _app_state, event_bus, stm32, upgrade_mgr=upgrade)
    watchdog = Watchdog(config.watchdog, event_bus)

    event_bus.subscribe("DECISION_ACTION", lambda d: _execute_action(d, mqtt, stm32))

    _app_state.log_event("system", "info", "机库控制系统启动")
    _app_state.log_event("system", "info", "配置: " + args.config)

    # 保存方便热重载
    _modules = [mqtt, mavlink, stm32, camera, decision, web_ui]

    _module_threads = {}
    _name_map = {"mqttclient":"mqtt","mavlinkclient":"mavlink","stm32comm":"stm32","cameracapture":"camera","webui":"web_ui","decisionengine":"decision"}
    for mod in _modules:
        try:
            mod.start()
            # 尝试获取模块线程用于存活检测
            clsname = mod.__class__.__name__.lower()
            key = _name_map.get(clsname, clsname)
            for attr in ["_thread", "_recv_thread", "_server_thread", "thread"]:
                t = getattr(mod, attr, None)
                if t and isinstance(t, threading.Thread):
                    _module_threads[key] = t
                    break
        except Exception:
            logger.exception("Failed to start %s", mod.__class__.__name__)

    watchdog.start()
    logger.info("All modules started. Entering main loop.")
    print("\n=== ANMK8639 Hangar Control STARTED ===\n", flush=True)
    _app_state.log_event("system", "info", "所有模块就绪，进入主循环")

    # ===== 信号处理 =====
    _running = [True]

    def on_terminate(sig, frame):
        logger.info("收到信号 %s, 正在优雅退出...", sig.name if hasattr(sig, 'name') else sig)
        _app_state.log_event("system", "info", "收到退出信号")
        _running[0] = False

    def on_reload(sig, frame):
        """SIGHUP: 热重载配置"""
        logger.info("收到 SIGHUP, 热重载配置...")
        _app_state.log_event("system", "info", "热重载配置")
        try:
            new_cfg = ConfigLoader(args.config)
            # 重新设置日志级别
            logging.getLogger().setLevel(getattr(logging, new_cfg.log.get("level", "INFO").upper()))
            # 更新各模块配置（只更新可变参数）
            # MAVLink 心跳超时
            if hasattr(mavlink, '_hb_timeout'):
                mavlink._hb_timeout = new_cfg.mavlink.get("heartbeat_timeout", 5)
            logger.info("配置已热重载 (日志级别、心跳超时等)")
            _app_state.log_event("system", "info", "配置热重载完成")
        except Exception:
            logger.exception("热重载失败")

    signal.signal(signal.SIGTERM, on_terminate)
    signal.signal(signal.SIGINT, on_terminate)
    signal.signal(signal.SIGHUP, on_reload)

    # ===== 主循环 =====
    tick = 0
    last_status = 0.0
    try:
        while _running[0]:
            event_bus.poll(timeout=0.1)
            tick += 1

            # 每秒心跳 — 始终保持有输出
            now = time.time()
            if now - last_status >= 1.0:
                last_status = now
                _print_heartbeat(_app_state, config)
    except KeyboardInterrupt:
        _running[0] = False

    # ===== 清理 (最多等5秒) =====
    logger.info("Shutting down...")
    def _do_shutdown():
        try:
            _app_state.log_event("system", "info", "机库控制系统关闭")
            for mod in reversed(_modules):
                try:
                    mod.stop()
                except Exception:
                    logger.exception("Stop error")
            watchdog.stop()
        except Exception:
            pass
    _t = threading.Thread(target=_do_shutdown, daemon=True)
    _t.start()
    _t.join(timeout=5.0)
    if _t.is_alive():
        logger.warning("部分模块未能在5秒内停止，强制退出")

    # 删除 PID 文件
    if not args.nodaemon:
        try:
            os.unlink(args.pidfile)
        except Exception:
            pass

    logger.info("System stopped. Goodbye.")


def _print_heartbeat(app_state, config):
    """每30秒打印系统资源 + 各模块数据新鲜度摘要"""
    health = app_state.health()
    uptime = _fmt_uptime(app_state.uptime)
    
    # 系统资源
    try:
        with open("/proc/loadavg") as f: load = f.read().split()[0]
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                p = line.split(":")
                if len(p) == 2: mem[p[0].strip()] = int(p[1].strip().split()[0])
        ram_used = (mem.get("MemTotal",1)-mem.get("MemAvailable",1))//1024
        ram_total = mem.get("MemTotal",1)//1024
        print("SYS: load=" + load + " ram=" + str(ram_used, flush=True) + "M/" + str(ram_total) + "M uptime=" + uptime)
    except: pass
    
    # 各模块数据新鲜度
    def _age(k, key):
        d = health.get(k, {})
        sec = d.get(key)
        return str(int(time.time()-sec))+"s" if sec is not None else "--"
    
    print("DATA: MAVLink HB:" + _age("mavlink","last_hb_sec", flush=True) + 
          " | MQTT MSG:" + _age("mqtt","last_msg_sec") + 
          " | STM32 RPT:" + _age("stm32","last_status_sec") + 
          " | Camera SNAP:" + _age("camera","last_snapshot_sec"))
    sys.stdout.flush()
def _fmt_uptime(sec):
    d = int(sec // 86400)
    h = int((sec % 86400) // 3600)
    m = int((sec % 3600) // 60)
    if d > 0:
        return f"{d}d{h}h"
    if h > 0:
        return f"{h}h{m}m"
    return f"{m}m"


def _execute_action(data, mqtt, stm32):
    target = data.get("target", "")
    if target == "mqtt" and data.get("type") == "alarm":
        mqtt.publish_alarm(data.get("level", "INFO"), data.get("code", "UNKNOWN"), data.get("msg", ""))
    elif target == "stm32":
        from protocol.stm32_proto import CMD_OPEN_DOOR, CMD_CLOSE_DOOR, CMD_LOCK, CMD_UNLOCK
        cmd_map = {"OPEN_DOOR": CMD_OPEN_DOOR, "CLOSE_DOOR": CMD_CLOSE_DOOR, "LOCK": CMD_LOCK, "UNLOCK": CMD_UNLOCK}
        code = cmd_map.get(data.get("cmd", ""))
        if code is not None:
            stm32.send_command(code)


if __name__ == "__main__":
    main()
