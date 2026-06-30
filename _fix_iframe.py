import sys

# Fix dashboard.html - replace cam-player content with go2rtc iframe
path_html = r"C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app\modules\dashboard.html"
with open(path_html, "r", encoding="utf-8-sig") as f:
    content = f.read()

# The auto-start flow is too complex and not working. Simplify:
# 1. Replace cam-player content: use iframe to go2rtc instead of img/video/loading
# 2. Replace the cam-btns section
# 3. Simplify the JS

old_player = """        <div class="cam-player" id="cam-player">
          <div class="cam-placeholder" id="cam-placeholder">点击「启动预览」查看画面</div>
          <img id="cam-preview-img" src="" style="display:none" onerror="_onCamImgError()">
          <video id="cam-video-el" autoplay muted playsinline style="display:none" onplaying="_onCamPlaying()" onerror="_onCamError()"></video>
          <div class="cam-loading-overlay" id="cam-loading">
            <div style="text-align:center">
              <div class="spinner"></div>
              <div style="color:var(--dim);font-size:12px;margin-top:10px" id="cam-loading-text">正在连接摄像头...</div>
            </div>
          </div>
          <div class="cam-error-overlay" id="cam-error">
            <div>
              <div class="cam-error-msg" id="cam-error-msg">无法连接摄像头</div>
              <div style="font-size:11px;color:var(--dim);margin-top:6px">请检查摄像头或切换模式</div>
            </div>
          </div>
        </div>
        <div class="cam-btns" style="margin-top:8px">
          <button class="btn btn-green btn-sm" id="cam-start-btn" onclick="startCameraPreview()">启动预览</button>
          <button class="btn btn-red btn-sm" id="cam-stop-btn" onclick="stopCameraPreview()" style="display:none">关闭预览</button>
        </div>
        <div style="margin-top:4px;font-size:11px;color:var(--dim)">
          模式：<select id="cam-mode-select" onchange="switchCamMode()" style="background:var(--bg);color:var(--text);border:1px solid var(--border);font-size:11px">
            <option value="mjpeg">MJPEG</option>
            <option value="mse" selected>MSE (HTML5)</option>
            <option value="webrtc">WebRTC</option>
          </select>
          <span style="margin-left:8px">|</span>
          <span id="cam-fps" style="color:var(--green)"></span>
        </div>"""

new_player = """        <div class="cam-player" id="cam-player">
          <iframe id="cam-iframe" src="" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0" allow="autoplay"></iframe>
          <div class="cam-placeholder" id="cam-placeholder" style="display:none"></div>
          <div class="cam-loading-overlay" id="cam-loading" style="display:flex">
            <div style="text-align:center">
              <div class="spinner"></div>
              <div style="color:var(--dim);font-size:12px;margin-top:10px" id="cam-loading-text">正在加载摄像头...</div>
            </div>
          </div>
        </div>"""

if old_player in content:
    content = content.replace(old_player, new_player)
    sys.stdout.write("Replaced cam-player with go2rtc iframe\n")
else:
    sys.stdout.write("old_player not found\n")

# Fix relay side too - same iframe approach
old_relay = """          <img id="relay-preview-img" src="" style="display:none" onerror="this.style.display='none';var ph=document.getElementById('relay-placeholder');if(ph)ph.style.display='flex'">
          <video id="relay-video-el" autoplay muted playsinline style="display:none" onplaying="_onRelayPlaying()" onerror="_onRelayError()"></video>
          <div class="cam-loading-overlay" id="relay-loading">
            <div style="text-align:center">
              <div class="spinner"></div>
              <div style="color:var(--dim);font-size:12px;margin-top:10px" id="relay-loading-text">正在连接...</div>
            </div>
          </div>
          <div class="cam-error-overlay" id="relay-error" style="display:none">
            <div style="text-align:center">
              <div class="cam-error-msg" id="relay-error-msg">无法连接</div>
              <div style="font-size:11px;color:var(--dim);margin-top:6px">请检查代理状态或网络</div>
            </div>
          </div>"""

new_relay = """          <iframe id="relay-preview-img" src="" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;display:none" allow="autoplay"></iframe>
          <div class="cam-loading-overlay" id="relay-loading">
            <div style="text-align:center">
              <div class="spinner"></div>
              <div style="color:var(--dim);font-size:12px;margin-top:10px" id="relay-loading-text">正在连接...</div>
            </div>
          </div>"""

if old_relay in content:
    content = content.replace(old_relay, new_relay)
    sys.stdout.write("Replaced relay player with iframe\n")
else:
    sys.stdout.write("old_relay not found\n")

# Add initGo2rtc function and simplify JS
# Find the autoStartCamera function and simplify
old_auto = """function autoStartCamera() {
    fetch("/api/camera/urls").then(function(r){return r.json()}).then(function(urls){
        _go2rtcUrls = urls;
        if (urls && urls.running) {
            _camActive = true;
            var btnStart = document.getElementById("cam-start-btn");
            var btnStop = document.getElementById("cam-stop-btn");
            var statusEl = document.getElementById("cam-status");
            var phEl = document.getElementById("cam-placeholder");
            if (btnStart) btnStart.style.display = "none";
            if (btnStop) btnStop.style.display = "";
            if (statusEl) { statusEl.textContent = "LIVE"; statusEl.style.color = "var(--green)"; }
            if (phEl) phEl.style.display = "none";
            var lt = document.getElementById("cam-loading-text");
            if (lt) lt.textContent = "Loading stream...";
            var loadEl = document.getElementById("cam-loading");
            if (loadEl) loadEl.style.display = "flex";
            switchCamMode(true);
        }
    }).catch(function(){});
}"""

new_auto = """function autoStartCamera() {
    // Use go2rtc WebRTC iframe - it handles the video natively
    var host = window.location.hostname;
    var port = 1984;
    var go2rtcUrl = "http://" + host + ":" + port + "/?src=camera";
    var iframe = document.getElementById("cam-iframe");
    if (iframe) {
        iframe.src = go2rtcUrl + "&autoplay=1";
        iframe.onload = function() {
            var loadEl = document.getElementById("cam-loading");
            if (loadEl) loadEl.style.display = "none";
            var statusEl = document.getElementById("cam-status");
            if (statusEl) { statusEl.textContent = "LIVE"; statusEl.style.color = "var(--green)"; }
        };
    }
}"""

if old_auto in content:
    content = content.replace(old_auto, new_auto)
    sys.stdout.write("Simplified autoStartCamera to use go2rtc iframe\n")
else:
    sys.stdout.write("old_auto not found\n")

with open(path_html, "w", encoding="utf-8") as f:
    f.write(content)
sys.stdout.write("Dashboard HTML updated\n")
sys.stdout.flush()
