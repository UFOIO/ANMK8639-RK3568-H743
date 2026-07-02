#!/bin/bash
# =============================================
# ANMK8639 摄像头 + 云台 配置脚本
# 用法: sudo bash deploy/setup_camera.sh
# 职责:
#   1. eth1 静态 IP (海康 RTSP 摄像头)
#   2. dnsmasq DHCP 给摄像头
#   3. 安装 go2rtc + RTSP 转 WebRTC/MSE
#   4. 配置 gimbal_camera 段 (云台相机)
# =============================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ---------- 从 /etc/hangar/local.yaml 读配置 (若读失败用默认值) ----------
_yaml_get() {
    local key="$1" default="$2"
    python3 -c "
import sys, yaml
try:
    cfg = yaml.safe_load(open('/etc/hangar/local.yaml'))
    v = cfg
    for k in '$key'.split('.'):
        v = v.get(k) if isinstance(v, dict) else None
        if v is None: break
    print(v if v is not None else '$default')
except Exception:
    print('$default')
" 2>/dev/null
}

# ---------- 默认值 (可在 /etc/hangar/local.yaml 覆盖) ----------
ETH1_IP="10.6.3.1/24"
DHCP_RANGE_START="10.6.3.100"
DHCP_RANGE_END="10.6.3.200"

# 海康摄像头 RTSP (默认)
HIKVISION_IP="$(_yaml_get camera.ip "10.6.3.110")"
HIKVISION_PORT="$(_yaml_get camera.port "554")"
HIKVISION_USER="$(_yaml_get camera.username "admin")"
HIKVISION_PASS="$(_yaml_get camera.password "")"
HIKVISION_CHANNEL="$(_yaml_get camera.channel "1")"
HIKVISION_STREAM="$(_yaml_get camera.stream "0")"

# 思翼云台 (4G模块 WiFi 网段)
GIMBAL_IP="$(_yaml_get gimbal_camera.host "192.168.144.25")"
GIMBAL_WEB_PORT="$(_yaml_get gimbal_camera.web_port "82")"
GIMBAL_PROXY_PORT=8080  # 整合进 hangar web_ui 主端口

if [ "$(id -u)" -ne 0 ]; then
    echo "请用 root 跑: sudo bash $0"
    exit 1
fi

echo "============================================"
echo "  ANMK8639 摄像头配置"
echo "============================================"

# ========== Step 1: eth1 静态 IP ==========
echo ""
echo -e "${GREEN}[1/5]${NC} 配置 eth1 静态 IP ${ETH1_IP}..."

cat > /etc/netplan/01-eth1-camera.yaml << EOF
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    eth1:
      dhcp4: no
      addresses:
        - ${ETH1_IP}
EOF

netplan apply
ip addr add ${ETH1_IP} dev eth1 2>/dev/null || true
sleep 1
echo "  ✓ eth1 = $(ip -4 addr show eth1 | grep inet | awk '{print $2}')"

# ========== Step 2: dnsmasq (DHCP for eth1) ==========
echo ""
echo -e "${GREEN}[2/5]${NC} 配置 dnsmasq DHCP (给摄像头自动分IP)..."

if ! command -v dnsmasq &>/dev/null; then
    apt-get update -qq && apt-get install -y dnsmasq >/dev/null
fi

cat > /etc/dnsmasq.conf << EOF
interface=eth1
bind-interfaces
dhcp-range=${DHCP_RANGE_START},${DHCP_RANGE_END},12h
port=0
EOF

systemctl stop systemd-resolved 2>/dev/null || true
systemctl disable systemd-resolved 2>/dev/null || true
echo "nameserver 8.8.8.8" > /etc/resolv.conf

systemctl daemon-reload
systemctl restart dnsmasq
systemctl enable dnsmasq
echo "  ✓ DHCP: ${DHCP_RANGE_START} - ${DHCP_RANGE_END}"

# ========== Step 3: go2rtc 安装 ==========
echo ""
echo -e "${GREEN}[3/5]${NC} 安装 go2rtc..."

if [ ! -f "/usr/local/bin/go2rtc" ]; then
    if [ -f "/home/kickpi/rk3568_app/go2rtc_linux_arm64" ]; then
        cp /home/kickpi/rk3568_app/go2rtc_linux_arm64 /usr/local/bin/go2rtc
        chmod +x /usr/local/bin/go2rtc
        echo "  -> 复制本地 go2rtc_linux_arm64"
    else
        echo -e "${YELLOW}  ⚠ 找不到 go2rtc 二进制${NC}"
        echo "  请把 go2rtc_linux_arm64 放到 /home/kickpi/rk3568_app/ 目录"
    fi
fi

# ========== Step 4: go2rtc 配置 ==========
echo ""
echo -e "${GREEN}[4/5]${NC} 配置 go2rtc..."

mkdir -p /etc/hangar
RTSP_URL="rtsp://${HIKVISION_IP}:${HIKVISION_PORT}/user=${HIKVISION_USER}&password=${HIKVISION_PASS}&channel=${HIKVISION_CHANNEL}&stream=${HIKVISION_STREAM}.sdp?"

GIMBAL_RTSP_URL="${GIMBAL_RTSP_URL:-rtsp://${GIMBAL_IP}:8554/main.264}"
cat > /etc/hangar/go2rtc.yaml << EOF
api:
  origin: "*"
rtsp:
  host: 0.0.0.0
streams:
  camera: "exec:ffmpeg -rtsp_transport tcp -i ${RTSP_URL} -c copy -an -f mpegts pipe:1"
  gimbal: "${GIMBAL_RTSP_URL}"
EOF

cp /home/kickpi/rk3568_app/deploy/go2rtc.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable go2rtc
systemctl restart go2rtc
echo "  ✓ go2rtc 监听 :1984"

# ========== Step 5: gimbal_camera 段写入 config.yaml ==========
echo ""
echo -e "${GREEN}[5/5]${NC} 配置 gimbal_camera 段..."

mkdir -p /etc/hangar

if ! grep -q "^gimbal_camera:" /etc/hangar/config.yaml 2>/dev/null; then
    cat >> /etc/hangar/config.yaml << EOF

# ===== 云台相机 (思翼, 通过 4G模块WiFi) =====
gimbal_camera:
  enabled: true                 # 启用云台存储代理
  host: "${GIMBAL_IP}"          # 云台内网 IP
  web_port: ${GIMBAL_WEB_PORT}  # Web Server 端口
  wifi_ssid: "H4T_4G"          # 4G模块 WiFi SSID
  wifi_password: "88888888"     # 4G模块 WiFi 密码
EOF
    echo "  ✓ gimbal_camera 段已添加"
else
    echo "  -> gimbal_camera 段已存在"
fi

# ========== 输出 ==========
echo ""
echo "============================================"
echo "  ✓✓✓ 摄像头配置完成 ✓✓✓"
echo "============================================"
echo ""
echo "--- 摄像头状态 ---"
echo "海康 RTSP:    rtsp://${HIKVISION_IP}:${HIKVISION_PORT}/..."
echo "go2rtc Web:   http://$(hostname -I | awk '{print $1}'):1984"
echo "云台 API:     http://${GIMBAL_IP}:${GIMBAL_WEB_PORT}/cgi-bin/media.cgi"
echo "云台代理:     http://$(hostname -I | awk '{print $1}'):${GIMBAL_PROXY_PORT}/camera"
echo "            (需先连上 4G模块 WiFi H4T_4G)"
