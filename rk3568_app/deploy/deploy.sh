#!/bin/bash
# 一键部署到 RK3568
# 用法: ./deploy.sh <RK3568_IP>

IP="${1:-192.168.1.100}"
USER="kickpi"
APP_DIR="/home/kickpi/rk3568_app"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploying to ${USER}@${IP}:${APP_DIR} ==="

echo "[1/4] Syncing code..."
rsync -avz --delete --exclude "data/" --exclude "__pycache__/" --exclude "*.pyc" "${SRC_DIR}/" "${USER}@${IP}:${APP_DIR}/"

echo "[2/4] Installing dependencies..."
ssh ${USER}@${IP} "cd ${APP_DIR} && pip3 install -r requirements.txt --quiet"

echo "[3/4] Installing systemd service..."
ssh ${USER}@${IP} "cp ${APP_DIR}/deploy/hangar.service /etc/systemd/system/ && systemctl daemon-reload"

echo "[4/4] Restarting service..."
ssh ${USER}@${IP} "systemctl restart hangar && systemctl status hangar --no-pager"

echo "=== Deploy complete ==="
echo "View logs: ssh ${USER}@${IP} 'journalctl -u hangar -f'"
