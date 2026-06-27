"""
USB 串口通信模块：与 STM32H743 进行二进制帧通信。
"""
import logging
import threading
import time
from queue import Queue, Empty
import serial

from protocol.stm32_proto import (
    build_frame, parse_frame, FRAME_HEAD,
    CMD_OPEN_DOOR, CMD_CLOSE_DOOR, CMD_LOCK, CMD_UNLOCK,
    CMD_GET_STATUS, CMD_GET_SENSORS, CMD_SOFT_RESET,
    CMD_ENTER_IAP, CMD_IAP_DATA, CMD_IAP_FINISH,
    RPT_STATUS, RPT_SENSORS, RPT_ALARM, RPT_ACK,
    ACK_OK, ACK_FAIL, ACK_TIMEOUT, ACK_UNKNOWN,
)

logger = logging.getLogger(__name__)


class STM32Comm:
    """STM32 USB CDC 串口通信模块。"""

    def __init__(self, config: dict, event_bus, app_state):
        self._port = config.get("port", "/dev/ttyACM0")
        self._baudrate = config.get("baudrate", 115200)
        self._cmd_timeout = config.get("cmd_timeout", 0.5)
        self._cmd_retry = config.get("cmd_retry", 3)

        self._event_bus = event_bus
        self._app_state = app_state
        self._ser = None
        self._running = False
        self._cmd_queue = Queue()
        self._open_warned = False

    def start(self):
        self._running = True
        self._open()
        t_recv = threading.Thread(target=self._recv_loop, daemon=True)
        t_recv.start()
        t_cmd = threading.Thread(target=self._cmd_worker, daemon=True)
        t_cmd.start()
        logger.info("STM32Comm started on %s", self._port)
        self._app_state.log_event("stm32", "info", "STM32通信模块已启动 (" + self._port + ")")

    def stop(self):
        self._running = False
        if self._ser and self._ser.is_open:
            self._ser.close()
        logger.info("STM32Comm stopped")
        self._app_state.log_event("stm32", "info", "STM32通信模块已停止")

    def send_command(self, cmd: int, data: bytes = b"") -> bool:
        self._cmd_queue.put((cmd, data, threading.Event()))
        return True

    def _open(self):
        try:
            self._ser = serial.Serial(self._port, self._baudrate, timeout=0.1)
            was_connected = self._app_state.get("hangar.stm32_connected")
            self._app_state.set("hangar.stm32_connected", True)
            logger.info("Serial opened: %s", self._port)
            if not was_connected:
                self._app_state.log_event("stm32", "info", "STM32串口已连接: " + self._port)
        except serial.SerialException:
            if self._app_state.get("hangar.stm32_connected"):
                self._app_state.log_event("stm32", "warn", "STM32串口断开")
            self._app_state.set("hangar.stm32_connected", False)
            self._ser = None

    def _recv_loop(self):
        buf = bytearray()
        while self._running:
            if self._ser is None or not self._ser.is_open:
                time.sleep(3)
                self._open()
                continue
            try:
                chunk = self._ser.read(256)
                if chunk:
                    buf.extend(chunk)
                    result = parse_frame(bytes(buf))
                    if result:
                        self._handle_frame(result)
                        idx = buf.find(FRAME_HEAD)
                        if idx >= 0:
                            del buf[:idx]
                            frame_len = 9 + len(result["data"])
                            del buf[:frame_len]
            except serial.SerialException:
                logger.warning("Serial error, will reconnect...")
                self._app_state.set("hangar.stm32_connected", False)
                self._app_state.log_event("stm32", "warn", "STM32串口通信错误，将重连")
                self._ser = None
            except Exception:
                logger.exception("STM32 recv error")

    def _handle_frame(self, frame: dict):
        cmd = frame["cmd"]
        data = frame["data"]

        if cmd == RPT_STATUS and len(data) >= 8:
            door = data[0]
            lock = data[1]
            alarms = int.from_bytes(data[2:4], "little")
            temp = int.from_bytes(data[4:6], "little", signed=True) / 10.0
            hum = int.from_bytes(data[6:8], "little") / 10.0
            self._app_state.set("hangar.door_status", self._door_str(door))
            self._app_state.set("hangar.lock_status", self._lock_str(lock))
            self._app_state.set("hangar.alarm_flags", alarms)
            self._app_state.set("hangar.temperature", temp)
            self._app_state.set("hangar.humidity", hum)
            self._app_state.set("hangar.last_status_update", time.time())
            self._event_bus.publish("HANGAR_STATUS", {"door": door, "lock": lock})
            if alarms:
                self._event_bus.publish("HANGAR_ALARM", {"flags": alarms})
                self._app_state.log_event("stm32", "error",
                                           "机库告警: flags=0x" + format(alarms, "04X"))

        elif cmd == RPT_SENSORS:
            pass

        elif cmd == RPT_ACK and len(data) >= 2:
            result = data[1]
            error_code = data[2] if len(data) >= 3 else 0xFF
            self._event_bus.publish("STM32_ACK", {
                "cmd": data[0], "result": result, "error": error_code,
            })
            if result == ACK_FAIL:
                self._app_state.log_event("stm32", "error",
                                           "STM32指令失败: cmd=0x" + format(data[0], "02X") +
                                           " error=" + str(error_code))

        elif cmd == RPT_ALARM and len(data) >= 4:
            flags = int.from_bytes(data[:4], "little")
            self._app_state.set("hangar.alarm_flags", flags)
            if flags:
                self._event_bus.publish("HANGAR_ALARM", {"flags": flags})
                self._app_state.log_event("stm32", "error",
                                           "机库告警: flags=0x" + format(flags, "04X"))

    def _cmd_worker(self):
        while self._running:
            try:
                cmd, data, done_event = self._cmd_queue.get(timeout=0.5)
                frame = build_frame(cmd, data)
                for attempt in range(self._cmd_retry):
                    if self._ser and self._ser.is_open:
                        try:
                            self._ser.write(frame)
                            self._ser.flush()
                        except serial.SerialException:
                            logger.error("Serial write failed")
                            break
                    break
                done_event.set()
            except Empty:
                pass
            except Exception:
                logger.exception("CMD worker error")

    @staticmethod
    def _door_str(v: int) -> str:
        m = {0: "CLOSED", 1: "OPEN", 2: "MOVING"}
        return m.get(v, "UNKNOWN")

    @staticmethod
    def _lock_str(v: int) -> str:
        m = {0: "UNLOCKED", 1: "LOCKED"}
        return m.get(v, "UNKNOWN")
