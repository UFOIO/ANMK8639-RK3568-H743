#!/bin/bash
# =============================================
# ANMK8639 Tailscale + 子网路由 配置脚本
# 用法: sudo bash deploy/setup_tailscale.sh
# 职责:
#   1. 安装 Tailscale
#   2. 用 /etc/hangar/local.yaml 里的 authkey 加入网络
#   3. 广播 192.168.144.0/24 让客户 PC 自动学到
#   4. 持久化配置
# 前提:
#   - /etc/hangar/local.yaml 已填 tailscale_auth_key
#   - 网络已通 (Phase 1 完成)
# =============================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 从 local.yaml 读 (可被环境变量覆盖)
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
GIMBAL_SUBNET="$(_yaml_get network.gimbal_subnet "192.168.144.0/24")"
ACCEPT_DNS="$(_yaml_get vpn.accept_dns "false")"

if [ "$(id -u)" -ne 0 ]; then
    echo "请用 root 跑: sudo bash $0"
    exit 1
fi

# ---------- 0. 检查前置条件 ----------
if [ ! -f /etc/hangar/local.yaml ]; then
    echo -e "${RED}✗ /etc/hangar/local.yaml 不存在${NC}"
    echo "  请先跑 deploy/install.sh 完成 Hangar 安装"
    exit 1
fi

AUTHKEY=$(grep -E "^\s*tailscale_auth_key:" /etc/hangar/local.yaml | head -1 | sed 's/.*tailscale_auth_key:\s*//' | tr -d '"' | tr -d "'" | xargs)

if [ -z "${AUTHKEY}" ] || [ "${AUTHKEY}" = "tskey-auth-xxxxx" ] || [[ "${AUTHKEY}" != tskey-auth-* ]]; then
    echo -e "${RED}✗ /etc/hangar/local.yaml 里的 tailscale_auth_key 无效${NC}"
    echo "  当前值: ${AUTHKEY}"
    echo ""
    echo "  请去 https://login.tailscale.com/admin/settings/keys 生成 Reusable + Pre-approved key"
    echo "  然后写入 /etc/hangar/local.yaml:"
    echo "    vpn:"
    echo "      tailscale_auth_key: \"tskey-auth-你的真key\""
    exit 1
fi

echo "============================================"
echo "  ANMK8639 Tailscale 配置"
echo "============================================"
echo "  Auth Key: ${AUTHKEY:0:20}...${AUTHKEY: -10}"
echo "  广播子网: ${GIMBAL_SUBNET}"
echo ""

# ---------- 1. 安装 Tailscale ----------
echo -e "${GREEN}[1/4]${NC} 安装 Tailscale..."

if ! command -v tailscale &>/dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "  -> Tailscale 已安装, 跳过"
fi

# ---------- 2. IP forwarding (子网路由前置) ----------
echo ""
echo -e "${GREEN}[2/4]${NC} 确保 IP forwarding 开启..."

if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.d/99-ip-forward.conf 2>/dev/null; then
    echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-ip-forward.conf
fi
sysctl -p /etc/sysctl.d/99-ip-forward.conf

ACTUAL=$(cat /proc/sys/net/ipv4/ip_forward)
echo "  ✓ ip_forward = ${ACTUAL}"

# ---------- 3. 加入网络 + 广播子网 ----------
echo ""
echo -e "${GREEN}[3/4]${NC} 加入 Tailscale 网络..."

# 先 logout 清干净旧状态
tailscale logout 2>/dev/null || true
systemctl restart tailscaled
sleep 3

# 关键: --advertise-routes 让 RK3568 当 subnet router
tailscale up \
    --authkey="${AUTHKEY}" \
    --advertise-routes=${GIMBAL_SUBNET} \
    --accept-dns=${ACCEPT_DNS}

sleep 8
STATUS=$(tailscale status 2>&1)

if echo "${STATUS}" | grep -q "subnet router"; then
    echo "  ✓ 子网路由已广播"
elif echo "${STATUS}" | grep -q "active"; then
    echo -e "${YELLOW}  ⚠ 已上线但 subnet router 未生效${NC}"
    echo "  可能需要去 https://login.tailscale.com/admin/machines 批准子网"
else
    echo -e "${RED}  ✗ Tailscale 上线失败${NC}"
    echo "  查看日志: journalctl -u tailscaled -n 20"
    exit 1
fi

# ---------- 4. 防火墙允许 Tailscale 转发 ----------
echo ""
echo -e "${GREEN}[4/4]${NC} 确保 iptables 允许 Tailscale 流量..."

# Tailscale 自身的 ts-forward 链会自动注入规则
# 但确保 FORWARD 链默认 ACCEPT
iptables -P FORWARD ACCEPT 2>/dev/null || true

netfilter-persistent save 2>/dev/null || true

# ---------- 输出 ----------
echo ""
echo "============================================"
echo "  ✓✓✓ Tailscale 配置完成 ✓✓✓"
echo "============================================"
echo ""
tailscale status

echo ""
echo -e "${YELLOW}重要: 首次配置需要在后台批准子网${NC}"
echo "  1. 浏览器打开: https://login.tailscale.com/admin/machines"
echo "  2. 找到 kickpi 设备"
echo "  3. 在 Subnets 区块点 Approve 批准 ${GIMBAL_SUBNET}"
echo ""
echo "批准后, 任何加入 Tailscale 网络的设备都能:"
echo "  - 直接 ping 192.168.144.25"
echo "  - 浏览器访问 http://192.168.144.25:82/..."
echo "  - 用 SIYI 官方 GCS 连 192.168.144.25:37260 (UDP)"
