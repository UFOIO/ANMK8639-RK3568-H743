"""
STM32 固件升级管理器。
通过 USB 串口 IAP 协议远程升级 STM32H743 固件。
"""
import hashlib
import logging
import os
import threading
import time
from enum import Enum

from protocol.stm32_proto import (
    CMD_ENTER_IAP, CMD_IAP_DATA, CMD_IAP_FINISH,
    RPT_ACK, ACK_OK, ACK_FAIL, ACK_TIMEOUT,
)

logger = logging.getLogger(__name__)

BLOCK_SIZE = 1024


class UpgradeState(Enum):
    IDLE = "idle"
    ENTERING_IAP = "entering_iap"
    TRANSFERRING = "transferring"
    FINISHING = "finishing"
    DONE = "done"
    FAILED = "failed"


class UpgradeManager:
    """STM32 IAP 固件升级。"""

    def __init__(self, config: dict, stm32_comm, event_bus):
        self._stm32 = stm32_comm
        self._event_bus = event_bus
        self._block_size = config.get("block_size", BLOCK_SIZE)
        self._block_timeout = config.get("block_timeout", 3.0)
        self._state = UpgradeState.IDLE
        self._cancel_flag = threading.Event()
        self._last_ack = None
        self._ack_event = threading.Event()

        # 订阅 ACK 消息
        event_bus.subscribe("STM32_ACK", self._on_ack)

        logger.info("UpgradeManager ready")

    # ===== 公共接口 =====

    def start_upgrade(self, firmware_path: str) -> bool:
        """
        发起固件升级。返回 True 表示流程启动成功。
        升级过程异步进行，通过事件总线报告进度。
        """
        if self._state != UpgradeState.IDLE:
            logger.warning("Upgrade already in progress: %s", self._state.value)
            return False

        if not os.path.exists(firmware_path):
            logger.error("Firmware not found: %s", firmware_path)
            self._report("error", "Firmware file not found")
            return False

        self._firmware_path = firmware_path
        self._cancel_flag.clear()
        threading.Thread(target=self._upgrade_worker, daemon=True).start()
        return True

    def cancel(self):
        """取消正在进行的升级。"""
        self._cancel_flag.set()
        logger.warning("Upgrade cancel requested")

    @property
    def state(self) -> str:
        return self._state.value

    # ===== 内部 =====

    def _upgrade_worker(self):
        try:
            self._do_upgrade()
        except Exception:
            logger.exception("Upgrade fatal error")
            self._fail("Internal error")

    def _do_upgrade(self):
        # 1. 校验固件
        firmware = self._load_firmware()
        if firmware is None:
            return
        total_blocks = (len(firmware) + self._block_size - 1) // self._block_size
        md5_full = hashlib.md5(firmware).digest()
        logger.info("Firmware: %d bytes, %d blocks, MD5=%s",
                    len(firmware), total_blocks, md5_full.hex())

        # 2. 进入 IAP 模式
        self._set_state(UpgradeState.ENTERING_IAP)
        self._report("progress", "Entering IAP mode...", 0)
        if not self._send_and_wait_ack(CMD_ENTER_IAP, timeout=2.0):
            self._fail("STM32 did not enter IAP mode")
            return
        time.sleep(0.5)  # 给 STM32 切换到 Bootloader 的缓冲时间

        # 3. 分块传输
        self._set_state(UpgradeState.TRANSFERRING)
        for seq in range(total_blocks):
            if self._cancel_flag.is_set():
                self._fail("Cancelled by user")
                return

            start = seq * self._block_size
            end = min(start + self._block_size, len(firmware))
            block_data = firmware[start:end]

            # 构建 IAP_DATA 帧
            seq_bytes = seq.to_bytes(4, "little")
            self._stm32.send_command(CMD_IAP_DATA, seq_bytes + block_data)

            # 等待 ACK
            if not self._wait_ack(self._block_timeout):
                self._fail(f"Block {seq}/{total_blocks} timeout")
                return

            ack = self._last_ack
            if ack and ack.get("result") != ACK_OK:
                err = ack.get("error", 0xFF)
                self._fail(f"Block {seq} failed: result={ack.get('result')} err=0x{err:02X}")
                return

            pct = int((seq + 1) / total_blocks * 100)
            if seq % 10 == 0 or seq == total_blocks - 1:
                self._report("progress", f"Block {seq+1}/{total_blocks}", pct)

        # 4. 完成
        self._set_state(UpgradeState.FINISHING)
        self._report("progress", "Verifying...", 99)
        # 发送 IAP_FINISH，携带 MD5 前 4 字节
        self._stm32.send_command(CMD_IAP_FINISH, md5_full[:4])
        if not self._wait_ack(5.0):
            self._fail("IAP_FINISH timeout")
            return

        ack = self._last_ack
        if ack and ack.get("result") == ACK_OK:
            self._set_state(UpgradeState.DONE)
            self._report("success", "Upgrade complete", 100)
            logger.info("Upgrade successful!")
        else:
            self._fail("IAP_FINISH rejected by STM32")

    def _load_firmware(self) -> bytes | None:
        try:
            with open(self._firmware_path, "rb") as f:
                data = f.read()
            if len(data) == 0:
                self._report("error", "Firmware file is empty")
                return None
            if len(data) > 2 * 1024 * 1024:  # 2MB 上限
                self._report("error", "Firmware too large (>2MB)")
                return None
            return data
        except OSError as e:
            self._report("error", f"Read firmware failed: {e}")
            return None

    def _send_and_wait_ack(self, cmd: int, timeout: float = 2.0) -> bool:
        """发送指令并等待 ACK。"""
        self._ack_event.clear()
        self._stm32.send_command(cmd)
        return self._wait_ack(timeout)

    def _wait_ack(self, timeout: float) -> bool:
        """等待 ACK 到来。"""
        return self._ack_event.wait(timeout)

    def _on_ack(self, data: dict):
        """收到 STM32 ACK 后的回调。"""
        self._last_ack = data
        self._ack_event.set()

    def _set_state(self, state: UpgradeState):
        self._state = state
        logger.info("Upgrade state: %s", state.value)

    def _fail(self, reason: str):
        self._set_state(UpgradeState.FAILED)
        self._report("error", reason, -1)
        logger.error("Upgrade failed: %s", reason)

    def _report(self, level: str, message: str, progress: int = -1):
        """通过事件总线上报进度（由 MQTT 模块转发到地面站）。"""
        self._event_bus.publish("UPGRADE_STATUS", {
            "level": level,
            "message": message,
            "progress": progress,
            "state": self._state.value,
        })
