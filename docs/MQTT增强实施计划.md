# MQTT 增强实施计划

> ANMK8639 机库控制系统 — LWT遗嘱 / QoS分级 / 断联缓存 / Broker监控  
> 状态: 📋 待审核 | 创建: 2026-06-29

---

## 一、现状分析

| 项目 | 状态 | 详情 |
|------|------|------|
| LWT 遗嘱消息 | ⚠️ 已有但不完善 | `mqtt_client.py:50` 已有基础遗嘱，但发到 `hangar/alarm`，调度需额外解析 |
| 遥测 QoS=0 | ✅ 已完成 | `mqtt_client.py:91` `publish_telemetry` 用 qos=0 |
| 告警 QoS | ⚠️ 需升级 | 当前 qos=1，应改为 qos=2 确保必定送达且不重复 |
| 断联消息缓存 | ❌ 未实现 | Mosquitto 默认不存离线消息 |
| Broker 健康监控 | ❌ 未实现 | WebUI 看不到 Mosquitto 是否活着 |
| QoS 配置文件化 | ❌ 未实现 | QoS 硬编码在各 publish 调用中 |

---

## 二、改动清单

### 2.1 告警 QoS 1 → 2

**文件**: `modules/mqtt_client.py`  
**改动**: 1 处

```diff
- self._client.publish("hangar/alarm", msg, qos=1)
+ self._client.publish("hangar/alarm", msg, qos=2)
```

> 原因: 告警是不可丢失的关键信息。QoS 2 保证"恰好一次送达"。

---

### 2.2 LWT 遗嘱消息优化

**文件**: `modules/mqtt_client.py`  
**改动**: 1 处，加 2 行

当前遗嘱只发 `hangar/alarm`，补充发 `hangar/status` 设成 "offline"：

```diff
  will_msg = build_message("alarm", {
      "level": "ERROR", "code": "DEVICE_OFFLINE", "msg": "RK3568 disconnected"
  })
  self._client.will_set("hangar/alarm", will_msg, qos=1, retain=False)
+ # 同时声明设备离线状态
+ offline_status = build_message("status", {"online": False})
+ self._client.will_set("hangar/status", offline_status, qos=1, retain=True)
```

> `retain=True` 是关键：新上线的调度系统立刻就能看到"离线"，不用等下次心跳超时。

---

### 2.3 Mosquitto 持久化 & 离线缓存

**新增文件**: `deploy/mosquitto-hangar.conf`

```conf
# 监听所有网口（本机 + Tailscale 虚拟网卡）
listener 1883 0.0.0.0

# 开启密码认证
password_file /etc/mosquitto/passwd
allow_anonymous false

# 持久化：重启不丢消息
persistence true
persistence_location /var/lib/mosquitto/

# 离线队列：断联期间缓存消息
max_queued_messages 1000

# 告警消息保留（retained）
max_inflight_messages 100
```

**setup.sh** 新增步骤（约 6 行 bash）：

```bash
echo "[X/Y] Mosquitto config..."
sudo cp "${SCRIPT_DIR}/deploy/mosquitto-hangar.conf" /etc/mosquitto/conf.d/hangar.conf
sudo systemctl restart mosquitto
```

---

### 2.4 Broker 健康监控

**文件**: `core/app_state.py`  
**改动**: ~10 行

在 `_get_system_info()` 函数末尾，检查 Mosquitto 进程：

```python
def _get_system_info():
    # ... 现有 CPU/RAM/Disk ...
    
    # Mosquitto 进程检测
    info["mosquitto"] = False
    try:
        for line in open("/proc/net/tcp", "r"):
            if "00001D8B" in line:  # 端口 1883 = 0x1D8B（小端）
                info["mosquitto"] = True
                break
    except:
        pass
    return info
```

> 通过检查 `/proc/net/tcp` 中 1883 端口是否被监听来判断。比调 `systemctl` 更轻量。

---

### 2.5 WebUI 系统资源卡片

**文件**: `modules/dashboard.html`  
**改动**: 系统资源卡片加 1 行

在 CPU/内存/磁盘 下方加：

```js
addInfo(sys, "Mosquitto", d.system.mosquitto ? "✅ 运行" : "❌ 停止");
```

---

### 2.6 config.yaml 更新

**文件**: `config.yaml`  
**改动**: mqtt 段更新注释

```yaml
mqtt:
  enabled: true                     # ← 上线后改为 true
  broker: "127.0.0.1"               # ← Hangar 连本机 Mosquitto
  port: 1883
  client_id: "hangar_001"
  username: "hangar"                # ← Mosquitto 用户
  password: "你的密码"               # ← 步骤 4.5 设的
  keepalive: 30
  status_interval: 5
  topic_prefix: "hangar/"
  qos: 1                            # 默认 QoS
  reconnect_min: 2
  reconnect_max: 60
```

> 注意: `broker` 填 `127.0.0.1` 是因为 Hangar 连的是**本机** Mosquitto。调度系统连的是 **Tailscale 虚拟 IP**。

---

## 三、实施顺序

| 步骤 | 文件 | 内容 | 风险 |
|------|------|------|------|
| 1 | `modules/mqtt_client.py` | 告警 QoS 1→2 + LWT 优化 | 低，不影响现有逻辑 |
| 2 | `core/app_state.py` | Broker 进程检测 | 低，纯新增 |
| 3 | `modules/dashboard.html` | 系统卡片加 Mosquitto 状态行 | 低 |
| 4 | `deploy/mosquitto-hangar.conf` | 新增 Mosquitto 配置 | 低，不覆盖原配置 |
| 5 | `config.yaml` | 更新 mqtt 段 | 低 |
| 6 | `setup.sh` | 新增 Mosquitto 配置步骤 | 中，需测试 |
| 7 | `docs/MQTT全国远程通信部署指南.md` | 补充 LWT/QoS 说明 | 零风险 |

---

## 四、不改动清单（已 OK 的部分）

以下内容当前代码已正确，不在此次计划中：

| 项目 | 说明 |
|------|------|
| `publish_telemetry` qos=0 | 遥测丢几帧无所谓 ✅ |
| `will_set("hangar/alarm", ...)` | 已有基础遗嘱 ✅ |
| `_on_connect` 重新订阅 | 断线重连后自动订阅 ✅ |
| `publish_status` | 全量状态上报已有 ✅ |

---

## 五、预期效果

运行后，调度系统可以：

| 能力 | 实现方式 |
|------|----------|
| 实时知道设备在线/离线 | LWT 遗嘱 → `hangar/status`（retain） |
| 告警绝不丢失 | QoS 2 + 持久化 |
| 断联期间告警不丢 | Mosquitto 缓存队列（1000 条） |
| 一眼看到 Broker 状态 | WebUI 系统资源卡片 |

---

> 📌 等待审核后开始实施。所有改动均在 PC 本地，不直接动 RK3568。
