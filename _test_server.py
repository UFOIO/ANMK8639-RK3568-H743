import json, time, os, threading, http.server

# Mock health data for local testing
def mock_health():
    return {
        "mavlink": {"status": "healthy", "connected": True, "last_hb_sec": 0.5, "last_pos_sec": 1.2},
        "mqtt": {"status": "healthy", "connected": True, "last_msg_sec": 2.1},
        "stm32": {"status": "stale", "connected": True, "last_status_sec": 8.5},
        "camera": {"status": "healthy", "last_snapshot_sec": 15.0},
        "uptime": 3600,
        "drone": {
            "mode": "LOITER", "armed": True, "satellites": 18, "gps_fix": 3,
            "alt_rel": 120.5, "groundspeed": 5.2, "battery": 85, "voltage": 23.8,
            "lat": 40.123456, "lon": 116.654321, "heading": 270,
            "roll": 2.1, "pitch": -1.5, "wp_current": 3
        },
        "hangar": {
            "door": "CLOSED", "lock": "LOCKED", "temp": 28.5, "humidity": 65.2, "alarm_flags": 0
        },
        "system": {"cpu": 35.2, "ram_pct": 45.1, "ram_used": "876M", "ram_total": "3901M",
                    "disk_pct": 22.0, "disk_used": "3.2G", "disk_total": "14.5G"},
        "events": [
            {"ts": time.time()-10, "source": "mavlink", "level": "info", "message": "Heartbeat OK"},
            {"ts": time.time()-30, "source": "stm32", "level": "warn", "message": "Status report delayed"},
            {"ts": time.time()-60, "source": "system", "level": "info", "message": "Service started"},
        ],
        "overall": "degraded"
    }

mock_rules = [
    {"name": "RTL Auto Open", "event": "DRONE_RTL", "action": "OPEN_DOOR", "enabled": True, "description": "Auto open door on RTL"},
    {"name": "Low Battery", "event": "DRONE_BATTERY_LOW", "action": "ALARM", "enabled": True, "description": "MQTT alarm when battery < 20%"},
    {"name": "Lost Drone", "event": "DRONE_DISCONNECTED", "action": "ALARM", "enabled": True, "description": "Alarm after 30s no heartbeat"},
    {"name": "Hangar Alarm", "event": "HANGAR_ALARM", "action": "ALARM", "enabled": False, "description": "Sensor anomaly alarm"},
    {"name": "MQTT Forward", "event": "MQTT_COMMAND", "action": "FORWARD", "enabled": True, "description": "Forward MQTT commands to STM32"},
]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            with open("rk3568_app/modules/dashboard.html", "rb") as f:
                html = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(html))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html)
        elif self.path == "/api/health":
            self._json(mock_health())
        elif self.path == "/api/decision":
            self._json({"rules": mock_rules})
        elif self.path == "/api/events":
            self._json({"events": mock_health()["events"]})
        elif self.path == "/api/logs":
            self._json({"lines": "[TEST] System log..."})
        elif self.path == "/api/config":
            self._json({})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        self._json({"ok": True})

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

s = http.server.HTTPServer(("127.0.0.1", 8088), Handler)
print("Test server: http://127.0.0.1:8088")
print("Ctrl+C to stop")
s.serve_forever()
