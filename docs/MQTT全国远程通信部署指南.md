# MQTT 全国远程通信部署指南

> ANMK8639 机库控制系统 — 基于 Tailscale + Mosquitto 的零成本全国 MQTT 通信方案

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

## 二、硬件 & 网络要求

| 设备 | 要求 |
|------|------|
| RK3568 | 能上网即可（4G / WiFi / 有线） |
| 路由器 | 无需任何配置 |
| 调度系统 | Windows/Linux/macOS，能上网 |

---

## 三、Tailscale 账号注册

> 在 **PC 浏览器** 操作，一次性。

```
1. 打开 https://login.tailscale.com
2. 点击 "Sign up with GitHub"（或 Google / Microsoft）
3. 授权登录 → 自动创建网络
4. 看到控制台面板 → 注册完成
```

免费版：3 用户、最多 100 台设备，无需绑卡。

---

## 四、RK3568 部署步骤

### 4.1 安装 Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### 4.2 加入网络

```bash
sudo tailscale up
```

终端会输出一个 URL，复制到 PC 浏览器打开，点击 **Confirm**。

### 4.3 验证

```bash
tailscale status
# 示例输出:
# 100.64.0.3  kickpi   linux  active
```

### 4.4 安装 Mosquitto

```bash
sudo apt install mosquitto mosquitto-clients -y
```

### 4.5 安全配置

```bash
# 创建密码文件
sudo mosquitto_passwd -c /etc/mosquitto/passwd hangar
# 输入密码两次

# 配置监听 + 认证
sudo tee /etc/mosquitto/conf.d/hangar.conf << 'EOF'
listener 1883 0.0.0.0
password_file /etc/mosquitto/passwd
allow_anonymous false
EOF

# 重启生效
sudo systemctl restart mosquitto
```

### 4.6 修改 config.yaml

```yaml
mqtt:
  enabled: true
  broker: "127.0.0.1"       # Hangar 连本机 Mosquitto
  port: 1883
  username: "hangar"
  password: "你的密码"
  topic_prefix: "hangar/"
```

### 4.7 重启服务

```bash
sudo systemctl restart hangar
hangar check   # 确认运行
```

---

## 五、调度系统部署

### 5.1 安装 Tailscale

| 系统 | 方法 |
|------|------|
| Windows | https://tailscale.com/download → 下载安装包 |
| Linux | `curl -fsSL https://tailscale.com/install.sh \| sh` |
| macOS | App Store 搜 Tailscale |

### 5.2 加入同一网络

```bash
sudo tailscale up
# 浏览器登录 同一个 Tailscale 账号 → Confirm
```

### 5.3 获取虚拟 IP

```bash
tailscale status
# 记下本机 IP，如 100.64.0.2
```

### 5.4 查看 RK3568 IP

```bash
tailscale status | grep kickpi
# 100.64.0.3  kickpi  linux  active
```

---

## 六、MQTT 连接配置（调度系统）

| 参数 | 值 |
|------|----|
| Broker 地址 | `100.64.0.3`（RK3568 的 Tailscale IP） |
| 端口 | `1883` |
| 用户名 | `hangar` |
| 密码 | 步骤 4.5 设的密码 |
| Topic 前缀 | `hangar/` |

### 测试连通

```bash
# 在调度系统上
mosquitto_sub -h 100.64.0.3 -p 1883 -u hangar -P 你的密码 -t "hangar/#" -v
```

---

## 七、MQTT Topic 说明

| Topic | 方向 | 说明 |
|-------|------|------|
| `hangar/telemetry` | RK3568 → 调度 | 遥测数据流 |
| `hangar/alarm` | RK3568 → 调度 | 告警信息 |
| `hangar/status` | RK3568 → 调度 | 系统状态 |
| `hangar/event` | RK3568 → 调度 | 事件日志 |
| `hangar/cmd` | 调度 → RK3568 | 远程指令 |
| `hangar/config` | 调度 → RK3568 | 远程配置 |

---

## 八、常见问题

| 问题 | 解决 |
|------|------|
| 连不上 | `ping 100.64.x.x` 测试 Tailscale |
| MQTT 拒绝 | 检查 mosquitto 状态 `systemctl status mosquitto` |
| 忘记密码 | `sudo mosquitto_passwd /etc/mosquitto/passwd hangar` 重设 |
| 设备离线 | `tailscale status` 查看在线状态 |
| 4G 路由器 | 无需任何配置，能上网就行 |
| Tailscale 到期 | 免费版永久，不会到期 |

---

## 九、setup.sh 自动化（规划中）

后续将在 `setup.sh` 中添加自动安装步骤：

```bash
# 未来一键安装将包含:
# [X/Y] Install Mosquitto + Tailscale
# [X/Y] Configure MQTT Broker
```

---

> 📌 部署前请确认 RK3568 能访问互联网。4G 路由器和有线网络均可。
