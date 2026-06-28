#!/bin/bash
# =============================================
# ANMK8639 Hangar Control System - 安装脚本
# 用法: sudo bash install.sh
# ==============================================
set -e

APP_NAME="hangar"
INSTALL_DIR="/opt/${APP_NAME}"
CONFIG_DIR="/etc/${APP_NAME}"
LOG_DIR="/var/log/${APP_NAME}"
DATA_DIR="/var/lib/${APP_NAME}"
BIN_LINK="/usr/local/bin/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

echo "=== ANMK8639 Hangar Control System 安装 ==="

echo "[1/6] 创建目录..."
mkdir -p "${INSTALL_DIR}" "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}/snapshots"

echo "[2/6] 复制改用文件..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
rsync -a --exclude="__pycache__" --exclude="*.pyc" --exclude="data/" "${SCRIPT_DIR}/" "${INSTALL_DIR}/"

echo "[3/6] 配置..."
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    cp "${INSTALL_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml"
    echo "  -> 创建默认配置"
else
    echo "  -> 配置已存在，跳过"
fi
ln -sf "${CONFIG_DIR}/config.yaml" "${INSTALL_DIR}/config.yaml"

echo "[4/6] 目录链接..."
ln -sfn "${LOG_DIR}" "${INSTALL_DIR}/data/logs"
ln -sfn "${DATA_DIR}" "${INSTALL_DIR}/data/snapshots"

echo "[5/6] 安装 systemd 服务..."
cp "${INSTALL_DIR}/deploy/hangar.service" "${SERVICE_FILE}"
# 确保使用 venv Python
sed -i "s|/usr/bin/python3|/home/kickpi/hangar_venv/bin/python3|g" "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${APP_NAME}"

echo "[6/6] 创建 CLI 命令..."
cp "${INSTALL_DIR}/deploy/hangar-cli.sh" "${BIN_LINK}"
chmod +x "${BIN_LINK}"

echo ""
echo "====================================="
echo "  ✅ 安装完成"
echo "  命令: hangar start|stop|restart|reload|status|logs|check|config"
echo "  Web:  http://$(hostname -I | awk '{print $1}'):8080"
echo "====================================="
