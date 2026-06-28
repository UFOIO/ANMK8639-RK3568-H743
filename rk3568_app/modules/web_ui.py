"""
Web 管理仪表盘 — 专业级航空风格。
零外部依赖，基于 Python 标准库 http.server。
功能：心跳脉冲、告警弹窗、连接健康面板、事件日志、结构化配置管理、指令下发、
     系统资源监控、摄像头截图画廊、STM32固件升级管理、决策规则查看。
"""
import json
import logging
import os
import threading
import time
import yaml
import subprocess
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

_DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")

def _load_dashboard():
    try:
        with open(_DASHBOARD_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>Dashboard HTML not found at " + _DASHBOARD_PATH + "</h1>"


def _get_system_info():
    """Collect system resource info (cross-platform)."""
    info = {
        "cpu_percent": 0,
        "load_avg": [],
        "ram_percent": 0,
        "ram_used": "",
        "ram_total": "",
        "disk_percent": 0,
        "disk_used": "",
        "disk_total": "",
        "uptime": 0,
        "pid": os.getpid(),
    }
    try:
        # CPU load
        if hasattr(os, "getloadavg"):
            info["load_avg"] = [round(x, 2) for x in os.getloadavg()]
            info["cpu_percent"] = info["load_avg"][0] * 100 / os.cpu_count() if os.cpu_count() else info["load_avg"][0] * 100

        # Memory from /proc/meminfo
        try:
            with open("/proc/meminfo") as f:
                mem = {}
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        mem[parts[0].strip()] = int(parts[1].strip().split()[0])
                total = mem.get("MemTotal", 0)
                available = mem.get("MemAvailable", 0)
                used = total - available
                info["ram_total"] = f"{total // 1024} MB"
                info["ram_used"] = f"{used // 1024} MB"
                info["ram_percent"] = round(used / total * 100, 1) if total > 0 else 0
        except Exception:
            pass

        # Disk
        try:
            stat = os.statvfs("/")
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bavail
            used = total - free
            info["disk_total"] = f"{total // (1024**3)} GB"
            info["disk_used"] = f"{used // (1024**3)} GB"
            info["disk_percent"] = round(used / total * 100, 1) if total > 0 else 0
        except Exception:
            pass

        # Uptime
        try:
            with open("/proc/uptime") as f:
                info["uptime"] = float(f.read().split()[0])
        except Exception:
            info["uptime"] = time.time() - info.get("_start", time.time())

    except Exception as e:
        logger.debug("System info collection partial: %s", e)

    return info


def _format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.1f} MB"
    return f"{size_bytes / 1024**3:.1f} GB"


def _load_yaml_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}



