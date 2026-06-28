#!/bin/bash
set -e
APP=hangar
INSTALL_DIR=/opt/hangar
CONFIG_DIR=/etc/hangar
LOG_DIR=/var/log/hangar
DATA_DIR=/var/lib/hangar
VENV=/home/kickpi/hangar_venv
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=========================================="
echo " ANMK8639 Hangar Control Deploy"
echo "=========================================="

echo "[1/8] System deps..."
sudo apt update -qq 2>/dev/null || true
sudo apt install -y -qq python3-pip python3-venv python3-lxml ffmpeg 2>/dev/null || true
sudo usermod -a -G systemd-journal $USER 2>/dev/null || true

echo "[2/8] Virtual env..."
if [ ! -d "${VENV}" ]; then
    python3 -m venv "${VENV}"
fi
source "${VENV}/bin/activate"
python3 -m pip install --upgrade pip -q 2>/dev/null || true

echo "[3/8] Python packages..."
MIRROR="-i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com --default-timeout=120"
echo "  -> Pure Python packages..."
pip install pyserial paho-mqtt pyyaml fastcrc -q $MIRROR 2>/dev/null || pip install pyserial paho-mqtt pyyaml fastcrc
echo "  -> pymavlink (skip lxml, use system apt)..."
pip install pymavlink --no-deps -q $MIRROR 2>/dev/null || pip install pymavlink --no-deps
echo "  -> OK"

echo "[4/8] Directories..."
sudo mkdir -p "${INSTALL_DIR}/data" "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}/snapshots"

echo "[5/8] Copy files..."
sudo cp "${SCRIPT_DIR}/main.py" "${INSTALL_DIR}/"
sudo cp "${SCRIPT_DIR}/config.yaml" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/core" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/modules" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/protocol" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/utils" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/deploy" "${INSTALL_DIR}/" 2>/dev/null || true

echo "[6/8] Config and symlinks..."
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    sudo cp "${INSTALL_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml"
    echo "  -> Created default config"
else
    echo "  -> Config exists, skipping"
fi
sudo rm -f "${INSTALL_DIR}/config.yaml"
sudo ln -sf "${CONFIG_DIR}/config.yaml" "${INSTALL_DIR}/config.yaml"
sudo chmod 644 "${CONFIG_DIR}/config.yaml"
sudo rm -rf "${INSTALL_DIR}/data/logs" 2>/dev/null || true
sudo rm -rf "${INSTALL_DIR}/data/snapshots" 2>/dev/null || true
sudo ln -sf "${LOG_DIR}" "${INSTALL_DIR}/data/logs"
sudo ln -sf "${DATA_DIR}" "${INSTALL_DIR}/data/snapshots"

echo "[7/8] systemd service..."
sudo cp "${SCRIPT_DIR}/deploy/hangar.service" /etc/systemd/system/
sudo sed -i "s|/usr/bin/python3|${VENV}/bin/python3|g" /etc/systemd/system/hangar.service
sudo sed -i "s|/home/kickpi/hangar_venv/bin/python3|${VENV}/bin/python3|g" /etc/systemd/system/hangar.service
sudo systemctl daemon-reload
sudo systemctl enable hangar 2>/dev/null || true

echo "[8/8] CLI command..."
sudo cp "${SCRIPT_DIR}/deploy/hangar-cli.sh" /usr/local/bin/hangar
sudo chmod +x /usr/local/bin/hangar

echo ""
echo "Starting service..."
sudo systemctl stop hangar 2>/dev/null || true
sudo systemctl start hangar 2>/dev/null || true
sleep 3

if systemctl is-active --quiet hangar; then
    echo ""
    echo "====================================="
    echo "  DEPLOY OK"
    echo "  hangar logs   - live output"
    echo "  hangar stop   - stop service"
    echo "  hangar check  - quick status"
    echo "  hangar status - detailed status"
    IP=$(hostname -I | awk '{print $1}')
    echo "  Web: http://$IP:8080"
    echo "====================================="
    echo ""
    echo "=== Live output (Ctrl+C to stop) ==="
    sudo journalctl -u hangar -f --no-pager -n 10

else
    echo ""
    echo "====================================="
    echo "  DEPLOY FAILED - check:"
    echo "  sudo journalctl -u hangar --no-pager -n 20"
    echo "====================================="
    sudo journalctl -u hangar --no-pager -n 15
    exit 1
fi
