"""
YAML 配置加载器
"""
import os
import yaml


class ConfigLoader:
    """加载 config.yaml，提供点号路径访问。"""

    def __init__(self, path="config.yaml"):
        if not os.path.isabs(path):
            # 相对于 main.py 所在目录
            base = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base, "..", path)
        with open(path, "r", encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

    def get(self, path, default=None):
        """
        点号路径取值。
        例: config.get("mqtt.broker") -> "192.168.1.1"
        """
        parts = path.split(".")
        node = self._data
        for p in parts:
            if isinstance(node, dict):
                node = node.get(p)
                if node is None:
                    return default
            else:
                return default
        return node

    @property
    def mqtt(self):
        return self._data.get("mqtt", {})

    @property
    def mavlink(self):
        return self._data.get("mavlink", {})

    @property
    def stm32(self):
        return self._data.get("stm32", {})

    @property
    def camera(self):
        return self._data.get("camera", {})

    @property
    def decision(self):
        return self._data.get("decision", {})

    @property
    def log(self):
        return self._data.get("log", {})

    @property
    def watchdog(self):
        return self._data.get("watchdog", {})
