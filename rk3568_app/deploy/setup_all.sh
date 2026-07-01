#!/bin/bash
# =============================================
# ANMK8639 一键全自动部署
# 用法: sudo bash deploy/setup_all.sh
# 包含: 网络配置 → go2rtc → hangar安装 → 服务启动
# =============================================
set -e

GREEN='\033[0;32m'
NC='\033[0m'

echo "============================================"
echo "  ANMK8639 Hangar Control System"
echo "  一键全自动部署"
echo "============================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ========== Phase 1: 网络 + 摄像头 ==========
echo -e "${GREEN}[Phase 1/2]${NC} 网络配置 + go2rtc 安装..."
bash "${SCRIPT_DIR}/setup_camera.sh"

# ========== Phase 2: Hangar 安装 ==========
echo ""
echo -e "${GREEN}[Phase 2/2]${NC} Hangar 控制系统安装..."
bash "${SCRIPT_DIR}/install.sh"

# ========== 启动所有服务 ==========
echo ""
echo -e "${GREEN}[Final]${NC} 启动所有服务..."
systemctl restart go2rtc 2>/dev/null || true
systemctl restart hangar 2>/dev/null || true
sleep 2

# ========== 验证 ==========
echo ""
echo "============================================"
echo "  √√√ 全部部署完成 √√√"
echo "============================================"
echo ""

echo "--- 网络 ---"
ip -br addr show eth0 eth1 wlan0 2>/dev/null || true

echo ""
echo "--- 服务状态 ---"
systemctl is-active go2rtc 2>/dev/null && echo "go2rtc:  RUNNING" || echo "go2rtc:  STOPPED"
systemctl is-active hangar 2>/dev/null && echo "hangar:  RUNNING" || echo "hangar:  STOPPED"

echo ""
echo "--- 访问地址 ---"
echo "Web 管理:  http://192.168.2.78:8080"
echo "go2rtc:    http://192.168.2.78:1984"
echo ""

echo "验证命令:"
echo "  hangar status"
echo "  curl http://127.0.0.1:1984/api/streams"
echo "  ping 10.6.3.110"