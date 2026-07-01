#!/usr/bin/env python3
"""
云台相机媒体代理 - 测试脚本
用法: python3 test_camera_proxy.py [--port 8081]
配置: 从 config.yaml 的 gimbal_camera 段读取

原理: RK3568 连上 4G 模块 WiFi 后,通过局域网访问云台 Web Server,
     再把媒体列表和文件流式透传给调度系统。
"""

import json
import sys
import os
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# === 从 config.yaml 加载配置 ===
try:
    import yaml
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(SCRIPT_DIR, "config.yaml"), "r", encoding="utf-8") as f:
        _cfg = yaml.safe_load(f)
    GC = _cfg.get("gimbal_camera", {})
except Exception:
    print("[警告] 无法读取 config.yaml，使用默认值")
    GC = {}

CAMERA_HOST = GC.get("host", "192.168.144.25")
CAMERA_PORT = GC.get("web_port", 82)
WIFI_SSID = GC.get("wifi_ssid", "")
WIFI_PASS = GC.get("wifi_password", "")
PROXY_PORT = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--port" else GC.get("proxy_port", 8081)

CAMERA_BASE = f"http://{CAMERA_HOST}:{CAMERA_PORT}/cgi-bin/media.cgi"

# ================================================================

class CameraProxyHandler(BaseHTTPRequestHandler):
    """HTTP 反向代理: 调度系统 → RK3568 → 云台相机 (流式, 不落盘)"""

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")

    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, msg, code=500):
        self._send_json({"success": False, "error": msg}, code)

    def _call_camera(self, endpoint, params=None):
        """调用云台 REST API"""
        url = f"{CAMERA_BASE}{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        print(f"  -> {url}")
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"success": False, "error": str(e)}

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        path = p.path
        q = dict(urllib.parse.parse_qsl(p.query))

        # ---- 测试: 列出目录 ----
        if path == "/test/list":
            result = self._call_camera("/api/v1/getdirectories", {"media_type": 0})
            self._send_json(result)

        # ---- 测试: 列出文件 ----
        elif path == "/test/files":
            result = self._call_camera("/api/v1/getmedialist", {
                "media_type": 0, "path": q.get("path", ""),
                "start": 0, "count": 100
            })
            self._send_json(result)

        # ---- 代理下载: 流式透传, 不落盘 (核心) ----
        elif path == "/test/download":
            file_url = q.get("url", "")
            if not file_url:
                return self._send_error("缺少 url 参数", 400)
            # SDK 返回的 url 里 host 可能是 xxx, 替换为实际 IP
            file_url = file_url.replace("http://xxx", f"http://{CAMERA_HOST}:{CAMERA_PORT}")
            print(f"  [流式下载] {file_url}")
            try:
                req = urllib.request.Request(file_url)
                with urllib.request.urlopen(req, timeout=30) as up:
                    self.send_response(200)
                    self.send_header("Content-Type", up.headers.get("Content-Type", "image/jpeg"))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    while True:
                        chunk = up.read(4096)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            except Exception as e:
                self._send_error(f"下载失败: {e}")

        # ---- 连通性检查 ----
        elif path == "/test/ping":
            result = self._call_camera("/api/v1/getdirectories", {"media_type": 0})
            self._send_json({
                "success": result.get("success", False),
                "camera": f"{CAMERA_HOST}:{CAMERA_PORT}",
                "detail": "connected" if result.get("success") else result
            })

        # ---- 首页 ----
        else:
            self._serve_page()

    def _serve_page(self):
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>云台代理测试</title>
<style>
body{{font-family:system-ui;max-width:800px;margin:30px auto;padding:15px}}
h2{{color:#333}} code{{background:#f4f4f4;padding:2px 6px;border-radius:3px}}
.btn{{margin:4px;padding:8px 14px;background:#007aff;color:#fff;border:none;border-radius:5px;cursor:pointer}}
.result{{background:#f9f9f9;padding:12px;border-radius:5px;white-space:pre-wrap;font-size:12px;max-height:400px;overflow:auto;margin-top:8px}}
a{{color:#007aff}}
</style></head><body>
<h2>云台相机媒体代理测试</h2>
<p>相机: <code>{CAMERA_HOST}:{CAMERA_PORT}</code> | 代理: <code>:{PROXY_PORT}</code></p>
<button class="btn" onclick="call('/test/ping')">连通检查</button>
<button class="btn" onclick="call('/test/list')">照片目录</button>
<button class="btn" onclick="call('/test/files')">文件列表</button>
<div class="result" id="out">点击按钮测试...</div>
<script>
async function call(url) {{
    document.getElementById('out').textContent = '请求中...';
    try {{
        const r = await fetch(url); const t = await r.text();
        try {{
            const j = JSON.parse(t);
            if (j.data && j.data.list) {{
                let h = '<b>文件 (点击下载):</b><br>';
                j.data.list.forEach(f => h += `<a href="/test/download?url=${{encodeURIComponent(f.url)}}" target="_blank">${{f.name}}</a><br>`);
                h += '<hr><pre>'+t+'</pre>';
                document.getElementById('out').innerHTML = h;
            }} else {{ document.getElementById('out').textContent = t; }}
        }} catch(e) {{ document.getElementById('out').textContent = t; }}
    }} catch(e) {{ document.getElementById('out').textContent = '❌ 连接失败: '+e.message; }}
}}
</script>
</body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def main():
    print(f"=== 云台相机媒体代理 ===")
    print(f"配置读取: config.yaml → gimbal_camera")
    print(f"相机地址: {CAMERA_HOST}:{CAMERA_PORT}")
    if WIFI_SSID:
        print(f"WiFi名称: {WIFI_SSID}")
    print()

    # 启动前检查连通性
    try:
        url = f"{CAMERA_BASE}/api/v1/getdirectories?media_type=0"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            print(f"云台连通: {'✅ 正常' if data.get('success') else '❌ 失败'}")
            if not data.get('success'):
                print(f"  详情: {json.dumps(data, ensure_ascii=False)[:200]}")
    except Exception as e:
        print(f"❌ 云台不可达: {e}")
        print()
        print("请确认:")
        print(f"  1. RK3568 已连上 4G 模块 WiFi")
        print(f"  2. 能 ping 通 {CAMERA_HOST}")
        print("  3. 云台相机已上电(需约30秒启动)")
        print(f"  提示: sudo nmcli device wifi connect \"{WIFI_SSID or 'WiFi名'}\" password \"密码\" -- ipv4.never-default yes")

    print()
    print(f"代理启动: http://0.0.0.0:{PROXY_PORT}")
    print(f"浏览器打开: http://100.84.131.95:{PROXY_PORT}")
    print(f"Ctrl+C 退出\n")

    server = HTTPServer(("0.0.0.0", PROXY_PORT), CameraProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")
        server.shutdown()


if __name__ == "__main__":
    main()