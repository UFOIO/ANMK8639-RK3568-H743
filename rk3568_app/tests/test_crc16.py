"""CRC16-MODBUS 单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.crc16 import crc16_modbus, crc16_verify


def test_empty():
    assert crc16_modbus(b"") == 0xFFFF

def test_known_vector():
    result = crc16_modbus(b"\x01\x02\x03")
    expected = 0x6161
    assert result == expected, f"Expected 0x{expected:04X}, got 0x{result:04X}"

def test_frame_crc():
    frame = b"\x01\x01\x00\x00"  # 开舱门: 地址0x01 命令0x01 长度0
    crc = crc16_modbus(frame)
    print(f"OPEN_DOOR CRC: 0x{crc:04X}")
    assert 0x0000 <= crc <= 0xFFFF

def test_verify():
    data = b"\x01\x10\x00\x00"
    crc = crc16_modbus(data)
    assert crc16_verify(data, crc) is True
    assert crc16_verify(data, crc ^ 1) is False

if __name__ == "__main__":
    for f in [test_empty, test_known_vector, test_frame_crc, test_verify]:
        f()
        print(f"  PASS: {f.__name__}")
    print("\nAll CRC16 tests passed!")
