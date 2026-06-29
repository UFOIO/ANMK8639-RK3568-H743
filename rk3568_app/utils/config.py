# -*- coding: utf-8 -*-
"""
YAML 配置加载器 — 分层合并 + 用户持久化

  加载顺序:
    1. config.yaml      (默认模板，可被部署覆盖)
    2. /etc/hangar/local.yaml (用户修改，永不覆盖)
    3. 深层合并: local.yaml 的值覆盖 config.yaml

  保存:
    save_local() → 只写用户修改过的字段到 local.yaml
"""
import os
import copy
import yaml

_LOCAL_PATH = "/etc/hangar/local.yaml"


def _deep_merge(base, override):
    """深层合并两个字典，override 覆盖 base"""
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(config_path="config.yaml"):
    """加载合并后的完整配置"""
    if not os.path.isabs(config_path):
        base = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base, "..", config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        default_cfg = yaml.safe_load(f) or {}

    # 尝试加载用户覆盖
    if os.path.exists(_LOCAL_PATH):
        with open(_LOCAL_PATH, "r", encoding="utf-8") as f:
            local_cfg = yaml.safe_load(f) or {}
        merged = _deep_merge(default_cfg, local_cfg)
    else:
        merged = default_cfg

    return ConfigLoader(merged)


def save_local(data: dict):
    """保存用户配置到 /etc/hangar/local.yaml"""
    os.makedirs(os.path.dirname(_LOCAL_PATH), exist_ok=True)
    with open(_LOCAL_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_local_raw():
    """读取用户配置原始字典（用于 WebUI 返回）"""
    if os.path.exists(_LOCAL_PATH):
        with open(_LOCAL_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def load_config_raw(config_path="config.yaml"):
    """加载合并后的原始字典（非 ConfigLoader 对象）"""
    if not os.path.isabs(config_path):
        base = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base, "..", config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        default_cfg = yaml.safe_load(f) or {}

    if os.path.exists(_LOCAL_PATH):
        with open(_LOCAL_PATH, "r", encoding="utf-8") as f:
            local_cfg = yaml.safe_load(f) or {}
        return _deep_merge(default_cfg, local_cfg)
    return default_cfg


class ConfigLoader:
    """加载 config，提供点号路径访问。"""

    def __init__(self, data_or_path):
        if isinstance(data_or_path, dict):
            self._data = data_or_path
        else:
            path = data_or_path
            if not os.path.isabs(path):
                base = os.path.dirname(os.path.abspath(__file__))
                path = os.path.join(base, "..", path)
            with open(path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}

    def get(self, path, default=None):
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
    def safety(self):
        return self._data.get("safety", {})

    @property
    def log(self):
        return self._data.get("log", {})

    @property
    def watchdog(self):
        return self._data.get("watchdog", {})

    @property
    def auth(self):
        return self._data.get("auth", {})

    @property
    def web_ui(self):
        return self._data.get("web_ui", {})

    @property
    def data(self):
        return self._data
