"""
ANMK8639 机库智能控制系统 — 主入口 (Linux Daemon 标准)。
支持: SIGHUP热重载 / SIGTERM优雅退出 / PID文件 / 命令行参数
"""
import argparse
import logging
import os
import signal
import sys
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

    for mod in _modules:
        try:
            mod.start()
        except Exception:
            logger.exception("Failed to start %s", mod.__class__.__name__)

    watchdog.start()
    logger.info("All modules started. Entering main loop.")
    _app_state.log_event("system", "info", "所有模块就绪，进入主循环")

    # ===== 信号处理 =====
    _running = True

    def on_terminate(sig, frame):
        global _running
        logger.info("收到信号 %s, 正在优雅退出...", sig.name if hasattr(sig, 'name') else sig)
        _app_state.log_event("system", "info", "收到退出信号")
        _running = False

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
        while _running:
            event_bus.poll(timeout=0.1)
            tick += 1

            # 每 5 秒打印状态快照
            now = time.time()
            if now - last_status >= 5.0:
                last_status = now
                _print_status(_app_state, config)
    except KeyboardInterrupt:
        pass

    # ===== 清理 =====
    logger.info("Shutting down...")
    _app_state.log_event("system", "info", "机库控制系统关闭")
    for mod in reversed(_modules):
        try:
            mod.stop()
        except Exception:
            logger.exception("Stop error")
    watchdog.stop()

    # 删除 PID 文件
    if not args.nodaemon:
        try:
            os.unlink(args.pidfile)
        except Exception:
            pass

    logger.info("System stopped. Goodbye.")


def _print_status(app_state, config):
    """打印简洁原始状态数据到终端 — 每个模块一行。"""
    health = app_state.health()
    status = app_state.to_dict()
    uptime = _fmt_uptime(app_state.uptime)

    mav = health["mavlink"]
    mqtt = health["mqtt"]
    stm = health["stm32"]
    cam = health["camera"]

    mav_ago = str(int(time.time()-mav["last_hb_sec"]))+"s" if mav["last_hb_sec"] else "--"
    mqtt_ago = str(int(time.time()-mqtt["last_msg_sec"]))+"s" if mqtt["last_msg_sec"] else "--"
    stm_ago = str(int(time.time()-stm["last_status_sec"]))+"s" if stm["last_status_sec"] else "--"
    cam_ago = str(int(time.time()-cam.get("last_snapshot_sec",0)))+"s" if cam.get("last_snapshot_sec") else "--"

    mav_ok = "OK" if mav["connected"] else "DOWN"
    mqtt_ok = "OK" if mqtt["connected"] else "DOWN"
    stm_ok = "OK" if stm["connected"] else "DOWN"
    cam_ok = "OK" if cam.get("last_snapshot_sec") else "DOWN"

    print("")
    print("=== STATUS " + time.strftime("%H:%M:%S") + " | UPTIME " + uptime + " | Web :" + str(config.get("web_ui",{}).get("port",8080)) + " ===")
    print("  MAVLink [" + mav_ok + "]  HB:" + mav_ago + "  |  MQTT [" + mqtt_ok + "]  MSG:" + mqtt_ago)
    print("  STM32  [" + stm_ok + "]  RPT:" + stm_ago + "  |  Camera [" + cam_ok + "]  SNAP:" + cam_ago)

    drone = status.get("drone", {})
    if drone.get("mode"):
        print("  DRONE  mode=" + str(drone.get("mode","?")) + "  batt=" + str(drone.get("battery","?")) + "%  alt=" + str(drone.get("alt","?")) + "m  spd=" + str(drone.get("groundspeed","?")) + "m/s  sat=" + str(drone.get("satellites","?")) + "  lat=" + str(drone.get("lat","?")) + "  lon=" + str(drone.get("lon","?")) + "  armed=" + ("YES" if drone.get("armed") else "NO"))

    hangar = status.get("hangar", {})
    if hangar.get("door"):
        alarms = hangar.get("alarms", [])
        alm_str = " ALARMS:" + ",".join(alarms) if alarms else ""
        print("  HANGAR door=" + str(hangar.get("door","?")) + "  lock=" + str(hangar.get("lock","?")) + "  temp=" + str(hangar.get("temperature","?")) + "C  hum=" + str(hangar.get("humidity","?")) + "%" + alm_str)

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

    print("=" * 60)
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
