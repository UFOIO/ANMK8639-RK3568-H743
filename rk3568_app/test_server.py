import http.server, json, os, yaml, time, io, base64

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
    {"ts": NOW-30, "source": "system", "level": "info", "message": "机库控制系统启动"},
    {"ts": NOW-28, "source": "system", "level": "info", "message": "所有模块就绪，进入主循环"},
    {"ts": NOW-25, "source": "mavlink", "level": "warn", "message": "MAVLink连接断开，将自动重连"},
    {"ts": NOW-20, "source": "stm32", "level": "info", "message": "STM32串口已连接: /dev/ttyACM0"},
    {"ts": NOW-15, "source": "stm32", "level": "warn", "message": "STM32串口断开"},
    {"ts": NOW-10, "source": "stm32", "level": "error", "message": "STM32通信超时，指令重试3次失败"},
    {"ts": NOW-5,  "source": "webui", "level": "info", "message": "Web仪表盘已启动: http://0.0.0.0:8080"},
]

H = {
    "mavlink": {"status": "healthy", "connected": True, "last_hb_sec": 2.1, "last_pos_sec": 2.0},
    "mqtt":    {"status": "healthy", "connected": True, "last_msg_sec": 3.5},
    "stm32":   {"status": "healthy", "connected": True, "last_status_sec": 1.2},
    "camera":  {"status": "healthy", "last_snapshot_sec": 5.2},
    "uptime": 300,
    "drone": {"mode":"STABILIZE","armed":False,"satellites":12,"gps_fix":3,"alt_rel":45,"groundspeed":5.2,"battery":85,"voltage":24.8,"lat":0,"lon":0,"heading":180,"roll":2.1,"pitch":-1.5,"wp_current":3,"data_fresh":True,"protection":{},"airspeed":5.8,"climb":0.3,"yaw":178,"temperature":32.5,"nav_bearing":180,"wp_distance":120.5,"terrain_alt":50.2,"ekf_health":True,"ekf_horiz":0.12,"ekf_vert":0.08,"vtol_state":0,"landed_state":0,"wind_x":2.1,"wind_y":-1.3,"vib_x":0.05,"vib_y":0.04,"vib_z":0.06,"battery2":84},
    "hangar": {"door":"CLOSED","lock":"LOCKED","temp":25.5,"humidity":62,"alarm_flags":0},
    "system": {"cpu":15,"ram_pct":45,"ram_used":"1750M","ram_total":"3901M","disk_pct":30,"disk_used":"3.2G","disk_total":"16G","mosquitto":False},
    "events": EVENTS,
    "overall": "healthy"
}

def make_test_frame(w=320, h=240):
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (w, h), (10, 20, 40))
        draw = ImageDraw.Draw(img)
        for i in range(0, w, 40):
            draw.line([(i, 0), (i, h)], fill=(30, 50, 80), width=1)
        for i in range(0, h, 40):
            draw.line([(0, i), (w, i)], fill=(30, 50, 80), width=1)
        cx, cy = w//2, h//2
        draw.ellipse([cx-40,cy-40,cx+40,cy+40], outline=(0,150,200), width=2)
        draw.line([(cx-50,cy),(cx+50,cy)], fill=(0,200,0), width=1)
        draw.line([(cx,cy-50),(cx,cy+50)], fill=(0,200,0), width=1)
        ts = time.strftime("%H:%M:%S")
        draw.text((10, h-30), "ANMK8639 TEST | " + ts, fill=(0,200,0))
        draw.text((10, 10), "MJPEG SIMULATED", fill=(0,200,0))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=60)
        return buf.getvalue()
    except ImportError:
        return base64.b64decode("/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAAQABABAREA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYI3JicoKSo1NjY3OTBERUZHSEpGUlNVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDnKKKKAP/2Q==")

CRLF = "\r\n"
DOUBLE_CRLF = "\r\n\r\n"

_gortc_running = False

def get_camera_urls():
    port = 1984
    return {
        "local_mjpeg": "http://127.0.0.1:8088/api/camera/live",
        "local_mse": "http://127.0.0.1:" + str(port) + "/api/stream?src=camera",
        "local_webrtc": "http://127.0.0.1:" + str(port) + "/webrtc?src=camera",
        "remote_mjpeg": "http://127.0.0.1:8088/api/camera/live",
        "remote_mse": "http://192.168.1.99:" + str(port) + "/api/stream?src=camera",
        "remote_webrtc": "http://192.168.1.99:" + str(port) + "/webrtc?src=camera",
        "running": True
    }

class X(http.server.BaseHTTPRequestHandler):
    def _j(self, d, c=200):
        self.send_response(c)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(d, ensure_ascii=False).encode())

    def _mjpeg_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            while True:
                frame = make_test_frame()
                self.wfile.write(b"--frame" + CRLF.encode())
                self.wfile.write(b"Content-Type: image/jpeg" + CRLF.encode())
                self.wfile.write(f"Content-Length: {len(frame)}".encode() + CRLF.encode())
                self.wfile.write(CRLF.encode())
                self.wfile.write(frame)
                self.wfile.write(CRLF.encode())
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def do_GET(self):
        import urllib.parse
        p = urllib.parse.urlparse(self.path).path
        if p == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASH)
        elif p == "/api/health": self._j(H)
        elif p == "/api/decision": self._j({"rules": RULES})
        elif p == "/api/events":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            count = int(qs.get("count", [50])[0])
            self._j({"events": EVENTS[:count]})
        elif p == "/api/logs": self._j({"logs": ["[INFO] 系统启动完成", "[WARN] MAVLink 未连接", "[INFO] STM32 等待连接"]})
        elif p == "/api/config": self._j(cfg)
        elif p == "/api/camera/live": self._mjpeg_stream()
        elif p == "/api/camera/urls": self._j(get_camera_urls())
        else: self._j({"error": "not found"}, 404)

    def do_POST(self):
        global _gortc_running
        p = __import__("urllib").parse.urlparse(self.path).path
        l = int(self.headers.get("Content-Length", 0))
        b = json.loads(self.rfile.read(l)) if l else {}
        if p == "/api/config": self._j({"ok": True})
        elif p in ("/api/camera/preview/start", "/api/camera/relay/start"):
            _gortc_running = True
            self._j({"ok": True, "msg": "go2rtc started (sim)", "urls": get_camera_urls()})
        elif p in ("/api/camera/preview/stop", "/api/camera/relay/stop"):
            _gortc_running = False
            self._j({"ok": True, "msg": "go2rtc stopped"})
        elif p == "/api/camera/snapshot":
            self._j({"ok": True, "path": "./data/snapshots/snap_test.jpg"})
        else: self._j({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass

print("=== ANMK8639 Test Server ===")
print("Dashboard: http://127.0.0.1:8088")
print("Camera preview API: /api/camera/live (MJPEG test stream)")
print()

import sys; sys.stdout.flush()
http.server.HTTPServer(("127.0.0.1", 8088), X).serve_forever()