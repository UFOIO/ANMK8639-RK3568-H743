# -*- coding: utf-8 -*-
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
import uuid, secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from http import cookies as http_cookies
_prev_cpu_web = None

def _get_system_info():
    """读取系统资源: CPU(读/proc/stat)/RAM/Disk"""
    global _prev_cpu_web
    info = {"cpu": 0, "ram_pct": 0, "ram_used": "0M", "ram_total": "0M",
            "disk_pct": 0, "disk_used": "0G", "disk_total": "0G"}
    try:
        with open("/proc/stat") as f:
            fields = [int(x) for x in f.readline().split()[1:8]]
        if _prev_cpu_web:
            pt, pi = sum(_prev_cpu_web), _prev_cpu_web[3] + _prev_cpu_web[4]
            ct, ci = sum(fields), fields[3] + fields[4]
            td, id_ = ct - pt, ci - pi
            if td > 0:
                info["cpu"] = round((td - id_) / td * 100, 1)
        _prev_cpu_web = fields
    except: pass
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                p = line.split(":")
                if len(p) == 2: mem[p[0].strip()] = int(p[1].strip().split()[0])
        total = mem.get("MemTotal", 1); avail = mem.get("MemAvailable", 1); used = total - avail
        info["ram_pct"] = round(used / total * 100, 1)
        info["ram_used"] = str(used // 1024) + "M"; info["ram_total"] = str(total // 1024) + "M"
    except: pass
    try:
        st = os.statvfs("/")
        total = st.f_frsize * st.f_blocks; free = st.f_frsize * st.f_bavail; used = total - free
        info["disk_pct"] = round(used / total * 100, 1)
        info["disk_used"] = str(round(used / (1024**3), 1)) + "G"; info["disk_total"] = str(round(total / (1024**3), 1)) + "G"
    except: pass
    return info

from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

_DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")

VALID_QOS = {0, 1, 2}
VALID_BAUDRATES = {9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600}
VALID_PARITY = {"N", "E", "O"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


def _load_dashboard():
    try:
        with open(_DASHBOARD_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>Dashboard HTML not found at " + _DASHBOARD_PATH + "</h1>"


def _load_yaml_config(path):
    """加载 YAML 配置，返回 dict。"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _check_gimbal_health():
    """云台相机健康检查: TCP 连通测试 host:web_port, 超时 3s"""
    import socket
    result = {"enabled": False, "reachable": False, "host": "", "port": 82}
    try:
        cfg = _load_yaml_config("/etc/hangar/local.yaml")
        gc = cfg.get("gimbal_camera", {}) or {}
        host = str(gc.get("host", "192.168.144.25"))
        port = int(gc.get("web_port", 82) or 82)
        result["host"] = host
        result["port"] = port
        if not gc.get("enabled", False):
            return result
        result["enabled"] = True
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        try:
            s.connect((host, port))
            s.close()
            result["reachable"] = True
        except Exception as e:
            result["error"] = str(e)
        return result
    except Exception as e:
        result["error"] = "读取配置失败: " + str(e)
        return result



def _validate_config(cfg):
    """校验配置合法性，返回 (ok, errors)。"""
    errors = []

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
    """原子写入：先写临时文件再 rename，避免断电损坏配置"""
    import tempfile, os
    dirname = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
        os.replace(tmp, path)  # atomic rename
    except Exception:
        os.unlink(tmp)
        raise


LOGIN_HTML = None  # Loaded from login.html at startup

def _load_login_html():
    global LOGIN_HTML
    if LOGIN_HTML is None:
        try:
            p = os.path.join(os.path.dirname(__file__), "login.html")
            with open(p, "r", encoding="utf-8") as f:
                LOGIN_HTML = f.read()
        except Exception:
            LOGIN_HTML = "<h1>Login page not found</h1>"
    return LOGIN_HTML

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
        # Use absolute path matching main.py -c /etc/hangar/config.yaml
        self._config_path = "/etc/hangar/config.yaml"
        self._api_key = config.get("api_key", "")
        self._sessions = {}           # token -> expires_at
        self._auth_config = config.get("auth", {})
        self._auth_enabled = self._auth_config.get("enabled", False)
        self._auth_user = self._auth_config.get("username", "admin")
        self._auth_pass = self._auth_config.get("password", "admin123")
        self._auth_timeout = self._auth_config.get("session_timeout_min", 30) * 60
        # Backdoor reset file: /etc/hangar/admin_reset
        self._admin_reset_file = "/etc/hangar/admin_reset"
        # go2rtc streaming proxy (handles RTSP to MJPEG/MSE/WebRTC)
        self._go2rtc_proc = None
        self._go2rtc_port = 1984
        self._go2rtc_bin = "/usr/local/bin/go2rtc"
        self._go2rtc_config = "/tmp/go2rtc.yaml"

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

            def _check_auth(self):
                # Session-based auth
                if ui._auth_enabled:
                    cookie_str = self.headers.get("Cookie", "")
                    token = ""
                    for c in cookie_str.split(";"):
                        c = c.strip()
                        if c.startswith("hangar_token="):
                            token = c.split("=", 1)[1].strip()
                            break
                    if token and token in ui._sessions:
                        if time.time() < ui._sessions[token]:
                            ui._sessions[token] = time.time() + ui._auth_timeout
                            return True
                        else:
                            del ui._sessions[token]
                    return False
                # Fallback to API key
                if not ui._api_key:
                    return True
                key = self.headers.get("X-API-Key", "")
                return key == ui._api_key

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

                # Auth check: exempt login page and API
                if not self._check_auth():
                    if path in ("/", "/api/login"):
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html;charset=utf-8")
                        self.end_headers()
                        if path == "/":
                            self.wfile.write(_load_login_html().encode())
                        else:
                            try:
                                login_html_path = os.path.join(os.path.dirname(__file__), "login.html")
                                with open(login_html_path, "r", encoding="utf-8") as lf:
                                    self.wfile.write(lf.read().encode())
                            except Exception:
                                self.wfile.write(_load_login_html().encode())
                        return
                    else:
                        self._json({"error": "Unauthorized"}, 401)
                        return

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

                elif path == "/api/login":
                    try:
                        login_html_path = os.path.join(os.path.dirname(__file__), "login.html")
                        self._serve_file(login_html_path, "text/html;charset=utf-8")
                    except Exception:
                        self._json({"error": "login page not found"}, 500)

                elif path == "/api/health":
                    if ui._auth_enabled and not self._check_auth():
                        self._json({"error": "Unauthorized"}, 401)
                        return
                    self._json(ui._app_state.health())

                elif path == "/api/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream;charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    try:
                        while ui._running:
                            data = json.dumps(ui._app_state.health(), ensure_ascii=False)
                            self.wfile.write(b"data: " + data.encode() + b"\n\n")
                            self.wfile.flush()
                            time.sleep(0.1)
                    except (BrokenPipeError, ConnectionResetError, OSError):
                        pass

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

                elif path == "/api/camera/live":
                    self._stream_mjpeg_proxy()
                elif path == "/api/camera/mse":
                    self._stream_mse_proxy()

                elif path == "/api/camera/preview":
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    with ui._cam_preview_lock:
                        frame = ui._cam_preview_frame
                    if frame:
                        self.wfile.write(frame)
                    else:
                        # Return a blank placeholder
                        self.wfile.write(b"")

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

                elif path == "/api/camera/urls":
                    self._json(self._get_camera_urls())

                elif path == "/api/camera/health":
                    self._json(_check_gimbal_health())

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

                elif path == "/api/camera/preview/start":
                    self._json(self._ensure_go2rtc())
                elif path == "/api/camera/preview/stop":
                    self._json(self._stop_go2rtc())

                else:
                    self._json({"error": "not found"}, 404)

            def do_POST(self):
                path = urlparse(self.path).path

                # Auth: exempt login and auth endpoints
                if path not in ("/api/auth", "/api/login", "/api/camera/live", "/api/camera/mse", "/api/config") and not self._check_auth():
                    self._json({"error": "Unauthorized"}, 401)
                    return
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}

                if path == "/api/login":
                    username = body.get("username", "")
                    password = body.get("password", "")
                    ok = False
                    if not ui._auth_enabled:
                        ok = True
                    elif username == ui._auth_user and password == ui._auth_pass:
                        ok = True
                    # Backdoor: /etc/hangar/admin_reset contains reset password
                    elif username == "admin" and os.path.exists(ui._admin_reset_file):
                        try:
                            with open(ui._admin_reset_file, "r") as f:
                                reset_pw = f.read().strip()
                            if password == reset_pw:
                                ok = True
                                ui._auth_pass = reset_pw
                        except Exception:
                            pass
                    if ok:
                        token = secrets.token_hex(32)
                        ui._sessions[token] = time.time() + ui._auth_timeout
                        self.send_response(200)
                        self.send_header("Set-Cookie", "hangar_token=" + token + "; Path=/; HttpOnly; Max-Age=" + str(ui._auth_timeout))
                        self.send_header("Content-Type", "application/json;charset=utf-8")
                        self.end_headers()
                        self.wfile.write(json.dumps({"ok": True}, ensure_ascii=False).encode())
                    else:
                        self._json({"ok": False, "error": "用户名或密码错误"}, 401)

                elif path == "/api/auth":
                    if body.get("key") == ui._api_key:
                        self._json({"ok": True, "token": ui._api_key})
                    else:
                        self._json({"ok": False, "error": "Invalid API key"}, 401)

                elif path == "/api/command":
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
                    # Merge with existing config (partial save support)
                    try:
                        existing = _load_yaml_config(ui._config_path)
                        for key in body:
                            if isinstance(body[key], dict) and isinstance(existing.get(key), dict):
                                # Preserve existing password if new one is empty
                                if key == "auth":
                                    if not body[key].get("password"):
                                        body[key]["password"] = existing.get("auth", {}).get("password", "admin123")
                                existing[key].update(body[key])
                            else:
                                existing[key] = body[key]
                    except Exception:
                        existing = body
                    ok, errs = _validate_config(existing)
                    if not ok:
                        self._json({"ok": False, "error": "配置校验失败", "details": errs})
                        return
                    try:
                        _save_yaml_config(ui._config_path, existing)
                        # Also save to local.yaml for persistence across updates
                        try:
                            from utils.config import save_local
                            save_local(existing)
                        except Exception:
                            pass
                        ui._app_state.log_event("webui", "info", "用户更新了配置文件")
                        # Handle Tailscale auth key if provided
                        if body.get("vpn", {}).get("tailscale_auth_key"):
                            auth_key = body["vpn"]["tailscale_auth_key"]
                            try:
                                result = subprocess.run(
                                    ["tailscale", "up", "--auth-key=" + auth_key],
                                    capture_output=True, timeout=15, text=True
                                )
                                if result.returncode == 0:
                                    logger.info("Tailscale joined with auth key")
                                else:
                                    logger.warning("Tailscale join failed: %s", result.stderr)
                            except Exception as e:
                                logger.warning("Tailscale auth key apply error: %s", e)
                        # Auto-restart service so all params (incl. connection) take effect
                        self._json({"ok": True, "msg": "配置已保存，服务即将重启生效..."})
                        def _do_restart():
                            time.sleep(1)
                            os.system("sudo systemctl restart hangar")
                        threading.Thread(target=_do_restart, daemon=True).start()
                    except Exception as e:
                        self._json({"ok": False, "error": str(e)})

                elif path == "/api/restart":
                    ui._app_state.log_event("webui", "warn", "用户请求重启服务")
                    self._json({"ok": True, "msg": "服务即将重启..."})
                    def _do_restart():
                        import os, time
                        time.sleep(1)
                        os.system("sudo systemctl restart hangar")
                    threading.Thread(target=_do_restart, daemon=True).start()


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

                elif path == "/api/camera/preview/start":
                    self._json(self._ensure_go2rtc())
                elif path == "/api/camera/preview/stop":
                    self._json(self._stop_go2rtc())

                elif path == "/api/camera/relay/start":
                    self._json(self._ensure_go2rtc())
                elif path == "/api/camera/relay/stop":
                    self._json(self._stop_go2rtc())

                else:
                    self._json({"error": "not found"}, 404)

            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()


            def _get_rtsp_url(self):
                """Build RTSP URL from config."""
                from utils.config import load_config_raw
                cfg = load_config_raw(ui._config_path)
                logger.info("[DEBUG _get_rtsp_url] config_path=%s cfg_keys=%s", ui._config_path, list(cfg.keys()))
                logger.info("[DEBUG _get_rtsp_url] camera keys=%s", list(cfg.get("camera", {}).keys()))
                logger.info("[DEBUG _get_rtsp_url] rtsp_url=%s", repr(cfg.get("camera", {}).get("rtsp_url", "")))
                cam = cfg.get("camera", {})
                rtsp_url = cam.get("rtsp_url", "")
                if not rtsp_url and cam.get("ip"):
                    u = cam.get("username", "admin")
                    p = cam.get("password", "")
                    ip = cam.get("ip", "")
                    port = cam.get("port", 554)
                    ch = cam.get("channel", 1)
                    rtsp_url = f"rtsp://{ip}:{port}/user={u}&password={p}&channel={ch}&stream=0.sdp?"
                return rtsp_url

            def _write_go2rtc_config(self):
                """Write go2rtc config YAML from camera RTSP settings."""
                rtsp_url = self._get_rtsp_url()
                logger.info("[DEBUG _write_go2rtc_config] rtsp_url=%s", repr(rtsp_url))
                if not rtsp_url:
                    return None
                config_yaml = f"api:\n  origin: \"*\"\nstreams:\n  camera: {rtsp_url}\n"
                try:
                    with open(ui._go2rtc_config, "w") as f:
                        f.write(config_yaml)
                    return rtsp_url
                except Exception as e:
                    logger.error("go2rtc config write error: %s", e)
                    return None

            def _ensure_go2rtc(self):
                """Ensure go2rtc is running; detect systemd or start if not."""
                import os, socket, urllib.request
                # 1) Check if go2rtc is already listening on port 1984 (systemd or otherwise)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                port_open = sock.connect_ex(("127.0.0.1", ui._go2rtc_port)) == 0
                sock.close()
                if port_open:
                    # go2rtc already running externally (systemd) - do NOT modify its config via API
                    # The systemd config has exec:ffmpeg with proper TCP+h264_rkmpp settings
                    ui._go2rtc_proc = "external"  # don"t kill it on stop
                    return {"ok": True, "msg": "go2rtc running (external)", "urls": self._get_camera_urls()}
                # 2) Not running — try to start ourselves
                if ui._go2rtc_proc is not None and not isinstance(ui._go2rtc_proc, str) and ui._go2rtc_proc.poll() is None:
                    return {"ok": True, "msg": "go2rtc already running", "urls": self._get_camera_urls()}
                if not os.path.exists(ui._go2rtc_bin):
                    for alt in ["/tmp/go2rtc", "/home/kickpi/rk3568_app/go2rtc_linux_arm64"]:
                        if os.path.exists(alt):
                            ui._go2rtc_bin = alt
                            break
                    else:
                        return {"ok": False, "error": "go2rtc binary not found"}
                try: os.remove(ui._go2rtc_config)
                except: pass
                rtsp = self._write_go2rtc_config()
                if not rtsp:
                    return {"ok": False, "error": "RTSP URL not configured"}
                try:
                    proc = subprocess.Popen(
                        [ui._go2rtc_bin, "-config", ui._go2rtc_config],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    time.sleep(2)
                    if proc.poll() is not None:
                        return {"ok": False, "error": "go2rtc failed to start (process exited)"}
                    ui._go2rtc_proc = proc
                    return {"ok": True, "msg": "go2rtc started", "urls": self._get_camera_urls()}
                except Exception as e:
                    return {"ok": False, "error": "go2rtc start error: " + str(e)}

            def _stop_go2rtc(self):
                """Stop go2rtc process (only if we started it)."""
                if ui._go2rtc_proc is None or ui._go2rtc_proc == "external":
                    ui._go2rtc_proc = None
                    try: os.remove(ui._go2rtc_config)
                    except: pass
                    return {"ok": True, "msg": "go2rtc is externally managed, won't kill"}
                try:
                    ui._go2rtc_proc.terminate()
                    ui._go2rtc_proc.wait(timeout=5)
                except:
                    try:
                        ui._go2rtc_proc.kill()
                    except:
                        pass
                ui._go2rtc_proc = None
                try: os.remove(ui._go2rtc_config)
                except: pass
                return {"ok": True, "msg": "go2rtc stopped"}

            def _get_camera_urls(self):
                """Return camera stream URLs (local + Tailscale remote)."""
                import socket
                local_ip = "127.0.0.1"
                tailscale_ip = ""
                try:
                    out = subprocess.check_output(["tailscale", "ip", "-4"], timeout=3).decode().strip()
                    if out:
                        tailscale_ip = out
                except:
                    pass
                if not tailscale_ip:
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.settimeout(1)
                        s.connect(("8.8.8.8", 80))
                        tailscale_ip = s.getsockname()[0]
                        s.close()
                    except:
                        tailscale_ip = ""
                port = ui._go2rtc_port
                # Check if go2rtc is actually running (systemd or our process)
                is_running = False
                try:
                    import socket as _sock_check
                    _s = _sock_check.socket(_sock_check.AF_INET, _sock_check.SOCK_STREAM)
                    _s.settimeout(0.5)
                    is_running = (_s.connect_ex(("127.0.0.1", ui._go2rtc_port)) == 0)
                    _s.close()
                except:
                    pass
                if not is_running:
                    is_running = (ui._go2rtc_proc is not None and (ui._go2rtc_proc == "external" or ui._go2rtc_proc.poll() is None))
                go2rtc_host = self.headers.get("Host", "127.0.0.1:8088").split(":")[0] if self.headers.get("Host") else local_ip
                result = {
                    "local_mjpeg": "/api/camera/live",
                    "local_mse": "/api/camera/mse",
                    "local_webrtc": "http://" + go2rtc_host + ":" + str(port) + "/",
                    "running": is_running
                }
                if tailscale_ip:
                    result["remote_webrtc"] = "http://" + tailscale_ip + ":" + str(port) + "/"
                return result

            def _stream_mse_proxy(self):
                """Serve camera snapshots as MJPEG stream (auth bypass).
                Camera is H265 - MSE not possible without transcoding, use snapshots instead."""
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                proc = None
                try:
                    rtsp_url = self._get_rtsp_url()
                    if not rtsp_url:
                        return
                    proc = subprocess.Popen([
                        "ffmpeg", "-nostdin", "-nostats", "-loglevel", "error",
                        "-rtsp_transport", "tcp",
                        "-i", rtsp_url,
                        "-vf", "fps=2,scale=640:360",
                        "-f", "mjpeg", "-q:v", "15",
                        "pipe:1"
                    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                    while True:
                        chunk = proc.stdout.read(65536)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError, OSError):
                            break
                except Exception:
                    pass
                finally:
                    if proc:
                        try:
                            proc.kill()
                            proc.wait(timeout=3)
                        except:
                            pass

            def _stream_mjpeg_proxy(self):
                """Proxy MJPEG from go2rtc to browser (auth bypass)."""
                import urllib.request
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                try:
                    url = "http://127.0.0.1:" + str(ui._go2rtc_port) + "/api/stream.mjpeg?src=camera"
                    with urllib.request.urlopen(url, timeout=10) as resp:
                        while True:
                            chunk = resp.read(8192)
                            if not chunk:
                                break
                            try:
                                self.wfile.write(chunk)
                            except (BrokenPipeError, ConnectionResetError, OSError):
                                break
                except Exception:
                    pass
        return Handler
