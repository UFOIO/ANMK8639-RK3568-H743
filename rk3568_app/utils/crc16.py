"""
CRC16-MODBUS 校验算法
多项式: 0x8005, 初始值: 0xFFFF
"""


def crc16_modbus(data: bytes) -> int:
    """
    计算 MODBUS-CRC16。
    与 STM32 侧保持一致（协议文档第五章）。
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
    return crc


def crc16_verify(data: bytes, expected: int) -> bool:
    """校验 CRC 是否匹配。"""
    return crc16_modbus(data) == expected
