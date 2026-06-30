import re

path = r"C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app\modules\web_ui.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Change urllib.request.quote to urllib.parse.quote 
# Fix 2: Also update systemd go2rtc config and restart service
old_block = '''            def _ensure_go2rtc(self):
                """Ensure go2rtc is running; detect systemd or start if not."""
                import os, socket, urllib.request
                # 1) Check if go2rtc is already listening on port 1984 (systemd or otherwise)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                port_open = sock.connect_ex(("127.0.0.1", ui._go2rtc_port)) == 0
                sock.close()
                if port_open:
                    # go2rtc already running — update stream config via API
                    rtsp_url = self._get_rtsp_url()
                    if not rtsp_url:
                        return {"ok": False, "error": "RTSP URL not configured"}
                    try:
                        api_url = "http://127.0.0.1:" + str(ui._go2rtc_port) + "/api/streams?src=camera&dst=" + urllib.request.quote(rtsp_url, safe="")
                        req = urllib.request.Request(api_url, method="PUT")
                        urllib.request.urlopen(req, timeout=5)
                        logger.info("[go2rtc] stream camera updated via API")
                    except Exception as e:
                        logger.warning("[go2rtc] API stream update failed (may already exist): %s", e)
                    ui._go2rtc_proc = "external"  # don"t kill it on stop
                    return {"ok": True, "msg": "go2rtc running (external)", "urls": self._get_camera_urls()}'''

new_block = '''            def _ensure_go2rtc(self):
                """Ensure go2rtc is running; detect systemd or start if not."""
                import os, socket, urllib.parse
                # 1) Check if go2rtc is already listening on port 1984 (systemd or otherwise)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                port_open = sock.connect_ex(("127.0.0.1", ui._go2rtc_port)) == 0
                sock.close()
                if port_open:
                    # go2rtc already running via systemd
                    rtsp_url = self._get_rtsp_url()
                    if not rtsp_url:
                        return {"ok": False, "error": "RTSP URL not configured"}
                    # Update systemd-managed config and restart go2rtc
                    systemd_config = "/etc/hangar/go2rtc.yaml"
                    try:
                        config_yaml = "streams:\\n  camera: " + rtsp_url + "\\n"
                        with open(systemd_config, "w") as f:
                            f.write(config_yaml)
                        subprocess.run(["systemctl", "restart", "go2rtc"], timeout=15)
                        time.sleep(3)
                        logger.info("[go2rtc] systemd config updated + restarted")
                    except Exception as e:
                        logger.warning("[go2rtc] systemd restart failed, trying API: %s", e)
                        # Fallback: update via go2rtc API
                        try:
                            api_url = "http://127.0.0.1:" + str(ui._go2rtc_port) + "/api/streams?src=camera&dst=" + urllib.parse.quote(rtsp_url, safe="")
                            req = urllib.request.Request(api_url, method="PUT")
                            urllib.request.urlopen(req, timeout=5)
                            logger.info("[go2rtc] stream camera updated via API")
                        except Exception as e2:
                            logger.warning("[go2rtc] API also failed: %s", e2)
                    ui._go2rtc_proc = "external"  # don"t kill it on stop
                    return {"ok": True, "msg": "go2rtc running", "urls": self._get_camera_urls()}'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Replaced _ensure_go2rtc")
else:
    print("WARNING: old block not found")
    # Try to find what's there
    idx = content.find("def _ensure_go2rtc(self):")
    if idx >= 0:
        print(f"Found at position {idx}")
        print(repr(content[idx:idx+200]))
    else:
        print("Function not found at all!")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
