path = r"C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app\modules\web_ui.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old_reboot = '''
                elif path == "/api/reboot":
                    ui._app_state.log_event("webui", "warn", "\u7528\u6237\u8bf7\u6c42\u91cd\u542f\u7ec8\u7aef")
                    self._json({"ok": True, "msg": "\u7ec8\u7aef\u5373\u5c06\u91cd\u542f\uff0c\u8bf7\u7a0d\u5019\u91cd\u65b0\u8fde\u63a5..."})
                    def _do_reboot():
                        import os, time
                        time.sleep(2)
                        os.system("systemctl reboot -i")
                    threading.Thread(target=_do_reboot, daemon=True).start()'''
c = c.replace(old_reboot, "")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: /api/reboot removed")
