#!/bin/bash
# =============================================
# ANMK8639 Hangar Control System - 快速安装
# 用法: sudo bash install.sh
# 前提: setup.sh 已执行 (venv + pip)
# =============================================
set -e

APP_NAME="hangar"
INSTALL_DIR="/opt/${APP_NAME}"
CONFIG_DIR="/etc/${APP_NAME}"
LOG_DIR="/var/log/${APP_NAME}"
DATA_DIR="/var/lib/${APP_NAME}"
BIN_LINK="/usr/local/bin/${APP_NAME}"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
VENV="/home/kickpi/hangar_venv"

echo "=== ANMK8639 Hangar Control System 安装 ==="

echo "[1/6] 创建目录..."
mkdir -p "${INSTALL_DIR}/data" "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}/snapshots"

echo "[2/6] 复制项目文件..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "${SCRIPT_DIR}/../main.py" "${INSTALL_DIR}/"
cp "${SCRIPT_DIR}/../config.yaml" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/../core" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/../modules" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/../protocol" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/../utils" "${INSTALL_DIR}/"
cp -r "${SCRIPT_DIR}/../deploy" "${INSTALL_DIR}/" 2>/dev/null || true

echo "[3/6] 配置..."
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    cp "${INSTALL_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml"
    echo "  -> 创建默认配置"
else
    echo "  -> 配置已存在，跳过"
fi
rm -f "${INSTALL_DIR}/config.yaml"
ln -sf "${CONFIG_DIR}/config.yaml" "${INSTALL_DIR}/config.yaml"

echo "[4/6] 目录链接..."
rm -rf "${INSTALL_DIR}/data/logs" 2>/dev/null || true
rm -rf "${INSTALL_DIR}/data/snapshots" 2>/dev/null || true
ln -sf "${LOG_DIR}" "${INSTALL_DIR}/data/logs"
ln -sf "${DATA_DIR}" "${INSTALL_DIR}/data/snapshots"

echo "[5/6] 安装 systemd 服务..."
cp "${SCRIPT_DIR}/hangar.service" "${SERVICE_FILE}"
sed -i "s|/usr/bin/python3|${VENV}/bin/python3|g" "${SERVICE_FILE}"
sed -i "s|/home/kickpi/hangar_venv/bin/python3|${VENV}/bin/python3|g" "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${APP_NAME}" 2>/dev/null || true

echo "[6/6] 创建 CLI 命令..."
cp "${SCRIPT_DIR}/hangar-cli.sh" "${BIN_LINK}"
chmod +x "${BIN_LINK}"

echo ""
echo "====================================="
echo "  ? 安装完成"
echo "  命令: hangar start|stop|restart|reload|status|logs|check|config"
echo "  Web:  http://$(hostname -I | awk '{print $1}'):8080"
echo "====================================="
