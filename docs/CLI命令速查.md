# ANMK8639 Hangar CLI — 命令速查

## 服务控制

```bash
hangar start          # 启动机库控制服务
hangar stop           # 停止机库控制服务  
hangar restart        # 重启服务（全部模块重新初始化，连接参数变更后使用）
hangar reload         # 热重载配置（仅阈值/间隔生效，不断开连接）
```

## 运行监控

```bash
hangar run            # 启动服务并显示实时数据流（Ctrl+C 退出）
hangar logs           # 查看实时数据流（服务需已在运行）
hangar status         # 详细状态：运行时间 + 各模块连接状态 + 系统资源
hangar check          # 快速检查：服务是否运行 + Web 地址
```

## 实时数据流输出格式

```
SYS: load=0.35 ram=558M/3901M uptime=12m
│    │        │             └─ 运行时间
│    │        └─ 内存 已用/总量
│    └─ CPU 负载（1分钟平均 ×100）
└─ 系统信息，1Hz

DATA: MAVLink UP HB:0s | MQTT DOWN MSG:-- | STM32 UP RPT:3s | Camera SNAP:15s
      │       │   │        │    │     │        │    │    │       │      │
      │       │   │        │    │     │        │    │    │       │      └─ 距上次截图
      │       │   │        │    │     │        │    │    └─ 距上次状态上报
      │       │   │        │    │     │        │    └─ STM32 连接状态
      │       │   │        │    │     │        └─ 距上次 MQTT 消息
      │       │   │        │    │     └─ MQTT 连接状态（UP/DOWN）
      │       │   │        │    └─ 距上次心跳（-- 表示从未收到）
      │       │   │        └─ MAVLink 连接状态
      │       │   └─ 模块名
      │       └─ 连接状态汇总，1Hz
      └─ 四模块数据行

TELEM: MODE:STABILIZE | ALT:120.5m | GS:5.2m/s | BAT:85% | SAT:18
       │                │            │           │         └─ GPS 卫星数
       │                │            │           └─ 电池剩余百分比
       │                │            └─ 地速（米/秒）
       │                └─ 相对高度（米）  
       └─ 飞行模式（STABILIZE/LOITER/RTL/AUTO/LAND/...）

MAVLink HB: mode=STABILIZE armed=False
            │              └─ 是否解锁（True/False）
            └─ 飞控当前模式
```

## 配置管理

```bash
hangar config         # 用 nano 编辑配置文件 /etc/hangar/config.yaml
```

## Web 看板

```bash
# 浏览器打开（替换 IP 为实际地址）
http://192.168.2.69:8080
```

## 手动控制（在命令行用 curl）

```bash
# 开门
curl -X POST http://127.0.0.1:8080/api/command -H "Content-Type: application/json" -d '{"cmd":"open_door"}'

# 关门
curl -X POST http://127.0.0.1:8080/api/command -H "Content-Type: application/json" -d '{"cmd":"close_door"}'

# 锁止
curl -X POST http://127.0.0.1:8080/api/command -H "Content-Type: application/json" -d '{"cmd":"lock"}'

# 解锁
curl -X POST http://127.0.0.1:8080/api/command -H "Content-Type: application/json" -d '{"cmd":"unlock"}'

# 手动抓拍
curl -X POST http://127.0.0.1:8080/api/camera/snapshot -H "Content-Type: application/json" -d '{}'

# 健康检查
curl http://127.0.0.1:8080/api/health

# 获取配置
curl http://127.0.0.1:8080/api/config

# 获取事件日志
curl "http://127.0.0.1:8080/api/events?count=50"
```

## 日志路径

| 路径 | 说明 |
|------|------|
| `journalctl -u hangar -f` | systemd 日志，含实时数据流 |
| `/var/log/hangar/` | 应用日志文件（按天轮转） |
| `/var/lib/hangar/` | 截图存档 |
| `/etc/hangar/config.yaml` | 配置文件 |
