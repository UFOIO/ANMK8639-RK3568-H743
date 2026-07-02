#!/bin/bash
# =============================================
# ANMK8639 网络配置脚本
# 用法: sudo bash deploy/setup_network.sh
# 职责:
#   1. eth0 静态 IP 192.168.2.78
#   2. eth1 静态 IP 10.6.3.1/24 (对接海康摄像头)
#   3. wlan0 连 H4T_4G (4G模块WiFi, 访问云台)
#   4. wlan0 never-default + autoconnect priority
#   5. IP forwarding 永久开启
#   6. iptables FORWARD 规则 + 持久化
#   7. wifi-watchdog (飞机回来时自动重连)
#   8. wifi-autoconnect (开机自动连)
# =============================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# ---------- 从 /etc/hangar/local.yaml 读配置 (若读失败用默认值) ----------
_yaml_get() {
    # 用法: _yaml_get <section.key> <default>
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

# ---------- 配置参数 (来自 local.yaml, 也可手动覆盖 export) ----------
ETH0_IP="$(_yaml_get network.eth0_ip "192.168.2.78/24")"
ETH0_GW="$(_yaml_get network.eth0_gw "192.168.2.1")"
ETH0_DNS=("114.114.114.114" "8.8.8.8")

ETH1_IP="$(_yaml_get network.eth1_ip "10.6.3.1/24")"

WIFI_SSID="$(_yaml_get network.wifi_ssid "H4T_4G")"
WIFI_PASS="$(_yaml_get network.wifi_password "88888888")"

GIMBAL_SUBNET="$(_yaml_get network.gimbal_subnet "192.168.144.0/24")"
HOME_SUBNET="192.168.2.0/24"

if [ "$(id -u)" -ne 0 ]; then
    echo "请用 root 跑: sudo bash $0"
    exit 1
fi

echo "============================================"
echo "  ANMK8639 网络配置"
echo "============================================"

# ========== Step 1: eth0 静态 IP (netplan + NM) ==========
echo ""
echo -e "${GREEN}[1/8]${NC} 配置 eth0 静态 IP ${ETH0_IP}..."

cat > /etc/netplan/00-eth0-dhcp.yaml << EOF
network:
  version: 2
  renderer: NetworkManager
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - ${ETH0_IP}
      routes:
        - to: default
          via: ${ETH0_GW}
      nameservers:
        addresses:
          - ${ETH0_DNS[0]}
          - ${ETH0_DNS[1]}
EOF

# 同步到 NetworkManager connection profile
nmcli connection modify "netplan-eth0" \
    ipv4.method manual \
    ipv4.addresses ${ETH0_IP} \
    ipv4.gateway ${ETH0_GW} \
    ipv4.dns "${ETH0_DNS[*]}" \
    connection.autoconnect yes \
    connection.autoconnect-priority 10 2>/dev/null || true

netplan apply
sleep 2
echo "  ✓ eth0 = $(ip -4 addr show eth0 | grep inet | awk '{print $2}')"

# ========== Step 2: eth1 静态 IP (摄像头) ==========
echo ""
echo -e "${GREEN}[2/8]${NC} 配置 eth1 静态 IP ${ETH1_IP}..."

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

nmcli connection modify "netplan-eth1" \
    ipv4.method manual \
    ipv4.addresses ${ETH1_IP} \
    ipv4.never-default yes \
    connection.autoconnect yes 2>/dev/null || true

netplan apply
sleep 1
ip addr add ${ETH1_IP} dev eth1 2>/dev/null || true
echo "  ✓ eth1 = $(ip -4 addr show eth1 | grep inet | awk '{print $2}')"

# ========== Step 3: WiFi H4T_4G 连接 ==========
echo ""
echo -e "${GREEN}[3/8]${NC} 连接 WiFi ${WIFI_SSID}..."

# 先解 WiFi 软阻塞 (开机后常见状态)
rfkill unblock wifi 2>/dev/null || true
ip link set wlan0 up 2>/dev/null || true
sleep 2

# 检查是否已经有同名 connection
if nmcli -t -f NAME connection show | grep -qx "${WIFI_SSID}"; then
    echo "  -> 连接配置已存在, 复用"
else
    nmcli device wifi connect "${WIFI_SSID}" password "${WIFI_PASS}" 2>/dev/null || \
    nmcli connection add type wifi ifname wlan0 mode infrastructure ssid "${WIFI_SSID}" \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "${WIFI_PASS}"
fi

# 显式存密码 (避免 desktop keyring 问题)
nmcli connection modify "${WIFI_SSID}" \
    wifi-sec.psk "${WIFI_PASS}" \
    wifi-sec.psk-flags 0 \
    ipv4.never-default yes \
    ipv4.method auto \
    connection.autoconnect yes \
    connection.autoconnect-priority 100

nmcli connection up "${WIFI_SSID}" 2>/dev/null || true
sleep 3

WIFI_IP=$(ip -4 addr show wlan0 | grep inet | awk '{print $2}')
if [ -n "${WIFI_IP}" ]; then
    echo "  ✓ wlan0 = ${WIFI_IP} (连上 ${WIFI_SSID})"
else
    echo -e "${YELLOW}  ⚠ wlan0 未拿到 IP (4G模块可能未上电, 重启后再试)${NC}"
fi

# ========== Step 4: 禁用其他 WiFi 自动连接 ==========
echo ""
echo -e "${GREEN}[4/8]${NC} 禁用家庭网/其他WiFi自动连接..."

for ssid in $(nmcli -t -f NAME,TYPE connection show | grep ':802-11-wireless$' | cut -d: -f1); do
    if [ "${ssid}" != "${WIFI_SSID}" ]; then
        nmcli connection modify "${ssid}" connection.autoconnect no 2>/dev/null || true
        echo "  -> ${ssid}: autoconnect=off"
    fi
done

# ========== Step 5: 永久 IP forwarding ==========
echo ""
echo -e "${GREEN}[5/8]${NC} 开启 IP forwarding..."

cat > /etc/sysctl.d/99-ip-forward.conf << 'EOF'
net.ipv4.ip_forward=1
EOF
sysctl -p /etc/sysctl.d/99-ip-forward.conf

ACTUAL=$(cat /proc/sys/net/ipv4/ip_forward)
echo "  ✓ ip_forward = ${ACTUAL}"

# ========== Step 6: iptables FORWARD + 持久化 ==========
echo ""
echo -e "${GREEN}[6/8]${NC} 配置 iptables FORWARD..."

# 默认 FORWARD ACCEPT (透明桥场景)
iptables -P FORWARD ACCEPT

# 加针对云台子网的规则 (允许双向)
iptables -C FORWARD -i eth0 -o wlan0 -s ${HOME_SUBNET} -d ${GIMBAL_SUBNET} -j ACCEPT 2>/dev/null || \
iptables -A FORWARD -i eth0 -o wlan0 -s ${HOME_SUBNET} -d ${GIMBAL_SUBNET} -j ACCEPT

iptables -C FORWARD -i wlan0 -o eth0 -s ${GIMBAL_SUBNET} -d ${HOME_SUBNET} -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
iptables -A FORWARD -i wlan0 -o eth0 -s ${GIMBAL_SUBNET} -d ${HOME_SUBNET} -m state --state ESTABLISHED,RELATED -j ACCEPT

# 装持久化工具
if ! command -v netfilter-persistent &>/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt install -y iptables-persistent >/dev/null 2>&1 || true
fi
netfilter-persistent save 2>/dev/null || true

echo "  ✓ FORWARD 规则已生效并持久化"

# ========== Step 7: wifi-autoconnect (开机首次连接) ==========
echo ""
echo -e "${GREEN}[7/8]${NC} 安装 wifi-autoconnect 服务 (开机30秒后首次连接)..."

cat > /etc/systemd/system/wifi-autoconnect.service << EOF
[Unit]
Description=Auto-connect ${WIFI_SSID} WiFi after boot
After=NetworkManager.service NetworkManager-wait-online.service
Wants=NetworkManager-wait-online.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 30
ExecStart=/usr/bin/nmcli connection up "${WIFI_SSID}"
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wifi-autoconnect.service >/dev/null 2>&1
echo "  ✓ wifi-autoconnect 服务已启用"

# ========== Step 8: wifi-watchdog (保活重连) ==========
echo ""
echo -e "${GREEN}[8/8]${NC} 安装 wifi-watchdog 服务 (飞机回来自动重连)..."

cat > /etc/systemd/system/wifi-watchdog.service << EOF
[Unit]
Description=WiFi reconnect watchdog for ${WIFI_SSID}
After=NetworkManager.service

[Service]
Type=simple
Restart=always
RestartSec=30
ExecStart=/bin/bash -c "while true; do if ! nmcli -t -f NAME,STATE connection show --active | grep -q ${WIFI_SSID}:activated; then nmcli connection up ${WIFI_SSID} >/dev/null 2>&1; fi; sleep 60; done"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wifi-watchdog.service >/dev/null 2>&1
systemctl start wifi-watchdog.service >/dev/null 2>&1
echo "  ✓ wifi-watchdog 服务已启用"

# ========== 验证 ==========
echo ""
echo "============================================"
echo "  ✓✓✓ 网络配置完成 ✓✓✓"
echo "============================================"
echo ""
echo "--- 当前状态 ---"
ip -br addr show eth0 wlan0 2>/dev/null || true
nmcli device status | grep -E "eth0|wlan0"
echo ""
echo "--- 验证命令 ---"
echo "  ping 192.168.144.25    # 云台"
echo "  ping baidu.com         # 公网"
echo "  rfkill list            # WiFi 软阻塞状态"
