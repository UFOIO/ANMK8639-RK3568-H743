#!/bin/bash
# ANMK8639 Hangar Control System - One-click deploy
set -e

APP="hangar"
INSTALL_DIR="/opt/${APP}"
CONFIG_DIR="/etc/${APP}"
LOG_DIR="/var/log/${APP}"
DATA_DIR="/var/lib/${APP}"
VENV="/home/kickpi/hangar_venv"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo " ANMK8639 Hangar Control Deploy"
echo "=========================================="

echo "[1/8] System deps..."
sudo apt update -qq
sudo apt install -y -qq python3-pip python3-venv python3-lxml ffmpeg 2>/dev/null

echo "[2/8] Virtual env..."
python3 -m venv "${VENV}" 2>/dev/null || true
source "${VENV}/bin/activate"
pip install --upgrade pip -q 2>/dev/null || true

echo "[3/8] Python packages..."
pip install paho-mqtt pymavlink --no-deps -q 2>/dev/null
pip install fastcrc -q 2>/dev/null || true

echo "[4/8] Directories..."
sudo mkdir -p "${INSTALL_DIR}" "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}/snapshots"

echo "[5/8] Copy files..."
sudo cp "${SCRIPT_DIR}/main.py" "${INSTALL_DIR}/"
sudo cp "${SCRIPT_DIR}/config.yaml" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/core" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/modules" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/protocol" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/utils" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/deploy" "${INSTALL_DIR}/"

echo "[6/8] Config..."
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    sudo cp "${INSTALL_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml"
fi
sudo ln -sf "${CONFIG_DIR}/config.yaml" "${INSTALL_DIR}/config.yaml"
sudo chmod 600 "${CONFIG_DIR}/config.yaml"
sudo ln -sfn "${LOG_DIR}" "${INSTALL_DIR}/data/logs"
sudo ln -sfn "${DATA_DIR}" "${INSTALL_DIR}/data/snapshots"

echo "[7/8] systemd..."
sudo cp "${INSTALL_DIR}/deploy/hangar.service" /etc/systemd/system/
sudo sed -i "s|/usr/bin/python3|${VENV}/bin/python3|g" /etc/systemd/system/hangar.service
sudo systemctl daemon-reload
sudo systemctl enable "${APP}"

echo "[8/8] CLI..."
sudo cp "${INSTALL_DIR}/deploy/hangar-cli.sh" /usr/local/bin/hangar 2>/dev/null || true
sudo chmod +x /usr/local/bin/hangar 2>/dev/null || true

echo ""
sudo systemctl restart "${APP}"
sleep 2

if systemctl is-active --quiet "${APP}"; then
    echo "DEPLOY OK"
    echo "  hangar logs   - live output"
    echo "  hangar check  - quick status"
    echo "  Web: http://$(hostname -I | awk '{print $1}'):8080"
else
    echo "DEPLOY FAILED - check:"
    echo "  sudo journalctl -u hangar --no-pager -n 20"
fi
