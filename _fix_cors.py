import sys

path = r"C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app\modules\web_ui.py"
with open(path, "r", encoding="utf-8-sig") as f:
    content = f.read()

changes = 0

# 1. Fix _write_go2rtc_config to add api origin CORS header
old_write = '''                config_yaml = f"streams:\\n  camera: {rtsp_url}\\n"'''
new_write = '''                config_yaml = f"api:\\n  origin: \\"*\\"\\nstreams:\\n  camera: {rtsp_url}\\n"'''

if old_write in content:
    content = content.replace(old_write, new_write)
    sys.stdout.write("1. Added CORS origin to go2rtc config writer\n")
    changes += 1
else:
    sys.stdout.write("1. Old write pattern not found\n")

# 2. Change local_mse URL to use window.location.hostname in frontend
# But this needs to be done in dashboard.html, not web_ui.py
# In web_ui.py, change local_mse to return the actual host IP for direct go2rtc access
# Since the browser connects to the same host as the web UI, use that hostname

# Actually, let's fix _get_camera_urls to use the request's host for the MSE URL
old_mse = '"local_mse": "/api/camera/mse"'
new_mse = '"local_mse": "http://" + (self.headers.get("Host", "127.0.0.1:8088").split(":")[0] if self.headers.get("Host") else local_ip) + ":" + str(port) + "/api/stream?src=camera"'

if old_mse in content:
    content = content.replace(old_mse, new_mse)
    sys.stdout.write("2. Changed local_mse to use request host for direct go2rtc access\n")
    changes += 1
else:
    sys.stdout.write("2. Old mse pattern not found\n")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

sys.stdout.write("Done. Changes: %d\n" % changes)
sys.stdout.flush()
