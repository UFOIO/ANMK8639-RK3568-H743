path = r"C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app\modules\dashboard.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Remove [重启终端] button
old_btns = '<button class="btn btn-red" onclick="restartService()">[\u91cd\u542f\u670d\u52a1]</button> <button class="btn btn-red" onclick="rebootDevice()">[\u91cd\u542f\u7ec8\u7aef]</button>'
new_btns = '<button class="btn btn-red" onclick="restartService()">[\u91cd\u542f\u670d\u52a1]</button>'
c = c.replace(old_btns, new_btns, 1)

# 2. Remove rebootDevice function
old_reboot = '''
function rebootDevice() {
  if (!confirm("\u786e\u5b9a\u91cd\u542f\u7ec8\u7aef\uff08RK3568\u6574\u673a\u91cd\u542f\uff09\uff1f\\n\u8fd9\u5c06\u65ad\u5f00\u6240\u6709\u8fde\u63a5\uff0c\u7ea6 30-60 \u79d2\u540e\u6062\u590d\u3002")) return;
  fetch("/api/reboot", {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"})
    .then(function(r) { return r.json(); })
    .then(function(res) { showToast(res.msg || "\u7ec8\u7aef\u5373\u5c06\u91cd\u542f...", "info"); })
    .catch(function(e) { showToast("\u9519\u8bef: " + e.message, "error"); });
}'''
c = c.replace(old_reboot, "", 1)

# 3. Update saveSection toast: remind about restart for connection changes
old_toast = 'showToast("\u914d\u7f6e\u5df2\u4fdd\u5b58\u5e76\u81ea\u52a8\u91cd\u8f7d\u751f\u6548", "info");'
new_toast = 'showToast("\u914d\u7f6e\u5df2\u4fdd\u5b58\uff0c\u9608\u503c/\u95f4\u9694\u5df2\u81ea\u52a8\u751f\u6548\u3002\u82e5\u4fee\u6539\u4e86IP/\u7aef\u53e3/\u4e32\u53e3\u8bbe\u5907\uff0c\u8bf7\u70b9[\u91cd\u542f\u670d\u52a1]", "info");'
c = c.replace(old_toast, new_toast, 1)

# Also update saveConfig toast
old_toast2 = 'showToast("\u914d\u7f6e\u5df2\u4fdd\u5b58\u5e76\u81ea\u52a8\u91cd\u8f7d\u751f\u6548", "info");'
c = c.replace(old_toast2, new_toast, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: reboot button removed, toast updated")
