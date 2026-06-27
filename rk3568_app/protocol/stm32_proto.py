"""
STM32 二进制通信协议编解码。

帧结构 (详见 docs/最新计划书.md 第五章):
  +--------+--------+--------+----------+----------+--------+--------+
  | 帧头   | 地址   | 命令   | 数据长度  | 数据      | CRC16  | 帧尾   |
  | 2B     | 1B     | 1B     | 2B(LE)   | NB       | 2B     | 2B     |
  | 0xAA55 | 0x01   | CMD    | Len      | Payload  | MODBUS | 0x55AA |
  +--------+--------+--------+----------+----------+--------+--------+
"""
import struct
from utils.crc16 import crc16_modbus

# 帧常量
FRAME_HEAD = b"\xAA\x55"
FRAME_TAIL = b"\x55\xAA"
STM32_ADDR = 0x01
MAX_DATA_LEN = 512
MIN_FRAME_LEN = 10  # 头(2) + 地址(1) + 命令(1) + 长度(2) + CRC(2) + 尾(2)


def build_frame(cmd: int, data: bytes = b"") -> bytes:
    """
    构建下行指令帧。
    cmd:  指令码 (0x01-0x32)
    data: 载荷数据
    """
    if len(data) > MAX_DATA_LEN:
        raise ValueError(f"Data too long: {len(data)} > {MAX_DATA_LEN}")
    addr_cmd_len = struct.pack("<BBH", STM32_ADDR, cmd, len(data))
    crc_input = addr_cmd_len + data
    crc = crc16_modbus(crc_input)
    crc_bytes = struct.pack("<H", crc)
    return FRAME_HEAD + crc_input + crc_bytes + FRAME_TAIL


def parse_frame(data: bytes) -> dict | None:
    """
    解析上行帧。返回 None 表示帧不完整或无效。
    返回: {"cmd": int, "data": bytes} 或 None
    """
    if len(data) < MIN_FRAME_LEN:
        return None
    # 找帧头
    idx = data.find(FRAME_HEAD)
    if idx < 0:
        return None
    start = idx + 2  # 跳过帧头
    if len(data) - start < 7:  # 至少需要 地址(1)+命令(1)+长度(2)+CRC(2)
        return None
    # 解析地址和命令
    addr = data[start]
    cmd = data[start + 1]
    data_len = struct.unpack_from("<H", data, start + 2)[0]
    if data_len > MAX_DATA_LEN:
        return None
    # 检查是否有足够数据
    expected_end = start + 4 + data_len + 2 + 2  # 地址+命令+长度 + 数据 + CRC + 帧尾
    if len(data) < expected_end:
        return None
    # 提取数据
    payload = data[start + 4 : start + 4 + data_len]
    # 提取并验证 CRC
    crc_received = struct.unpack_from("<H", data, start + 4 + data_len)[0]
    crc_calc = crc16_modbus(data[start : start + 4 + data_len])
    if crc_received != crc_calc:
        return None
    # 验证帧尾
    tail = data[expected_end - 2 : expected_end]
    if tail != FRAME_TAIL:
        return None
    return {"addr": addr, "cmd": cmd, "data": payload}


# ===== 指令码常量 =====
CMD_OPEN_DOOR   = 0x01
CMD_CLOSE_DOOR  = 0x02
CMD_LOCK        = 0x03
CMD_UNLOCK      = 0x04
CMD_GET_STATUS  = 0x10
CMD_GET_SENSORS = 0x11
CMD_HEARTBEAT   = 0x12
CMD_SOFT_RESET  = 0x20
CMD_ENTER_IAP   = 0x30
CMD_IAP_DATA    = 0x31
CMD_IAP_FINISH  = 0x32

# 上行命令码
RPT_STATUS  = 0x80
RPT_SENSORS = 0x81
RPT_ALARM   = 0x82
RPT_ACK     = 0x83

# ACK 结果码
ACK_OK      = 0x00
ACK_FAIL    = 0x01
ACK_TIMEOUT = 0x02
ACK_UNKNOWN = 0xFF
