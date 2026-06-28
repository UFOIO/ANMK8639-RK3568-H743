#!/usr/bin/env python3
"""
MAVLink 飞控 USB 直连测试工具
用法: python3 mavlink_test.py
会自动列出可用串口，让你选择飞控端口
"""
import os
import sys
import time
import glob

# 检查 pymavlink
try:
    from pymavlink import mavutil
except ImportError:
    print("请先安装 pymavlink: pip install pymavlink")
    sys.exit(1)

# ====== 1. 扫描可用串口 ======
ports = []
for pattern in ["/dev/ttyACM*", "/dev/ttyUSB*", "/dev/ttyS*"]:
    ports.extend(glob.glob(pattern))

if not ports:
    print("未发现串口设备，请确认飞控已通过 USB 插入")
    print("当前 /dev/tty* 列表：")
    for p in sorted(glob.glob("/dev/tty*")):
        print(" ", p)
    sys.exit(1)

print("\n=== 可用串口 ===")
for i, p in enumerate(sorted(ports)):
    print(f"  [{i}] {p}")

print(f"  [q] 退出")

choice = input("\n选择飞控端口: ").strip()
if choice.lower() == "q":
    sys.exit(0)

try:
    idx = int(choice)
    port = sorted(ports)[idx]
except (ValueError, IndexError):
    print("无效选择")
    sys.exit(1)

baud = input("波特率 (默认 115200): ").strip()
baud = int(baud) if baud else 115200

print(f"\n连接: {port} @ {baud} ...")

# ====== 2. 连接飞控 ======
try:
    mav = mavutil.mavlink_connection(port, baud=baud)
except Exception as e:
    print(f"连接失败: {e}")
    sys.exit(1)

# ====== 3. 飞行模式映射 ======
MODE_MAP = {
    0:  "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4:  "GUIDED",    5: "LOITER", 6: "RTL", 7: "CIRCLE",
    9:  "LAND",      11: "DRIFT", 13: "SPORT", 14: "FLIP",
    15: "AUTOTUNE",  16: "POSHOLD", 17: "BRAKE",
    21: "SMART_RTL",
}

def mode_name(cm):
    return MODE_MAP.get(cm, f"MODE_{cm}")

print("\n✅ 已连接，等待 MAVLink 数据... (Ctrl+C 停止)\n")
print("-" * 75)

msg_count = 0
hb_count = 0
last_print = 0

try:
    while True:
        msg = mav.recv_match(blocking=True, timeout=1.0)
        if msg is None:
            continue

        msg_count += 1
        msg_id = msg.get_msgId()

        # HEARTBEAT
        if msg_id == 0:
            hb_count += 1
            fm = mode_name(msg.custom_mode)
            armed = (msg.base_mode & 0x80) != 0
            print(f"🟢 HEARTBEAT #{hb_count}  模式={fm}  武装={'是' if armed else '否'}  "
                  f"类型={msg.type}  自驾仪={msg.autopilot}")

        # GLOBAL_POSITION_INT
        elif msg_id == 33:
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            alt = msg.relative_alt / 1000.0
            hdg = msg.hdg / 100
            print(f"📍 GPS  纬度={lat:.6f}  经度={lon:.6f}  相对高度={alt:.1f}m  航向={hdg}°")

        # GPS_RAW_INT
        elif msg_id == 24:
            print(f"🛰 GPS_RAW  卫星={msg.satellites_visible}  定位类型={msg.fix_type}  "
                  f"HDOP={msg.eph}/100  VDOP={msg.epv}/100")

        # ATTITUDE
        elif msg_id == 30:
            print(f"📐 姿态  Roll={msg.roll:.1f}°  Pitch={msg.pitch:.1f}°  Yaw={msg.yaw:.1f}°")

        # BATTERY_STATUS
        elif msg_id == 147:
            volt = msg.voltages[0] / 1000.0 if msg.voltages and len(msg.voltages) > 0 else 0
            print(f"🔋 电池  剩余={msg.battery_remaining}%  电压={volt:.2f}V")

        # VFR_HUD
        elif msg_id == 74:
            print(f"✈ VFR  空速={msg.airspeed}m/s  地速={msg.groundspeed}m/s  "
                  f"高度={msg.alt}m  油门={msg.throttle}%")

        # SYS_STATUS
        elif msg_id == 1:
            print(f"⚙ SYS_STATUS  电池电压={msg.voltage_battery/1000:.1f}V  "
                  f"电流={msg.current_battery/100:.1f}A  传感器健康=0x{msg.onboard_control_sensors_health:08X}")

        # STATUSTEXT
        elif msg_id == 253:
            text = msg.text.strip() if msg.text else ""
            sev = ["紧急","错误","警告","信息","调试"][min(msg.severity, 4)]
            print(f"💬 飞控消息 [{sev}] {text}")

        # MISSION_CURRENT
        elif msg_id == 42:
            print(f"🎯 航点  当前={msg.seq}")

        # RC_CHANNELS
        elif msg_id == 87:
            print(f"🎮 RC通道  {msg.chan1_raw} {msg.chan2_raw} {msg.chan3_raw} {msg.chan4_raw}  "
                  f"5:{msg.chan5_raw} 6:{msg.chan6_raw} 7:{msg.chan7_raw} 8:{msg.chan8_raw}")

        # 每秒统计
        now = time.time()
        if now - last_print >= 5:
            print(f"\n--- 5秒统计: 总消息={msg_count}  心跳={hb_count} ---\n")
            last_print = now

except KeyboardInterrupt:
    print(f"\n\n停止。共收到 {msg_count} 条消息，{hb_count} 次心跳")
    mav.close()
