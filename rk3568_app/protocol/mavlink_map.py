"""
MAVLink 消息 ID 映射表。

列出本项目关心的 MAVLink v2 消息及其关键字段。
"""
from pymavlink.dialects.v20 import ardupilotmega as mavlink

# 消息ID -> (消息名, 关心字段列表)
MESSAGE_MAP = {
    0:  ("HEARTBEAT",           ["type", "autopilot", "base_mode", "custom_mode", "system_status"]),
    1:  ("SYS_STATUS",          ["onboard_control_sensors_present", "onboard_control_sensors_enabled",
                                  "onboard_control_sensors_health", "voltage_battery", "current_battery",
                                  "battery_remaining"]),
    24: ("GPS_RAW_INT",         ["lat", "lon", "alt", "eph", "epv", "vel", "cog", "satellites_visible"]),
    30: ("ATTITUDE",            ["roll", "pitch", "yaw", "rollspeed", "pitchspeed", "yawspeed"]),
    33: ("GLOBAL_POSITION_INT", ["lat", "lon", "alt", "relative_alt", "vx", "vy", "vz", "hdg"]),
    74: ("VFR_HUD",             ["airspeed", "groundspeed", "heading", "throttle", "alt", "climb"]),
    87: ("RC_CHANNELS_RAW",     ["chan1_raw", "chan2_raw", "chan3_raw", "chan4_raw",
                                  "chan5_raw", "chan6_raw", "chan7_raw", "chan8_raw"]),
    105: ("HIGHRES_IMU",        ["xacc", "yacc", "zacc", "xgyro", "ygyro", "zgyro"]),
    147: ("BATTERY_STATUS",     ["voltages", "current_battery", "current_consumed", "battery_remaining",
                                  "temperature"]),
    253: ("STATUSTEXT",         ["severity", "text"]),
}

# 飞行模式映射 (custom_mode 值 -> 模式名)
# ArduPilot 的 custom_mode 值与机架类型相关，这里列常见多旋翼模式
MODE_MAP = {
    0:  "STABILIZE",
    1:  "ACRO",
    2:  "ALT_HOLD",
    3:  "AUTO",
    4:  "GUIDED",
    5:  "LOITER",
    6:  "RTL",
    7:  "CIRCLE",
    9:  "LAND",
    11: "DRIFT",
    13: "SPORT",
    14: "FLIP",
    15: "AUTOTUNE",
    16: "POSHOLD",
    17: "BRAKE",
    18: "THROW",
    19: "AVOID_ADSB",
    20: "GUIDED_NOGPS",
    21: "SMART_RTL",
}


def mode_name(custom_mode: int) -> str:
    """根据 custom_mode 返回飞行模式名称。"""
    return MODE_MAP.get(custom_mode, f"MODE_{custom_mode}")


def is_rtl(custom_mode: int) -> bool:
    """判断是否为返航模式(RTL 或 SmartRTL)。"""
    return custom_mode in (6, 21)
