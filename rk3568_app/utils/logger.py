"""
日志管理器：分级输出 + 文件按天轮转 + 保留N天
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler


def setup_logger(config):
    """
    初始化全局日志系统。
    调用一次即可，后续各模块通过 logging.getLogger(__name__) 获取。
    """
    log_dir = config.get("dir", "./data/logs")
    log_level = config.get("level", "INFO")
    max_days = config.get("max_days", 30)

    os.makedirs(log_dir, exist_ok=True)

    # 根 logger
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 格式
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # 文件输出（按天轮转，保留 max_days 天）
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=max_days,
        encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    root.info("Logger initialized (level=%s, dir=%s)", log_level, log_dir)
    return root
