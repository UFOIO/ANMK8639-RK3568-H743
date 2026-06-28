"""
终端状态面板 — ANSI 转义码原地刷新。
在 SSH/终端前台运行时显示多行实时状态。
后台运行(systemd)时自动降级为单行日志。
"""
import os
import sys
import time

# === ANSI 控制码 ===
CLEAR = "\033[2J"        # 清屏
HOME = "\033[H"          # 光标归位
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_LINE = "\033[2K"   # 清除当前行
RESET = "\033[0m"

# === 颜色 ===
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
CYAN = "\033[36m"
WHITE = "\033[37m"

def _c(color, text):
    """Wrap text with color + reset."""
    return color + str(text) + RESET

def _bar(pct, width=20):
    """Draw a progress bar: ████░░░░░░ 45%"""
    filled = int(pct / 100 * width)
    bar_str = "█" * filled + "░" * (width - filled)
    color = GREEN if pct < 70 else YELLOW if pct < 90 else RED
    return _c(color, bar_str) + f" {pct:5.1f}%"


class TerminalDashboard:
    """终端实时状态面板。"""

    def __init__(self, app_state, config):
        self._app = app_state
        self._cfg = config
        self._first = True
        self._lines = 0
        self._enabled = sys.stdout.isatty() and not os.environ.get("JOURNAL_STREAM", "")

    @property
    def enabled(self):
        return self._enabled

    def start(self):
        if self._enabled:
            sys.stdout.write(HIDE_CURSOR)
            sys.stdout.flush()

    def stop(self):
        if self._enabled:
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write(CLEAR)
            sys.stdout.flush()

    def refresh(self):
        """刷新一帧。"""
        if not self._enabled:
            return

        health = self._app.health()
        status = self._app.to_dict()
        events = self._app.get_events(5)

        lines = []
        w = self._term_width()

        # === 顶栏 ===
        uptime = int(health.get("uptime", 0))
        uptime_str = f"{uptime // 60}m{uptime % 60}s"
        title = _c(BOLD + CYAN, " ANMK8639  Hangar Control ")
        lines.append("┌" + "─" * (w - 2) + "┐")
        header = f"│{title}{' ' * (w - 2 - 25 - 25)}{_c(DIM, 'RUN '+uptime_str):>25}│"
        lines.append(_fix_width(header, w))

        # === 连接状态 ===
        lines.append("├" + "─" * (w - 2) + "┤")
        lines.append(_fix_width(f"│ {_c(BOLD, 'Connections')}" + " " * (w - 16) + "│", w))

        conns = [
            ("MAVLink", health["mavlink"]["connected"], self._ago(health["mavlink"].get("last_hb_sec")),
             status.get("drone", {}).get("mode", "--")),
            ("MQTT   ", health["mqtt"]["connected"], self._ago(health["mqtt"].get("last_msg_sec")),
             "enabled" if self._cfg.get("mqtt", {}).get("enabled") else "disabled"),
            ("STM32  ", health["stm32"]["connected"], self._ago(health["stm32"].get("last_status_sec")),
             self._cfg.get("stm32", {}).get("port", "/dev/ttyACM0")),
            ("Camera ", health["camera"].get("last_snapshot_sec") is not None,
             self._ago(health["camera"].get("last_snapshot_sec")),
             "snapshot"),
        ]
        for name, ok, ago, detail in conns:
            icon = _c(GREEN, "●") if ok else _c(RED, "○") if ago != "--" else _c(YELLOW, "◐")
            line = f"│  {icon} {_c(BOLD, name)} {detail:<14} {_c(DIM, ago)}"
            lines.append(_fix_width(line + " " * (w - len(line) + 10) + "│", w))

        # === 无人机 ===
        drone = status.get("drone", {})
        if drone.get("mode"):
            lines.append("├" + "─" * (w - 2) + "┤")
            lines.append(_fix_width(f"│ {_c(BOLD, 'Drone')}" + " " * (w - 9) + "│", w))
            dline = (f"│  Mode: {_c(CYAN, drone.get('mode','--'))}  "
                     f"Batt: {_c(GREEN if drone.get('battery',0)>20 else RED, str(drone.get('battery','--'))+'%')}  "
                     f"Alt: {drone.get('alt','--')}m  "
                     f"Speed: {drone.get('groundspeed','--')} m/s")
            lines.append(_fix_width(dline + " " * (w - len(dline) + 17) + "│", w))
            gps = (f"│  GPS: {drone.get('lat','--')},{drone.get('lon','--')}  "
                   f"Sats: {drone.get('satellites','--')}  "
                   f"Fix: {drone.get('fix_type','--')}  "
                   f"Armed: {_c(GREEN,'YES') if drone.get('armed') else _c(DIM,'NO')}")
            lines.append(_fix_width(gps + " " * (w - len(gps) + 10) + "│", w))

        # === 最近事件 ===
        if events:
            lines.append("├" + "─" * (w - 2) + "┤")
            lines.append(_fix_width(f"│ {_c(BOLD, 'Events')} (last {len(events)})" + " " * (w - 16) + "│", w))
            for e in events[-4:]:
                ts = time.strftime("%H:%M:%S", time.localtime(e["ts"]))
                lvl = e["level"]
                lcolor = {"info": BLUE, "warn": YELLOW, "error": RED}.get(lvl, WHITE)
                src = e["source"][:10]
                msg = e["message"][:w - 36]
                eline = f"│  {_c(DIM, ts)} {_c(lcolor, lvl.upper()):8} {_c(CYAN, src):12} {msg}"
                lines.append(_fix_width(eline + " " * (w - len(eline) + 8) + "│", w))

        # === 系统资源 ===
        sys_info = self._get_sys()
        lines.append("├" + "─" * (w - 2) + "┤")
        cpu_bar = _bar(sys_info["cpu"], 15)
        ram_bar = _bar(sys_info["ram"], 15)
        sline = (f"│  CPU {cpu_bar}  RAM {ram_bar}  "
                 f"{sys_info.get('ram_used','')}/{sys_info.get('ram_total','')}")
        lines.append(_fix_width(sline + " " * (w - len(sline) + 5) + "│", w))

        # === 底栏 ===
        lines.append("└" + "─" * (w - 2) + "┘")
        lines.append(_c(DIM, "  Ctrl+C to stop  |  hangar status  |  Web :8080"))
        lines.append("")

        # === 输出 ===
        if self._first:
            sys.stdout.write(CLEAR)
            self._first = False
        else:
            # 光标移到第一行
            sys.stdout.write(f"\033[{self._lines}A")

        for line in lines:
            sys.stdout.write(CLEAR_LINE + line + "\n")
        sys.stdout.flush()

        self._lines = len(lines)

    def _term_width(self):
        try:
            return os.get_terminal_size().columns
        except Exception:
            return 80

    def _ago(self, ts):
        if ts is None:
            return "--"
        sec = time.time() - ts
        if sec < 5:
            return _c(GREEN, "just now")
        if sec < 60:
            return f"{int(sec)}s ago"
        return f"{int(sec//60)}m ago"

    def _get_sys(self):
        info = {"cpu": 0, "ram": 0, "ram_used": "", "ram_total": ""}
        try:
            with open("/proc/loadavg") as f:
                info["cpu"] = min(float(f.read().split()[0]) * 100 / (os.cpu_count() or 4), 100)
        except Exception:
            pass
        try:
            with open("/proc/meminfo") as f:
                mem = {}
                for line in f:
                    p = line.split(":")
                    if len(p) == 2:
                        mem[p[0].strip()] = int(p[1].strip().split()[0])
                total = mem.get("MemTotal", 1)
                avail = mem.get("MemAvailable", 1)
                info["ram"] = round((total - avail) / total * 100, 1)
                info["ram_used"] = f"{(total - avail)//1024}M"
                info["ram_total"] = f"{total//1024}M"
        except Exception:
            pass
        return info


def _fix_width(line, width):
    """确保行长度不超过终端宽度。"""
    # 去掉ANSI码计算实际宽度
    plain = ""
    skip = False
    for c in line:
        if c == "\033":
            skip = True
        if not skip:
            plain += c
        if skip and c == "m":
            skip = False
    if len(plain) > width:
        # 简单截断
        return line[:width]
    return line
