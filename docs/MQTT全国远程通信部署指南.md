# MQTT 全国远程通信部署指南

> ANMK8639 机库控制系统 — 基于 Tailscale + Mosquitto 的零成本全国 MQTT 通信方案  
> 最后更新: 2026-06-29

---

## 一、架构总览

```
调度系统(B市)                       RK3568 机库(A市)
     │                                    │
     ├── Tailscale ──── 互联网 ────────────┤
     │  100.64.0.2                    100.64.0.3
     │                                    │
     └── MQTT ──────────────▶  Mosquitto(:1883)
                                          │
                                       Hangar(127.0.0.1)
```

**核心思路**：RK3568 同时跑 Hangar 和 Mosquitto MQTT Broker，通过 Tailscale 组建虚拟局域网，调度系统在全国任意地点直连。

| 优势 | 说明 |
|------|------|
| 零成本 | Tailscale 免费版 100 设备，Mosquitto 开源 |
| 零配置 | 无需公网 IP、端口映射、路由器设置 |
| 低延迟 | Tailscale 优先 P2P 直连，不过中转 |
| 轻量 | Mosquitto 仅占 2-3MB 内存 |
| 兼容 | 4G 路由器 / 物理网线 / WiFi 均可 |

---

## 二、MQTT 增强功能

### 2.1 LWT 遗嘱消息

RK3568 断网/断电时，Mosquitto 自动向调度系统推送：

```
hangar/status → {"type":"status","payload":{"online":false}}  (retain)
hangar/alarm  → {"type":"alarm","payload":{"level":"ERROR","code":"DEVICE_OFFLINE"}}
```

`retain=True` 确保新上线的调度系统立即可见设备离线状态。

### 2.2 QoS 分级

| Topic | QoS | 说明 |
|-------|-----|------|
| `hangar/drone/telemetry` | 0 | 遥测高频，丢几帧无影响 |
| `hangar/status` | 1 | 状态上报，至少送达一次 |
| `hangar/event` | 1 | 事件日志 |
| `hangar/alarm` | **2** | 告警必须送达且不重复 |

### 2.3 断联消息缓存

调度系统离线期间的告警不会丢失：

```conf
# /etc/mosquitto/conf.d/hangar.conf
max_queued_messages 1000   # 最多缓存 1000 条
persistence true           # 重启 Mosquitto 也不丢
```

### 2.4 Broker 健康监控

WebUI 系统资源卡片底部实时显示：

```
Broker ✅  (Mosquitto 运行中)
Broker ❌  (Mosquitto 未运行)
```

通过检查 `/proc/net/tcp` 端口 1883 是否监听来判断。

---

## 三、硬件 & 网络要求

| 设备 | 要求 |
|------|------|
| RK3568 | 能上网即可（4G / WiFi / 有线） |
| 路由器 | 无需任何配置 |
| 调度系统 | Windows/Linux/macOS，能上网 |

---

## 四、Tailscale 账号注册

> 在 **PC 浏览器** 操作，一次性。

```
1. 打开 https://login.tailscale.com
2. 点击 "Sign up with GitHub"（或 Google / Microsoft）
3. 授权登录 → 自动创建网络
4. 看到控制台面板 → 注册完成
```

免费版：3 用户、最多 100 台设备，无需绑卡。

---

## 五、RK3568 部署步骤

### 5.1 安装 Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### 5.2 加入网络

```bash
sudo tailscale up
```

终端会输出一个 URL，复制到 PC 浏览器打开，点击 **Confirm**。

### 5.3 验证

```bash
tailscale status
# 示例输出:
# 100.64.0.3  kickpi   linux  active
```

### 5.4 安装 Mosquitto

```bash
sudo apt install mosquitto mosquitto-clients -y
```

### 5.5 安全配置

```bash
# 创建密码文件
sudo mosquitto_passwd -c /etc/mosquitto/passwd hangar
# 输入密码两次

# 应用 Hangar 配置（持久化 + 离线缓存 + 监听所有网口）
sudo cp /home/kickpi/rk3568_app/deploy/mosquitto-hangar.conf /etc/mosquitto/conf.d/hangar.conf
sudo systemctl restart mosquitto
```

### 5.6 修改 config.yaml

```yaml
mqtt:
  enabled: true                     # ← 改成 true
  broker: "127.0.0.1"               # Hangar 连本机 Mosquitto
  port: 1883
  username: "hangar"
  password: "你的密码"
  topic_prefix: "hangar/"
```

### 5.7 重启服务

```bash
sudo systemctl restart hangar
hangar check   # 确认运行
```

---

## 六、调度系统部署

### 6.1 安装 Tailscale

| 系统 | 方法 |
|------|------|
| Windows | https://tailscale.com/download → 下载安装包 |
| Linux | `curl -fsSL https://tailscale.com/install.sh \| sh` |
| macOS | App Store 搜 Tailscale |

### 6.2 加入同一网络

```bash
sudo tailscale up
# 浏览器登录 同一个 Tailscale 账号 → Confirm
```

### 6.3 获取 RK3568 虚拟 IP

```bash
tailscale status | grep kickpi
# 100.64.0.3  kickpi  linux  active
```

---

## 七、MQTT 连接参数（调度系统）

| 参数 | 值 |
|------|----|
| Broker 地址 | `100.64.0.3`（RK3568 的 Tailscale IP） |
| 端口 | `1883` |
| 用户名 | `hangar` |
| 密码 | 步骤 5.5 设的密码 |
| Topic 前缀 | `hangar/` |

### 测试连通

```bash
# 在调度系统上
mosquitto_sub -h 100.64.0.3 -p 1883 -u hangar -P 你的密码 -t "hangar/#" -v
```

---

## 八、MQTT Topic 说明

| Topic | 方向 | QoS | 说明 |
|-------|------|-----|------|
| `hangar/telemetry` | RK3568 → 调度 | 0 | 遥测数据流 |
| `hangar/alarm` | RK3568 → 调度 | 2 | 告警信息（必达） |
| `hangar/status` | RK3568 → 调度 | 1 | 系统状态 + LWT 遗嘱 |
| `hangar/event` | RK3568 → 调度 | 1 | 事件日志 |
| `hangar/command` | 调度 → RK3568 | 1 | 远程指令 |
| `hangar/config/set` | 调度 → RK3568 | 1 | 远程配置 |

---

## 九、常见问题

| 问题 | 解决 |
|------|------|
| 连不上 | `ping 100.64.x.x` 测试 Tailscale |
| MQTT 拒绝 | 检查 mosquitto 状态 `systemctl status mosquitto` |
| 忘记密码 | `sudo mosquitto_passwd /etc/mosquitto/passwd hangar` 重设 |
| 设备离线 | `tailscale status` 查看在线状态 |
| 4G 路由器 | 无需任何配置，能上网就行 |
| Broker 显示 ❌ | `sudo systemctl restart mosquitto` |
| 告警丢失 | 检查 QoS: hangar/alarm 必须 qos=2 |

---

> 📌 部署前请确认 RK3568 能访问互联网。4G 路由器和有线网络均可。
