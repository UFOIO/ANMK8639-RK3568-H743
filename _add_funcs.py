import sys
sys.stdout.reconfigure(encoding='utf-8')

filepath = r'C:\Users\gjt\Desktop\ANMK8639-RK3568-H743\rk3568_app\modules\dashboard.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# The functions to insert, right before </script>
new_funcs = r'''
function loadConfig() {
    fetch("/api/config")
        .then(function(r) { return r.json(); })
        .then(function(cfg) {
            setVal("cfg-mqtt-enabled", cfg.mqtt && cfg.mqtt.enabled, true);
            setVal("cfg-mqtt-broker", cfg.mqtt && cfg.mqtt.broker);
            setVal("cfg-mqtt-port", cfg.mqtt && cfg.mqtt.port);
            setVal("cfg-mqtt-username", cfg.mqtt && cfg.mqtt.username);
            setVal("cfg-mqtt-password", cfg.mqtt && cfg.mqtt.password);
            setVal("cfg-mqtt-topic_prefix", cfg.mqtt && cfg.mqtt.topic_prefix);
            setVal("cfg-mavlink-connection", cfg.mavlink && cfg.mavlink.connection);
            setVal("cfg-mavlink-host", cfg.mavlink && cfg.mavlink.host);
            setVal("cfg-mavlink-port", cfg.mavlink && cfg.mavlink.port);
            setVal("cfg-mavlink-device", cfg.mavlink && cfg.mavlink.device);
            setVal("cfg-mavlink-baudrate", cfg.mavlink && cfg.mavlink.baudrate);
            setVal("cfg-mavlink-hb_timeout", cfg.mavlink && cfg.mavlink.hb_timeout);
            setVal("cfg-mavlink-telem_rate", cfg.mavlink && cfg.mavlink.telem_rate);
            setVal("cfg-camera-ip", cfg.camera && cfg.camera.ip);
            setVal("cfg-camera-port", cfg.camera && cfg.camera.port);
            setVal("cfg-camera-username", cfg.camera && cfg.camera.username);
            setVal("cfg-camera-password", cfg.camera && cfg.camera.password);
            setVal("cfg-camera-channel", cfg.camera && cfg.camera.channel);
            setVal("cfg-camera-rtsp_url", cfg.camera && cfg.camera.rtsp_url);
            setVal("cfg-stm32-device", cfg.stm32 && cfg.stm32.device);
            setVal("cfg-stm32-baudrate", cfg.stm32 && cfg.stm32.baudrate);
            setVal("cfg-vpn-tailscale_auth_key", cfg.vpn && cfg.vpn.tailscale_auth_key);
            setVal("cfg-auth-enabled", cfg.auth && cfg.auth.enabled, true);
            setVal("cfg-auth-username", cfg.auth && cfg.auth.username);
            setVal("cfg-auth-password", cfg.auth && cfg.auth.password);
            setVal("cfg-auth-session_timeout_min", cfg.auth && cfg.auth.session_timeout_min);
            setVal("cfg-decision-auto_open_on_rtl", cfg.decision && cfg.decision.auto_open_on_rtl, true);
            setVal("cfg-decision-low_battery_threshold", cfg.decision && cfg.decision.low_battery_threshold);
            setVal("cfg-decision-lost_timeout", cfg.decision && cfg.decision.lost_timeout);
            onMavConnChange();
        })
        .catch(function(e) { console.error("loadConfig:", e); });
}

function setVal(id, val, isCheckbox) {
    var el = document.getElementById(id);
    if (!el) return;
    if (isCheckbox) { el.checked = !!val; }
    else if (val !== null && val !== undefined) { el.value = val; }
}

function getVal(id, isCheckbox) {
    var el = document.getElementById(id);
    if (!el) return null;
    if (isCheckbox) return el.checked;
    return el.value;
}

function saveConfig() {
    var data = {
        mqtt: { enabled: getVal("cfg-mqtt-enabled",true), broker: getVal("cfg-mqtt-broker"), port: parseInt(getVal("cfg-mqtt-port"))||1883, username: getVal("cfg-mqtt-username"), password: getVal("cfg-mqtt-password"), topic_prefix: getVal("cfg-mqtt-topic_prefix") },
        mavlink: { connection: getVal("cfg-mavlink-connection"), host: getVal("cfg-mavlink-host"), port: parseInt(getVal("cfg-mavlink-port"))||5760, device: getVal("cfg-mavlink-device"), baudrate: parseInt(getVal("cfg-mavlink-baudrate"))||115200, hb_timeout: parseInt(getVal("cfg-mavlink-hb_timeout"))||5, telem_rate: parseInt(getVal("cfg-mavlink-telem_rate"))||4 },
        camera: { ip: getVal("cfg-camera-ip"), port: parseInt(getVal("cfg-camera-port"))||554, username: getVal("cfg-camera-username"), password: getVal("cfg-camera-password"), channel: parseInt(getVal("cfg-camera-channel"))||1, rtsp_url: getVal("cfg-camera-rtsp_url") },
        stm32: { device: getVal("cfg-stm32-device"), baudrate: parseInt(getVal("cfg-stm32-baudrate"))||115200 },
        vpn: { tailscale_auth_key: getVal("cfg-vpn-tailscale_auth_key") },
        auth: { enabled: getVal("cfg-auth-enabled",true), username: getVal("cfg-auth-username"), password: getVal("cfg-auth-password"), session_timeout_min: parseInt(getVal("cfg-auth-session_timeout_min"))||30 },
        decision: { auto_open_on_rtl: getVal("cfg-decision-auto_open_on_rtl",true), low_battery_threshold: parseInt(getVal("cfg-decision-low_battery_threshold"))||20, lost_timeout: parseInt(getVal("cfg-decision-lost_timeout"))||30 }
    };
    var st = document.getElementById("cfg-save-status");
    if (st) { st.textContent = "..."; st.style.color = "var(--yellow)"; }
    fetch("/api/config", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(data) })
        .then(function(r) { return r.json(); })
        .then(function(res) {
            if (res.ok) { if (st) { st.textContent = res.msg || "OK"; st.style.color = "var(--green)"; } showToast("OK", "success"); }
            else { if (st) { st.textContent = res.error || "FAIL"; st.style.color = "var(--red)"; } showToast(res.error || "FAIL", "error"); }
        })
        .catch(function(e) { if (st) { st.textContent = "err"; st.style.color = "var(--red)"; } showToast("err", "error"); });
}

function saveSection(section) {
    var data = {};
    switch(section) {
        case "mqtt": data.mqtt = { enabled: getVal("cfg-mqtt-enabled",true), broker: getVal("cfg-mqtt-broker"), port: parseInt(getVal("cfg-mqtt-port"))||1883, username: getVal("cfg-mqtt-username"), password: getVal("cfg-mqtt-password"), topic_prefix: getVal("cfg-mqtt-topic_prefix") }; break;
        case "mavlink": data.mavlink = { connection: getVal("cfg-mavlink-connection"), host: getVal("cfg-mavlink-host"), port: parseInt(getVal("cfg-mavlink-port"))||5760, device: getVal("cfg-mavlink-device"), baudrate: parseInt(getVal("cfg-mavlink-baudrate"))||115200, hb_timeout: parseInt(getVal("cfg-mavlink-hb_timeout"))||5, telem_rate: parseInt(getVal("cfg-mavlink-telem_rate"))||4 }; break;
        case "camera": data.camera = { ip: getVal("cfg-camera-ip"), port: parseInt(getVal("cfg-camera-port"))||554, username: getVal("cfg-camera-username"), password: getVal("cfg-camera-password"), channel: parseInt(getVal("cfg-camera-channel"))||1, rtsp_url: getVal("cfg-camera-rtsp_url") }; break;
        case "stm32": data.stm32 = { device: getVal("cfg-stm32-device"), baudrate: parseInt(getVal("cfg-stm32-baudrate"))||115200 }; break;
        case "vpn": data.vpn = { tailscale_auth_key: getVal("cfg-vpn-tailscale_auth_key") }; break;
        case "auth": data.auth = { enabled: getVal("cfg-auth-enabled",true), username: getVal("cfg-auth-username"), password: getVal("cfg-auth-password"), session_timeout_min: parseInt(getVal("cfg-auth-session_timeout_min"))||30 }; break;
        case "decision": data.decision = { auto_open_on_rtl: getVal("cfg-decision-auto_open_on_rtl",true), low_battery_threshold: parseInt(getVal("cfg-decision-low_battery_threshold"))||20, lost_timeout: parseInt(getVal("cfg-decision-lost_timeout"))||30 }; break;
    }
    var st = document.getElementById("cfg-save-" + section);
    if (st) { st.textContent = "..."; st.style.color = "var(--yellow)"; }
    fetch("/api/config", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(data) })
        .then(function(r) { return r.json(); })
        .then(function(res) {
            if (res.ok) { if (st) { st.textContent = "OK"; st.style.color = "var(--green)"; } showToast(section + " OK", "success"); }
            else { if (st) { st.textContent = "FAIL"; st.style.color = "var(--red)"; } showToast(res.error || "FAIL", "error"); }
        })
        .catch(function(e) { if (st) { st.textContent = "err"; st.style.color = "var(--red)"; } showToast("err", "error"); });
}
'''

# Insert functions before </script>
content = content.replace('</script>', new_funcs + '\n</script>')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
print('saveConfig found:', any('function saveConfig' in l for l in lines))
print('saveSection found:', any('function saveSection' in l for l in lines))
print('loadConfig found:', any('function loadConfig' in l for l in lines))
