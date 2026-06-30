#!/bin/bash
# ============================================
# ANMK8639 ???????????
# ???dnsmasq DHCP + go2rtc ?????
# ???sudo bash deploy/setup_camera.sh
# ============================================
set -e

echo "=== ANMK8639 ??????? ==="

# ---------- 1. ?? eth1 ?? IP ----------
echo "[1/5] ?? eth1 ?? IP (10.6.3.1/24)..."
if ! grep -q "10.6.3.1" /etc/rc.local 2>/dev/null; then
    echo "ip addr add 10.6.3.1/24 dev eth1" >> /etc/rc.local
fi
ip addr add 10.6.3.1/24 dev eth1 2>/dev/null || true

# ---------- 2. ????? dnsmasq (DHCP for eth1) ----------
echo "[2/5] ?? dnsmasq DHCP ???..."
if ! command -v dnsmasq &>/dev/null; then
    apt-get update -qq && apt-get install -y dnsmasq
fi

# ?? systemd-resolved (??53??)
systemctl stop systemd-resolved 2>/dev/null || true
systemctl disable systemd-resolved 2>/dev/null || true
echo "nameserver 8.8.8.8" > /etc/resolv.conf

cat > /etc/dnsmasq.conf << 'DNSEOF'
interface=eth1
bind-interfaces
dhcp-range=10.6.3.100,10.6.3.200,12h
port=0
DNSEOF

systemctl daemon-reload
systemctl restart dnsmasq
systemctl enable dnsmasq

# ---------- 3. ?? go2rtc ----------
echo "[3/5] ?? go2rtc..."
if [ -f "/home/kickpi/rk3568_app/go2rtc_linux_arm64" ]; then
    cp /home/kickpi/rk3568_app/go2rtc_linux_arm64 /usr/local/bin/go2rtc
    chmod +x /usr/local/bin/go2rtc
elif [ ! -f "/usr/local/bin/go2rtc" ]; then
    echo "???? go2rtc_linux_arm64 ??? /usr/local/bin/go2rtc"
fi

# ---------- 4. ?? go2rtc ?? ----------
echo "[4/5] ?? go2rtc ??..."
mkdir -p /etc/hangar
cat > /etc/hangar/go2rtc.yaml << 'G2EOF'
streams:
  camera: rtsp://10.6.3.110:554/user=admin&password=&channel=1&stream=0.sdp?
G2EOF

# ---------- 5. ????? systemd ?? ----------
echo "[5/5] ?? go2rtc systemd ??..."
cp /home/kickpi/rk3568_app/deploy/go2rtc.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable go2rtc
systemctl restart go2rtc

echo ""
echo "=== ????! ==="
echo "??? DHCP ??: 10.6.3.100 - 10.6.3.200"
echo "go2rtc API:       http://$(hostname -I | awk '{print $1}'):1984"
echo "MJPEG ?:         http://$(hostname -I | awk '{print $1}'):1984/api/stream.mjpeg?src=camera"
echo "MSE ?:           http://$(hostname -I | awk '{print $1}'):1984/api/stream?src=camera"
echo "WebRTC:           http://$(hostname -I | awk '{print $1}'):1984/webrtc?src=camera"
echo ""
echo "????? IP ???? /etc/hangar/go2rtc.yaml ?? RTSP URL"
echo "?? systemctl restart go2rtc"