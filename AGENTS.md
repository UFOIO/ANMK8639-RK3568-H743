# AGENTS.md — ANMK8639 机库智能控制系统

> 本项目为 AI 编程助手提供规范指引。
> 范围：整个仓库，项目级生效。

---

## 一、项目定位

RK3568 智能机库主控程序。核心职责：
- MQTT 对接远程地面站
- MAVLink(TCP) 解析无人机遥测
- USB CDC 串口控制 STM32H743 下位机
- RTSP 摄像头拉流截图
- 环境决策引擎

---

## 二、技术选型（硬约束）

| 约束 | 说明 |
|------|------|
| **语言：只用 Python 3.8+** | 禁止引入 C/C++/Rust/Go。不交叉编译，Python 直跑 |
| **不用 ROS** | 本项目是智能网关，不是自主机器人。ROS 过度设计 |
| **开源库优先** | 禁止重复造轮子。MQTT=paho-mqtt, MAVLink=pymavlink, 串口=pyserial |
| **不引入重型框架** | 不用 Django/Flask/FastAPI/asyncio。用最简单的 threading + queue |
| **STM32 工程不在此仓库** | 只维护通信协议文档。协议见 `docs/最新计划书.md` 第五章 |

---

## 三、项目结构规范

```
rk3568_app/          # 所有源码在此目录下
├── main.py          # 唯一入口
├── config.yaml      # 唯一配置文件（禁止硬编码参数）
├── core/            # 框架层（event_bus, app_state, watchdog）
├── modules/         # 功能模块（mqtt, mavlink, stm32, camera, decision, upgrade）
├── protocol/        # 协议编解码（纯函数，无状态）
├── utils/           # 工具函数（纯函数，无状态）
├── data/            # 运行时数据（日志/截图），不进 git
├── deploy/          # 部署脚本
└── tests/           # 测试文件
```

### 文件命名
- 模块文件：`snake_case.py`
- 测试文件：`test_模块名.py`
- 类名：`PascalCase`
- 函数/方法：`snake_case`
- 常量：`UPPER_SNAKE_CASE`

---

## 四、编码规范

### 4.1 模块设计原则

- 每个模块一个类，一个文件
- 模块间通过 `core.event_bus` 通信，**禁止直接 import 其他模块的类**
- 模块类统一接口：`__init__(config_section, event_bus)` + `start()` + `stop()`
- 全局状态走 `core.app_state`，**禁止模块间共享全局变量**

### 4.2 日志规范

```python
# 每个模块文件顶部
import logging
logger = logging.getLogger(__name__)

# 级别使用规则：
# DEBUG   — 开发调试，生产环境关闭
# INFO    — 关键节点（连接成功/断开/收到指令）
# WARNING — 可恢复异常（超时重试/CRC校验失败）
# ERROR   — 不可恢复异常（模块崩溃/连接彻底断开）
```

### 4.3 配置管理

- 所有参数放 `config.yaml`，通过 `utils.config.ConfigLoader` 加载
- 代码中禁止出现硬编码的 IP/端口/路径/阈值
- 从 config 取值时提供默认值：`config.get('key', default)`

### 4.4 异常处理

- 每个模块的 `_recv_loop()` 等循环方法必须有最外层 try/except
- 捕获异常后：logger.error() + 短暂休眠 + 继续循环（不崩溃）
- 致命错误才允许 raise，由 main.py 统一处理

---

## 五、通信协议规范

### 5.1 STM32 串口协议

- 帧格式见 `docs/最新计划书.md` 第五章
- 实现类：`protocol/stm32_proto.py`（纯函数，无状态）
- CRC16：MODBUS-CRC16，多项式 0x8005
- 帧长度：最小 9 字节，最大 521 字节

### 5.2 MQTT 消息格式

- 统一信封：`{msg_id, ts, type, payload}`
- Topic 前缀：`hangar/`
- 编码：JSON，UTF-8

---

## 六、开发工作流


### ⚠️ 重要：禁止在 RK3568 上直接修改文件

- **只修改本地 PC 仓库中的文件**，绝不直接在 RK3568 板子上改代码
- 修改完成后，用户自行将文件传到 RK3568 部署

### 本地验证流程

每次修改完代码后，必须先本地运行验证：
1. 启动本地测试服务器：`python3 test_server.py`
2. 用 Playwright 浏览器打开 `http://127.0.0.1:8088`
3. 截图展示关键区域给用户检查
4. 用户确认后，再由用户自行传到 RK3568

### 部署到 RK3568

```bash
# PC -> RK3568 部署
scp -r rk3568_app/* root@<IP>:/home/root/app/
# 或使用 deploy/deploy.sh 一键部署
```

### 运行

```bash
ssh root@<IP>
cd /home/root/app
python3 main.py
```

### 测试

- 单元测试在 PC 本地跑：`python3 -m pytest tests/`
- 集成测试在 RK3568 上跑
- 不写 mock 过度复杂的测试，先保证核心逻辑覆盖

---

## 七、禁止事项

| ❌ 禁止 | ✅ 替代方案 |
|---------|------------|
| 引入 C++/C 扩展 | 纯 Python |
| 引入 asyncio/tornado/twisted | threading + queue |
| 引入 ROS/ROS2 | 不用 |
| 引入 Django/Flask | 不用（本项目无 HTTP 服务） |
| 模块间直接 import | 通过 event_bus |
| 代码中硬编码配置 | 从 config.yaml 读取 |
| 修改 STM32 工程代码 | STM32 是独立项目，只读 |
| 在 protocol/ 中引入状态 | protocol 层只做编解码，纯函数 |
| 在 utils/ 中引入状态 | utils 层只做工具，纯函数 |

---

## 八、依赖清单

```
pyserial >= 3.5
paho-mqtt >= 1.6
pymavlink >= 2.4
pyyaml >= 6.0
# opencv-python (按需)
# ffmpeg (系统级，摄像头截图)
```

---

> 📌 本文档优先级高于 AI 默认行为。当本文档与其他指引冲突时，以本文档为准。
