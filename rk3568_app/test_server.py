import http.server, json, os, yaml, time
os.chdir(r"C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app")

DASH = open("modules/dashboard.html", "rb").read()
cfg = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))
dc = cfg.get("decision", {})

RULES = [
    {"name": "返航自动开舱", "event": "DRONE_RTL", "action": "OPEN_DOOR -> STM32", "enabled": dc.get("auto_open_on_rtl", True), "description": "检测到无人机进入RTL模式时自动打开发射舱门"},
    {"name": "低电量告警", "event": "DRONE_BATTERY_LOW", "action": "ALARM -> MQTT", "enabled": True, "description": "无人机电量低于" + str(dc.get("low_battery_threshold", 20)) + "%时通过MQTT发送告警"},
    {"name": "无人机失联告警", "event": "DRONE_DISCONNECTED", "action": "ALARM -> MQTT", "enabled": True, "description": "无人机失联超过" + str(dc.get("lost_timeout", 30)) + "秒时发送告警"},
    {"name": "机库异常告警", "event": "HANGAR_ALARM", "action": "ALARM -> MQTT", "enabled": True, "description": "机库传感器异常时发送告警"},
    {"name": "远程地面站指令转发", "event": "MQTT_COMMAND", "action": "FORWARD -> STM32", "enabled": True, "description": "接收并解析MQTT地面站下发指令转发到STM32执行"},
]

NOW = time.time()
EVENTS = [
    {"ts": NOW - 30, "source": "system", "level": "info", "message": "机库控制系统启动"},
    {"ts": NOW - 28, "source": "system", "level": "info", "message": "所有模块就绪，进入主循环"},
    {"ts": NOW - 25, "source": "mavlink", "level": "warn", "message": "MAVLink连接断开，将自动重连"},
    {"ts": NOW - 20, "source": "stm32", "level": "info", "message": "STM32串口已连接: /dev/ttyACM0"},
    {"ts": NOW - 15, "source": "stm32", "level": "warn", "message": "STM32串口断开"},
    {"ts": NOW - 10, "source": "stm32", "level": "error", "message": "STM32通信超时，指令重试3次失败"},
    {"ts": NOW - 5, "source": "webui", "level": "info", "message": "Web仪表盘已启动: http://0.0.0.0:8080"},
]

H = {
    "mavlink": {"status": "dead", "connected": False, "last_hb_sec": None, "last_pos_sec": None},
    "mqtt": {"status": "dead", "connected": False, "last_msg_sec": None},
    "stm32": {"status": "dead", "connected": False, "last_status_sec": None},
    "camera": {"status": "healthy", "last_snapshot_sec": 5.2},
    "uptime": 300,
    "drone": {"mode": "STABILIZE", "armed": False, "satellites": 0, "gps_fix": 0, "alt_rel": 0, "groundspeed": 0, "battery": 100, "voltage": 25.2, "lat": 0, "lon": 0, "heading": 0, "roll": 0, "pitch": 0, "wp_current": 0},
    "hangar": {"door": "CLOSED", "lock": "LOCKED", "temp": 25, "humidity": 60, "alarm_flags": 0},
    "system": {"cpu": 15, "ram_pct": 45, "ram_used": "1750M", "ram_total": "3901M", "disk_pct": 30, "disk_used": "3.2G", "disk_total": "16G"},
    "events": EVENTS,
    "overall": "degraded"
}

class X(http.server.BaseHTTPRequestHandler):
    def _j(s, d, c=200):
        s.send_response(c); s.send_header("Content-Type", "application/json; charset=utf-8")
        s.send_header("Access-Control-Allow-Origin", "*"); s.end_headers()
        s.wfile.write(json.dumps(d, ensure_ascii=False).encode())
    def do_GET(s):
        import urllib.parse; p = urllib.parse.urlparse(s.path).path
        if p == "/": s.send_response(200); s.send_header("Content-Type", "text/html; charset=utf-8"); s.end_headers(); s.wfile.write(DASH)
        elif p == "/api/health": s._j(H)
        elif p == "/api/decision": s._j({"rules": RULES})
        elif p == "/api/events":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(s.path).query)
            count = int(qs.get("count", [50])[0])
            s._j({"events": EVENTS[:count]})
        elif p == "/api/logs": s._j({"logs": ["[INFO] 系统启动完成", "[WARN] MAVLink 未连接", "[INFO] STM32 等待连接"]})
        elif p == "/api/config": s._j(cfg)
        else: s._j({"error": "not found"}, 404)
    def do_POST(s):
        import urllib.parse; p = urllib.parse.urlparse(s.path).path
        l = int(s.headers.get("Content-Length", 0)); b = json.loads(s.rfile.read(l)) if l else {}
        if p == "/api/config": s._j({"ok": True})
        else: s._j({"error": "not found"}, 404)
    def do_OPTIONS(s):
        s.send_response(204); s.send_header("Access-Control-Allow-Origin", "*")
        s.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS"); s.send_header("Access-Control-Allow-Headers", "Content-Type"); s.end_headers()

import sys; sys.stdout.flush()
http.server.HTTPServer(("127.0.0.1", 8088), X).serve_forever()
