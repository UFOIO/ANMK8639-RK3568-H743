"""STM32 协议编解码单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol.stm32_proto import (
    build_frame, parse_frame,
    CMD_OPEN_DOOR, CMD_CLOSE_DOOR, CMD_LOCK,
    CMD_GET_STATUS, CMD_GET_SENSORS,
    FRAME_HEAD, FRAME_TAIL, MIN_FRAME_LEN,
)

def test_build_no_data():
    """构建无数据指令帧（如开舱门）。"""
    frame = build_frame(CMD_OPEN_DOOR)
    assert len(frame) == MIN_FRAME_LEN, f"len={len(frame)}"
    assert frame[:2] == FRAME_HEAD, f"head={frame[:2].hex()}"
    assert frame[-2:] == FRAME_TAIL, f"tail={frame[-2:].hex()}"
    print(f"  Frame: {frame.hex().upper()}")

def test_build_with_data():
    """构建带数据指令帧。"""
    data = b"\x01\x02\x03\x04"
    frame = build_frame(CMD_GET_STATUS, data)
    assert len(frame) == MIN_FRAME_LEN + 4
    assert frame[:2] == FRAME_HEAD
    assert frame[-2:] == FRAME_TAIL

def test_parse_valid():
    """解析正常帧。"""
    frame = build_frame(CMD_CLOSE_DOOR)
    result = parse_frame(frame)
    assert result is not None, "parse_frame returned None"
    assert result["cmd"] == CMD_CLOSE_DOOR
    assert result["data"] == b""

def test_parse_with_data():
    """解析带数据帧。"""
    data = b"\xAA\xBB\xCC"
    frame = build_frame(CMD_GET_SENSORS, data)
    result = parse_frame(frame)
    assert result is not None
    assert result["cmd"] == CMD_GET_SENSORS
    assert result["data"] == data

def test_parse_corrupt_crc():
    """CRC错误应返回None。"""
    frame = build_frame(CMD_LOCK)
    # 篡改CRC
    corrupt = bytearray(frame)
    corrupt[-4] ^= 0xFF  # 翻转CRC一个字节
    result = parse_frame(bytes(corrupt))
    assert result is None

def test_parse_short():
    """太短的帧应返回None。"""
    assert parse_frame(b"\xAA") is None
    assert parse_frame(b"\xAA\x55\x01") is None

def test_parse_no_header():
    """无帧头数据应返回None。"""
    assert parse_frame(b"\x00" * 20) is None

def test_roundtrip():
    """构建 -> 解析 往返测试。"""
    for cmd in [CMD_OPEN_DOOR, CMD_CLOSE_DOOR, CMD_LOCK,
                CMD_GET_STATUS, CMD_GET_SENSORS]:
        frame = build_frame(cmd)
        result = parse_frame(frame)
        assert result is not None, f"roundtrip failed for cmd=0x{cmd:02X}"
        assert result["cmd"] == cmd

if __name__ == "__main__":
    tests = [test_build_no_data, test_build_with_data, test_parse_valid,
             test_parse_with_data, test_parse_corrupt_crc,
             test_parse_short, test_parse_no_header, test_roundtrip]
    for t in tests:
        t()
        print(f"  PASS: {t.__name__}")
    print("\nAll STM32 proto tests passed!")