def _validate_config(cfg):
    """校验配置合法性。返回 (ok, error_list)。"""
    errors = []
    VALID_BAUDRATES = {9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600}
    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}
    VALID_PARITY = {"N", "E", "O"}
    VALID_QOS = {0, 1, 2}

    def _chk_port(v, name):
        if not isinstance(v, int) or v < 1 or v > 65535:
            errors.append(name + "端口必须在1-65535之间, 当前值: " + str(v))

    def _chk_ip(v, name):
        if not v or not isinstance(v, str):
            errors.append(name + "IP地址不能为空")

    def _chk_positive(v, name):
        if not isinstance(v, (int, float)) or v <= 0:
            errors.append(name + "必须为正数, 当前值: " + str(v))

    # MQTT
    mq = cfg.get("mqtt", {})
    _chk_ip(mq.get("broker", ""), "MQTT Broker")
    _chk_port(mq.get("port", 0), "MQTT")
    if mq.get("keepalive", 0) < 1:
        errors.append("MQTT keepalive 至少1秒")
    if mq.get("qos", 0) not in VALID_QOS:
        errors.append("MQTT QoS 必须是0/1/2")

    # MAVLink
    ml = cfg.get("mavlink", {})
    _chk_ip(ml.get("host", ""), "MAVLink")
    _chk_port(ml.get("port", 0), "MAVLink")
    _chk_positive(ml.get("heartbeat_timeout", 0), "MAVLink heartbeat_timeout")

    # STM32
    st = cfg.get("stm32", {})
    if not st.get("port", ""):
        errors.append("STM32 串口不能为空")
    if st.get("baudrate", 0) not in VALID_BAUDRATES:
        errors.append("STM32 波特率无效, 可选: " + str(sorted(VALID_BAUDRATES)))
    if st.get("parity", "N") not in VALID_PARITY:
        errors.append("STM32 校验位必须是N/E/O")
    if st.get("data_bits", 0) not in {7, 8}:
        errors.append("STM32 数据位必须是7或8")
    if st.get("stop_bits", 0) not in {1, 2}:
        errors.append("STM32 停止位必须是1或2")
    _chk_positive(st.get("cmd_timeout", 0), "STM32 cmd_timeout")
    if st.get("cmd_retry", 0) < 1:
        errors.append("STM32 cmd_retry 至少为1")

    # Camera
    cam = cfg.get("camera", {})
    if cam.get("enabled", True):
        if cam.get("rtsp_url", ""):
            if not cam["rtsp_url"].startswith("rtsp://"):
                errors.append("Camera RTSP URL 必须以 rtsp:// 开头")
        else:
            _chk_ip(cam.get("ip", ""), "Camera")
            _chk_port(cam.get("port", 0), "Camera")
    if cam.get("snapshot_timeout", 0) < 1:
        errors.append("Camera snapshot_timeout 至少1秒")

    # Decision
    dc = cfg.get("decision", {})
    if not (0 <= dc.get("low_battery_threshold", 0) <= 100):
        errors.append("Decision low_battery_threshold 必须在0-100之间")
    _chk_positive(dc.get("lost_timeout", 0), "Decision lost_timeout")

    # Log
    lg = cfg.get("log", {})
    if lg.get("level", "INFO") not in VALID_LOG_LEVELS:
        errors.append("Log level 必须是 DEBUG/INFO/WARNING/ERROR")

    # Web UI
    wu = cfg.get("web_ui", {})
    _chk_port(wu.get("port", 0), "Web UI")

    return (len(errors) == 0, errors)

def _save_yaml_config(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)


