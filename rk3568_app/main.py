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

            # 每 5 秒打印状态快照
            now = time.time()
            if now - last_status >= 5.0:
                last_status = now
                _print_status(_app_state, config, _module_threads)
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


def _print_status(app_state, config, modules_dict=None):
    """打印每个模块的独立存活状态 — 多行原始数据。
    modules_dict: {name: thread_object} 用于检测线程存活
    """
    health = app_state.health()
    status = app_state.to_dict()
    uptime = _fmt_uptime(app_state.uptime)

    # 每个模块独立一行，带存活标识
    now = time.time()
    
    def _alive(mod_name, thread_obj):
        """检查模块线程是否存活。返回 alive 标识符。"""
        if thread_obj is None:
            return "  "  # 未启动
        if thread_obj.is_alive():
            return "OK"
        return "XX"  # 线程已死!

    # 取各模块线程
    threads = modules_dict or {}
    
    mav = health["mavlink"]
    mqtt = health["mqtt"]
    stm = health["stm32"]
    cam = health["camera"]

    mav_ago = str(int(now-mav["last_hb_sec"]))+"s" if mav["last_hb_sec"] else "--"
    mqtt_ago = str(int(now-mqtt["last_msg_sec"]))+"s" if mqtt["last_msg_sec"] else "--"
    stm_ago = str(int(now-stm["last_status_sec"]))+"s" if stm["last_status_sec"] else "--"
    cam_ago = str(int(now-cam.get("last_snapshot_sec",0)))+"s" if cam.get("last_snapshot_sec") else "--"

    def _s(mod, key="status"):
        s = mod.get(key, "dead")
        return {"healthy":"OK","stale":"OLD","degraded":"DEG","dead":"DOWN"}.get(s, "??")

    mav_alive = _alive("mavlink", threads.get("mavlink"))
    mqtt_alive = _alive("mqtt", threads.get("mqtt"))
    stm_alive = _alive("stm32", threads.get("stm32"))
    cam_alive = _alive("camera", threads.get("camera"))
    web_alive = _alive("web_ui", threads.get("web_ui"))
    dec_alive = _alive("decision", threads.get("decision"))

    print("")
    print("=" * 70)
    print("  ANMK8639  |  " + time.strftime("%Y-%m-%d %H:%M:%S") + "  |  UPTIME " + uptime + "  |  Web :" + str(config.get("web_ui",{}).get("port",8080)))
    print("-" * 70)
    print("  MODULE     THREAD   CONN    DATA AGE     DETAIL")
    print("-" * 70)
    print("  mavlink    [" + mav_alive + "]     [" + _s(mav) + "]    HB:" + mav_ago.ljust(8) + "  " + str(status.get("drone",{}).get("mode","--")))
    print("  mqtt       [" + mqtt_alive + "]     [" + _s(mqtt) + "]    MSG:" + mqtt_ago.ljust(8) + "  " + ("enabled" if config.get("mqtt",{}).get("enabled") else "disabled"))
    print("  stm32      [" + stm_alive + "]     [" + _s(stm) + "]    RPT:" + stm_ago.ljust(8) + "  " + config.get("stm32",{}).get("port","/dev/ttyACM0"))
    print("  camera     [" + cam_alive + "]     [" + _s(cam) + "]    SNAP:" + cam_ago.ljust(8) + "  rtsp://" + config.get("camera",{}).get("ip","?") + ":" + str(config.get("camera",{}).get("port","?")))
    print("  web_ui     [" + web_alive + "]     --      --            http://0.0.0.0:" + str(config.get("web_ui",{}).get("port",8080)))
    print("  decision   [" + dec_alive + "]     --      --            5 rules")
    print("-" * 70)

    drone = status.get("drone", {})
    if drone.get("mode"):
        print("  DRONE  mode=" + str(drone.get("mode","?")) + "  batt=" + str(drone.get("battery","?")) + "%  alt=" + str(drone.get("alt","?")) + "m  spd=" + str(drone.get("groundspeed","?")) + "m/s  sat=" + str(drone.get("satellites","?")) + "  lat=" + str(drone.get("lat","?")) + "  lon=" + str(drone.get("lon","?")))

    hangar = status.get("hangar", {})
    if hangar.get("door"):
        alarms = hangar.get("alarms", [])
        alm = " ALARMS:" + ",".join(alarms) if alarms else ""
        print("  HANGAR door=" + str(hangar.get("door","?")) + "  lock=" + str(hangar.get("lock","?")) + "  temp=" + str(hangar.get("temperature","?")) + "C  hum=" + str(hangar.get("humidity","?")) + "%" + alm)

    try:
        with open("/proc/loadavg") as f:
            load = f.read().split()[0]
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                p = line.split(":")
                if len(p) == 2:
                    mem[p[0].strip()] = int(p[1].strip().split()[0])
        ram_used = (mem.get("MemTotal",1)-mem.get("MemAvailable",1))//1024
        ram_total = mem.get("MemTotal",1)//1024
        print("  SYSTEM load=" + load + "  ram=" + str(ram_used) + "M/" + str(ram_total) + "M")
    except:
        pass

    print("=" * 70)
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
