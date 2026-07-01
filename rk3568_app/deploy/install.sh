#!/bin/bash
# =============================================
# ANMK8639 Hangar Control System - 快速安装
# 用法: sudo bash deploy/install.sh
# 前提: setup_network.sh 已执行 (网络通)
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

if [ "$(id -u)" -ne 0 ]; then
    echo "请用 root 跑: sudo bash $0"
    exit 1
fi

echo "=== ANMK8639 Hangar Control System 安装 ==="

echo "[1/7] 安装系统依赖..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv ffmpeg iptables-persistent >/dev/null 2>&1 || true

echo "[2/7] 创建目录..."
mkdir -p "${INSTALL_DIR}/data" "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}/snapshots"

echo "[3/7] 创建 Python 虚拟环境..."
if [ ! -d "${VENV}" ]; then
    sudo -u kickpi python3 -m venv "${VENV}" 2>/dev/null || python3 -m venv "${VENV}"
fi

echo "[4/7] 复制项目文件..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/.."
cp "${SRC_DIR}/main.py" "${INSTALL_DIR}/"
cp "${SRC_DIR}/config.yaml" "${INSTALL_DIR}/"
cp -r "${SRC_DIR}/modules" "${INSTALL_DIR}/"
cp -r "${SRC_DIR}/protocol" "${INSTALL_DIR}/"
cp -r "${SRC_DIR}/utils" "${INSTALL_DIR}/"
cp -r "${SRC_DIR}/deploy" "${INSTALL_DIR}/" 2>/dev/null || true

echo "[5/7] 安装 Python 依赖..."
"${VENV}/bin/pip" install --quiet --upgrade pip
"${VENV}/bin/pip" install --quiet pyserial paho-mqtt pymavlink pyyaml
"${VENV}/bin/pip" install --quiet -r "${SRC_DIR}/requirements.txt" 2>/dev/null || true

echo "[6/7] 配置..."
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    cp "${INSTALL_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml"
    echo "  -> 创建默认配置 /etc/hangar/config.yaml"
fi
if [ ! -f "${CONFIG_DIR}/local.yaml" ]; then
    cp "${INSTALL_DIR}/config.yaml" "${CONFIG_DIR}/local.yaml"
    echo "  -> 创建初始 local.yaml (用户配置)"
    echo "  -> 提示: 编辑 ${CONFIG_DIR}/local.yaml 填入 tailscale_auth_key 等"
fi
rm -f "${INSTALL_DIR}/config.yaml"
ln -sf "${CONFIG_DIR}/config.yaml" "${INSTALL_DIR}/config.yaml"

# 目录软链接
rm -rf "${INSTALL_DIR}/data/logs" 2>/dev/null || true
rm -rf "${INSTALL_DIR}/data/snapshots" 2>/dev/null || true
ln -sf "${LOG_DIR}" "${INSTALL_DIR}/data/logs"
ln -sf "${DATA_DIR}" "${INSTALL_DIR}/data/snapshots"

echo "[7/7] 安装 systemd 服务..."
cp "${SCRIPT_DIR}/hangar.service" "${SERVICE_FILE}"
sed -i "s|/usr/bin/python3|${VENV}/bin/python3|g" "${SERVICE_FILE}"
sed -i "s|/home/kickpi/hangar_venv/bin/python3|${VENV}/bin/python3|g" "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${APP_NAME}" 2>/dev/null || true

# CLI 命令
cp "${SCRIPT_DIR}/hangar-cli.sh" "${BIN_LINK}"
chmod +x "${BIN_LINK}"

echo ""
echo "====================================="
echo "  ✓ Hangar 安装完成"
echo "====================================="
echo "  命令: hangar start|stop|restart|reload|status|logs|check|config"
echo "  Web:  http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "  下一步: 编辑 /etc/hangar/local.yaml 填 tailscale_auth_key"
echo "          然后跑: sudo bash deploy/setup_tailscale.sh"
echo "====================================="