class WebUI:
    """嵌入式 HTTP 服务器，提供专业级管理仪表盘。"""

    def __init__(self, config: dict, app_state, event_bus, stm32_comm=None, upgrade_mgr=None):
        self._host = config.get("host", "0.0.0.0")
        self._port = config.get("port", 8080)
        self._app_state = app_state
        self._event_bus = event_bus
        self._stm32 = stm32_comm
        self._upgrade_mgr = upgrade_mgr
        self._server = None
        self._config_path = "config.yaml"

    def start(self):
        handler = self._make_handler()
        self._server = HTTPServer((self._host, self._port), handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        logger.info("Web UI ready: http://%s:%d", self._host, self._port)
        self._app_state.log_event("webui", "info", "Web仪表盘已启动: http://" + self._host + ":" + str(self._port))

    def stop(self):
        if self._server:
            self._server.shutdown()
        logger.info("Web UI stopped")

    def _make_handler(self):
        ui = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                logger.debug("HTTP %s", args[0] if args else fmt)

            def _json(self, data, code=200):
                body = json.dumps(data, ensure_ascii=False).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json;charset=utf-8")
                self.send_header("Content-Length", len(body))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def _serve_file(self, path, content_type):
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.send_header("Content-Length", len(data))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)
                except Exception:
                    self._json({"error": "file not found"}, 404)

            def do_GET(self):
                path = urlparse(self.path).path
                qs = parse_qs(urlparse(self.path).query)

                if path == "/":
                    html = _load_dashboard()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html;charset=utf-8")
                    self.send_header("Content-Length", len(html.encode()))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(html.encode())

                elif path == "/api/status":
                    self._json(ui._app_state.to_dict())

                elif path == "/api/health":
                    self._json(ui._app_state.health())

                elif path == "/api/events":
                    count = int(qs.get("count", [50])[0])
                    self._json({"events": ui._app_state.get_events(count)})

                elif path == "/api/config":
                    try:
                        cfg = _load_yaml_config(ui._config_path)
                        self._json(cfg)
                    except Exception as e:
                        self._json({"error": str(e)}, 500)

                elif path == "/api/logs":
                    try:
                        log_dir = "./data/logs"
                        files = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")])
                        if files:
                            with open(os.path.join(log_dir, files[-1]), "r", encoding="utf-8") as f:
                                lines = f.readlines()
                            self._json({"lines": "".join(lines[-80:])})
                        else:
                            self._json({"lines": "(无日志)"})
                    except Exception as e:
                        self._json({"error": str(e)}, 500)

                elif path == "/api/system":
                    self._json(_get_system_info())

                elif path == "/api/camera/snapshots":
                    try:
                        snap_dir = "./data/snapshots"
                        if os.path.isdir(snap_dir):
                            files = sorted(
                                [f for f in os.listdir(snap_dir) if f.endswith(".jpg") or f.endswith(".png")],
                                reverse=True
                            )[:20]
                            result = []
                            for f in files:
                                fpath = os.path.join(snap_dir, f)
                                st = os.stat(fpath)
                                result.append({
                                    "name": f,
                                    "size": _format_size(st.st_size),
                                    "time": time.strftime("%H:%M:%S", time.localtime(st.st_mtime)),
                                })
                            self._json({"snapshots": result})
                        else:
                            self._json({"snapshots": []})
                    except Exception as e:
                        self._json({"error": str(e)}, 500)

                elif path.startswith("/api/camera/snapshot/") and len(path) > 22:
                    fname = os.path.basename(path)
                    fpath = os.path.join("./data/snapshots", fname)
                    ct = "image/png" if fname.endswith(".png") else "image/jpeg"
                    self._serve_file(fpath, ct)

                elif path == "/api/decision":
                    # Return decision rules from config
                    try:
                        cfg = _load_yaml_config(ui._config_path)
                        dc = cfg.get("decision", {})
                        rules = [
                            {
                                "name": "返航自动开舱",
                                "event": "DRONE_RTL",
                                "action": "OPEN_DOOR -> STM32",
                                "enabled": dc.get("auto_open_on_rtl", True),
                                "description": "检测到无人机进入RTL模式时自动打开发射舱门",
                            },
                            {
                                "name": "低电量告警",
                                "event": "DRONE_BATTERY_LOW",
                                "action": "ALARM -> MQTT",
                                "enabled": True,
                                "description": "无人机电量低于" + str(dc.get("low_battery_threshold", 20)) + "%时通过MQTT发送告警",
                            },
                            {
                                "name": "无人机失联告警",
                                "event": "DRONE_DISCONNECTED",
                                "action": "ALARM -> MQTT",
                                "enabled": True,
                                "description": "无人机失联超过" + str(dc.get("lost_timeout", 30)) + "秒时发送告警",
                            },
                            {
                                "name": "机库异常告警",
                                "event": "HANGAR_ALARM",
                                "action": "ALARM -> MQTT",
                                "enabled": True,
                                "description": "机库传感器异常（门故障/锁定异常等）时发送告警",
                            },
                            {
                                "name": "远程地面站指令转发",
                                "event": "MQTT_COMMAND",
                                "action": "FORWARD -> STM32",
                                "enabled": True,
                                "description": "接收并解析MQTT地面站下发的指令，转发到STM32执行",
                            },
                        ]
                        self._json({"rules": rules})
                    except Exception as e:
                        self._json({"error": str(e)}, 500)

                elif path == "/api/upgrade/status":
                    if ui._upgrade_mgr:
                        try:
                            state = ui._upgrade_mgr._state.value if hasattr(ui._upgrade_mgr, '_state') else "idle"
                            progress = getattr(ui._upgrade_mgr, '_progress', 0)
                            self._json({
                                "state": state,
                                "progress": progress,
                                "info": getattr(ui._upgrade_mgr, '_last_ack', "") or "",
                                "error": getattr(ui._upgrade_mgr, '_last_error', "") or "",
                            })
                        except Exception:
                            self._json({"state": "idle", "progress": 0, "info": "", "error": ""})
                    else:
                        self._json({"state": "unavailable", "progress": 0, "info": "Upgrade manager not loaded", "error": ""})

                else:
                    self._json({"error": "not found"}, 404)

            def do_POST(self):
                path = urlparse(self.path).path
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}

                if path == "/api/command":
                    cmd = body.get("cmd", "")
                    cmd_map = {"OPEN_DOOR": 0x01, "CLOSE_DOOR": 0x02, "LOCK": 0x03, "UNLOCK": 0x04}
                    code = cmd_map.get(cmd)
                    if code is not None and ui._stm32:
                        ui._stm32.send_command(code)
                        ui._app_state.log_event("webui", "info", "用户下发指令: " + cmd)
                        self._json({"ok": True, "cmd": cmd})
                    else:
                        self._json({"ok": False, "error": "unknown cmd or STM32 offline"})

                elif path == "/api/config":
                    ok, errs = _validate_config(body)
                    if not ok:
                        self._json({"ok": False, "error": "配置校验失败", "details": errs})
                        return
                    try:
                        _save_yaml_config(ui._config_path, body)
                        ui._app_state.log_event("webui", "info", "用户更新了配置文件(结构化)")
                        self._json({"ok": True})
                    except Exception as e:
                        self._json({"ok": False, "error": str(e)})

                elif path == "/api/restart":
                    ui._app_state.log_event("webui", "warn", "用户请求重启服务")
                    self._json({"ok": True, "msg": "请手动执行: sudo systemctl restart hangar"})

                elif path == "/api/camera/snapshot":
                    try:
                        snap_dir = "./data/snapshots"
                        os.makedirs(snap_dir, exist_ok=True)
                        fname = "snap_" + time.strftime("%Y%m%d_%H%M%S") + ".jpg"
                        fpath = os.path.join(snap_dir, fname)
                        # Signal camera module to take a snapshot via event bus
                        ui._event_bus.publish("CAMERA_SNAPSHOT", {"path": fpath})
                        ui._app_state.log_event("camera", "info", "WebUI触发手动抓拍: " + fname)
                        # Wait briefly for ffmpeg to complete
                        time.sleep(1)
                        if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                            self._json({"ok": True, "file": fname})
                        else:
                            self._json({"ok": True, "file": fname, "note": "等待摄像头模块写入..."})
                    except Exception as e:
                        self._json({"ok": False, "error": str(e)}, 500)

                elif path == "/api/upgrade/start":
                    fw_path = body.get("path", "")
                    if not fw_path:
                        self._json({"ok": False, "error": "缺少固件路径"})
                    elif ui._upgrade_mgr:
                        ok = ui._upgrade_mgr.start_upgrade(fw_path)
                        if ok:
                            ui._app_state.log_event("webui", "info", "用户启动固件升级: " + fw_path)
                            self._json({"ok": True})
                        else:
                            self._json({"ok": False, "error": "升级已在运行或启动失败"})
                    else:
                        self._json({"ok": False, "error": "升级管理器未加载"})

                elif path == "/api/upgrade/cancel":
                    if ui._upgrade_mgr:
                        try:
                            ui._upgrade_mgr._cancel_flag.set() if hasattr(ui._upgrade_mgr, '_cancel_flag') else None
                            ui._app_state.log_event("webui", "warn", "用户取消固件升级")
                            self._json({"ok": True})
                        except Exception as e:
                            self._json({"ok": False, "error": str(e)})
                    else:
                        self._json({"ok": False, "error": "升级管理器未加载"})

                else:
                    self._json({"error": "not found"}, 404)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()

        return Handler
