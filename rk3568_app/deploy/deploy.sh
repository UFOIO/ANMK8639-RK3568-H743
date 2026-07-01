#!/bin/bash
# =============================================
# 一键部署代码到 RK3568 (PC 端运行)
# 用法: ./deploy.sh <RK3568_IP> [用户名]
# 示例: ./deploy.sh 192.168.2.78 kickpi
# =============================================

IP="${1:-192.168.2.78}"
USER="${2:-kickpi}"
APP_DIR="/home/kickpi/rk3568_app"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "$1" ]; then
    echo "用法: $0 <RK3568_IP> [用户名]"
    echo "示例: $0 192.168.2.78 kickpi"
    exit 1
fi

echo "=== 部署到 ${USER}@${IP}:${APP_DIR} ==="

echo "[1/4] 同步代码..."
rsync -avz --delete \
    --exclude "data/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude "venv/" \
    "${SRC_DIR}/" "${USER}@${IP}:${APP_DIR}/"

echo "[2/4] 安装 Python 依赖..."
ssh ${USER}@${IP} "cd ${APP_DIR} && source hangar_venv/bin/activate 2>/dev/null && pip install -q -r requirements.txt"

echo "[3/4] 同步 systemd 服务..."
ssh ${USER}@${IP} "sudo cp ${APP_DIR}/deploy/hangar.service /etc/systemd/system/ && sudo systemctl daemon-reload"

echo "[4/4] 重启服务..."
ssh ${USER}@${IP} "sudo systemctl restart hangar && sudo systemctl status hangar --no-pager | head -10"

echo ""
echo "=== 部署完成 ==="
echo "查看日志: ssh ${USER}@${IP} 'journalctl -u hangar -f'"
echo "Web UI:   http://${IP}:8080"
