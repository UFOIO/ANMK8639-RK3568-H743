#!/bin/bash
# =============================================
# ANMK8639 一键全自动部署 (Phase 1 ~ 4)
# 用法: sudo bash deploy/setup_all.sh
# 
# Phase 1: 网络配置 (eth0/eth1/WiFi/IP转发/iptables/watchdog)
# Phase 2: 摄像头配置 (海康 RTSP + 思翼云台)
# Phase 3: Hangar 安装 (Python + systemd)
# Phase 4: Tailscale (子网路由, 跨公网访问)
#
# 前置: /etc/hangar/local.yaml 已填 tailscale_auth_key
#       (否则 Phase 4 会跳过, 可手动重跑)
# =============================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}请用 root 跑: sudo bash $0${NC}"
    exit 1
fi

echo "============================================"
echo "  ANMK8639 Hangar Control System"
echo "  一键全自动部署"
echo "============================================"
echo ""
echo "  本脚本将依次:"
echo "    Phase 1: 网络配置 (eth0/eth1/WiFi)"
echo "    Phase 2: 摄像头 (海康 + 思翼云台)"
echo "    Phase 3: Hangar 安装"
echo "    Phase 4: Tailscale (可选, 需要 auth key)"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ========== Phase 1: 网络 ==========
echo ""
echo -e "${GREEN}[Phase 1/4]${NC} 网络配置..."
bash "${SCRIPT_DIR}/setup_network.sh"

# ========== Phase 2: 摄像头 ==========
echo ""
echo -e "${GREEN}[Phase 2/4]${NC} 摄像头配置..."
bash "${SCRIPT_DIR}/setup_camera.sh"

# ========== Phase 3: Hangar 安装 ==========
echo ""
echo -e "${GREEN}[Phase 3/4]${NC} Hangar 控制系统安装..."
bash "${SCRIPT_DIR}/install.sh"

# ========== Phase 4: Tailscale ==========
echo ""
echo -e "${GREEN}[Phase 4/4]${NC} Tailscale + 子网路由..."
if [ -f /etc/hangar/local.yaml ] && grep -q "tskey-auth-" /etc/hangar/local.yaml 2>/dev/null; then
    bash "${SCRIPT_DIR}/setup_tailscale.sh"
else
    echo -e "${YELLOW}  ⚠ /etc/hangar/local.yaml 还没有 Tailscale auth key${NC}"
    echo "  请先编辑:"
    echo "    sudo nano /etc/hangar/local.yaml"
    echo "  找到 vpn.tailscale_auth_key, 填入真 key"
    echo "  然后跑:"
    echo "    sudo bash deploy/setup_tailscale.sh"
fi

# ========== 启动所有服务 ==========
echo ""
echo -e "${GREEN}[Final]${NC} 启动所有服务..."
systemctl restart go2rtc 2>/dev/null || true
systemctl restart hangar 2>/dev/null || true
sleep 3

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
for svc in go2rtc hangar iptables; do
    if systemctl is-active ${svc} &>/dev/null; then
        echo -e "${svc}: ${GREEN}RUNNING${NC}"
    else
        echo -e "${svc}: ${RED}STOPPED${NC}"
    fi
done

echo ""
echo "--- 访问地址 ---"
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Web 管理:    http://${LOCAL_IP}:8080"
echo "go2rtc:      http://${LOCAL_IP}:1984"
echo "Tailscale:   $(tailscale ip -4 2>/dev/null || echo '未上线')"
echo ""

echo "============================================"
echo "  下一步:"
echo "  1. PC 浏览器打开 http://${LOCAL_IP}:8080"
echo "  2. 默认账号 admin / admin123 (首次登录后改密码)"
echo "  3. 配置 → VPN 板块填 Tailscale auth key (如未填)"
echo "  4. PC 装 Tailscale 加入同一网络, 即可远程访问"
echo "============================================"
