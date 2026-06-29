#!/bin/bash
# ===========================================
# ANMK8639 Hangar Control — 一键全自动部署
# 适用: 空白 RK3568 (Ubuntu 20.04 arm64)
# 用法: sudo bash setup.sh
# ===========================================
set -e

APP=hangar
INSTALL_DIR=/opt/hangar
CONFIG_DIR=/etc/hangar
LOG_DIR=/var/log/hangar
DATA_DIR=/var/lib/hangar
VENV=/home/kickpi/hangar_venv
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo " ANMK8639 Hangar Control Deploy"
echo "=========================================="
echo ""

# ===== [1/10] System Deps =====
echo "[1/10] System dependencies..."
sudo apt update -qq 2>/dev/null || true
sudo apt install -y -qq python3-pip python3-venv python3-lxml ffmpeg mosquitto mosquitto-clients 2>/dev/null || true
sudo usermod -a -G systemd-journal $USER 2>/dev/null || true
echo -e "  ${GREEN}OK${NC}"

# ===== [2/10] Tailscale VPN =====
echo "[2/10] Tailscale VPN..."
if ! command -v tailscale &> /dev/null; then
    echo "  Installing Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh 2>/dev/null || {
        echo -e "  ${YELLOW}Tailscale install skipped (no internet?)${NC}"
    }
fi
if command -v tailscale &> /dev/null; then
    if tailscale status 2>/dev/null | grep -q "Logged out"; then
        echo ""
        echo -e "  ${YELLOW}>> Tailscale 未登录。${NC}"
        echo "  1. 浏览器打开 https://login.tailscale.com 注册账号"
        echo "  2. Settings → Keys → Generate Auth Key → 复制 key"
        echo "  3. 粘贴到下面（留空跳过）："
        read -p "  Tailscale Auth Key (留空跳过): " AUTH_KEY
        if [ -n "$AUTH_KEY" ]; then
            sudo tailscale up --auth-key="$AUTH_KEY" 2>/dev/null && echo -e "  ${GREEN}Tailscale OK${NC}" || echo -e "  ${YELLOW}Tailscale login failed${NC}"
        fi
    else
        echo -e "  ${GREEN}Tailscale already active${NC}"
    fi
else
    echo -e "  ${YELLOW}Tailscale not available${NC}"
fi

# ===== [3/10] Mosquitto Config =====
echo "[3/10] Mosquitto MQTT Broker..."
if command -v mosquitto &> /dev/null; then
    # Create password file
    if [ ! -f /etc/mosquitto/passwd ]; then
        echo "  Creating Mosquitto user 'hangar'..."
        read -sp "  Enter MQTT password for 'hangar': " MQ_PW
        echo ""
        if [ -n "$MQ_PW" ]; then
            echo "$MQ_PW" | sudo tee /tmp/mq_pw > /dev/null
            echo "$MQ_PW" | sudo tee -a /tmp/mq_pw > /dev/null
            sudo mosquitto_passwd -c /etc/mosquitto/passwd hangar < /tmp/mq_pw 2>/dev/null || {
                # Fallback for older mosquitto versions
                sudo touch /etc/mosquitto/passwd
                sudo mosquitto_passwd -b /etc/mosquitto/passwd hangar "$MQ_PW" 2>/dev/null || true
            }
            sudo rm -f /tmp/mq_pw
            echo -e "  ${GREEN}Mosquitto user created${NC}"
        fi
    else
        echo "  Mosquitto password file exists, skipping"
    fi

    # Apply hangar config
    if [ -f "${SCRIPT_DIR}/deploy/mosquitto-hangar.conf" ]; then
        sudo cp "${SCRIPT_DIR}/deploy/mosquitto-hangar.conf" /etc/mosquitto/conf.d/hangar.conf
        sudo systemctl restart mosquitto 2>/dev/null || true
        sudo systemctl enable mosquitto 2>/dev/null || true
        echo -e "  ${GREEN}Mosquitto configured${NC}"
    fi
else
    echo -e "  ${YELLOW}Mosquitto not found${NC}"
fi

# ===== [4/10] Virtual Env =====
echo "[4/10] Python virtual env..."
if [ ! -d "${VENV}" ]; then
    python3 -m venv "${VENV}"
fi
source "${VENV}/bin/activate"
python3 -m pip install --upgrade pip -q 2>/dev/null || true
echo -e "  ${GREEN}OK${NC}"

# ===== [5/10] Python Packages =====
echo "[5/10] Python packages..."
MIRROR="-i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com --default-timeout=120"
pip install pyserial paho-mqtt pyyaml fastcrc -q $MIRROR 2>/dev/null || pip install pyserial paho-mqtt pyyaml fastcrc
pip install pymavlink --no-deps -q $MIRROR 2>/dev/null || pip install pymavlink --no-deps
echo -e "  ${GREEN}OK${NC}"

# ===== [6/10] Directories =====
echo "[6/10] Creating directories..."
sudo mkdir -p "${INSTALL_DIR}/data" "${CONFIG_DIR}" "${LOG_DIR}" "${DATA_DIR}/snapshots"
sudo mkdir -p /var/lib/mosquitto 2>/dev/null || true
echo -e "  ${GREEN}OK${NC}"

