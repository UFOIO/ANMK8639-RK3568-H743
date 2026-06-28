"""
日志管理器：分级输出 + 文件按天轮转 + 保留N天 + 可选JSON格式。
"""
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler


class JsonFormatter(logging.Formatter):
    """JSON结构化日志格式，兼容 ELK/Loki 等日志系统。"""
    def format(self, record):
        obj = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "level": record.levelname,
            "module": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            obj["exception"] = str(record.exc_info[1])
        return json.dumps(obj, ensure_ascii=False)


def setup_logger(config):
    """
    初始化全局日志系统。
    config.log.format: "text" (默认) 或 "json"
    """
    log_dir = config.get("dir", "./data/logs")
    log_level = config.get("level", "INFO")
    max_days = config.get("max_days", 30)
    log_format = config.get("format", "text")

    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 文本格式
    text_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台永远用文本（人可读）
    console = logging.StreamHandler()
    console.setFormatter(text_fmt)
    root.addHandler(console)

    # 文件输出：根据配置选择格式
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=max_days,
        encoding="utf-8"
    )
    if log_format == "json":
        file_handler.setFormatter(JsonFormatter())
        # 同时保留一份文本日志方便快速查看
        txt_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, "app.txt.log"),
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        txt_handler.setFormatter(text_fmt)
        root.addHandler(txt_handler)
    else:
        file_handler.setFormatter(text_fmt)
    root.addHandler(file_handler)

    root.info("Logger initialized (level=%s, format=%s, dir=%s)", log_level, log_format, log_dir)
    return root