# ===== [7/10] Copy Files =====
echo "[7/10] Copying files..."
sudo cp "${SCRIPT_DIR}/main.py" "${INSTALL_DIR}/"
sudo cp "${SCRIPT_DIR}/config.yaml" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/core" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/modules" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/protocol" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/utils" "${INSTALL_DIR}/"
sudo cp -r "${SCRIPT_DIR}/deploy" "${INSTALL_DIR}/" 2>/dev/null || true
echo -e "  ${GREEN}OK${NC}"

# ===== [8/10] Config & Symlinks =====
echo "[8/10] Configuration..."
if [ ! -f "${CONFIG_DIR}/config.yaml" ]; then
    sudo cp "${INSTALL_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml"
else
    echo "  Config exists, keeping existing"
fi
sudo rm -f "${INSTALL_DIR}/config.yaml"
sudo ln -sf "${CONFIG_DIR}/config.yaml" "${INSTALL_DIR}/config.yaml"
sudo chmod 644 "${CONFIG_DIR}/config.yaml"

# Protect local.yaml (user config, never overwritten)
touch "${CONFIG_DIR}/local.yaml" 2>/dev/null || true
sudo chmod 644 "${CONFIG_DIR}/local.yaml" 2>/dev/null || true

# Symlink logs & data
sudo rm -rf "${INSTALL_DIR}/data/logs" 2>/dev/null || true
sudo rm -rf "${INSTALL_DIR}/data/snapshots" 2>/dev/null || true
sudo ln -sf "${LOG_DIR}" "${INSTALL_DIR}/data/logs"
sudo ln -sf "${DATA_DIR}" "${INSTALL_DIR}/data/snapshots"

# Set MQTT password in config if provided
if [ -n "$MQ_PW" ]; then
    if command -v python3 &> /dev/null; then
        sudo python3 -c "
import yaml
with open('${CONFIG_DIR}/local.yaml', 'r') as f:
    c = yaml.safe_load(f) or {}
if 'mqtt' not in c: c['mqtt'] = {}
c['mqtt']['password'] = '$MQ_PW'
c['mqtt']['enabled'] = True
c['mqtt']['broker'] = '127.0.0.1'
with open('${CONFIG_DIR}/local.yaml', 'w') as f:
    yaml.safe_dump(c, f, allow_unicode=True)
" 2>/dev/null || true
    fi
fi

echo -e "  ${GREEN}OK${NC}"

# ===== [9/10] systemd Service =====
echo "[9/10] Installing systemd service..."
sudo cp "${SCRIPT_DIR}/deploy/hangar.service" /etc/systemd/system/
sudo sed -i "s|/usr/bin/python3|${VENV}/bin/python3|g" /etc/systemd/system/hangar.service
sudo sed -i "s|/home/kickpi/hangar_venv/bin/python3|${VENV}/bin/python3|g" /etc/systemd/system/hangar.service
sudo systemctl daemon-reload
sudo systemctl enable hangar 2>/dev/null || true
echo -e "  ${GREEN}OK${NC}"

# ===== [10/10] CLI Command =====
echo "[10/10] Installing CLI..."
sudo cp "${SCRIPT_DIR}/deploy/hangar-cli.sh" /usr/local/bin/hangar
sudo chmod +x /usr/local/bin/hangar
echo -e "  ${GREEN}OK${NC}"

# ===== Start =====
echo ""
echo "Starting services..."
sudo systemctl restart mosquitto 2>/dev/null || true
sudo systemctl stop hangar 2>/dev/null || true
sudo systemctl start hangar 2>/dev/null || true
sleep 3

IP=$(hostname -I | awk '{print $1}')
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "未配置")

echo ""
echo "========================================="
echo "  ${GREEN}DEPLOY COMPLETE${NC}"
echo "========================================="
echo ""
echo "  WebUI  (局域网):  http://$IP:8080"
if [ "$TAILSCALE_IP" != "未配置" ]; then
    echo "  WebUI  (远程):    http://$TAILSCALE_IP:8080"
fi
echo "  MQTT   (局域网):  $IP:1883"
if [ "$TAILSCALE_IP" != "未配置" ]; then
    echo "  MQTT   (远程):    $TAILSCALE_IP:1883"
fi
echo ""
echo "  命令: hangar start|stop|restart|logs|check|status|config"
echo "  默认登录: admin / admin123"
if [ -n "$MQ_PW" ]; then
    echo "  MQTT 用户: hangar / $MQ_PW"
fi
echo ""
echo "========================================="
echo ""

# Show live output if service running
if systemctl is-active --quiet hangar; then
    echo "=== Live output (Ctrl+C to stop) ==="
    sudo journalctl -u hangar -f --no-pager -n 10
else
    echo -e "${RED}Service failed to start. Check:${NC}"
    echo "  sudo journalctl -u hangar --no-pager -n 20"
    sudo journalctl -u hangar --no-pager -n 15
    exit 1
fi
