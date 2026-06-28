#!/bin/bash
# ANMK8639 Hangar CLI
APP="hangar"
PORT=8080
IP=$(hostname -I 2>/dev/null)
IP=${IP%% *}
WEB="http://${IP:-127.0.0.1}:${PORT}"

case "${1:-help}" in
    start)   sudo systemctl start $APP ;;
    stop)    sudo systemctl stop $APP ;;
    restart) sudo systemctl restart $APP ;;
    reload)  sudo systemctl reload $APP && echo "SIGHUP sent, config reloaded" ;;

    run)
        sudo systemctl start $APP 2>/dev/null
        sleep 1
        if systemctl is-active --quiet $APP; then
            echo "Service started. Live data stream (Ctrl+C to exit):"
            echo ""
            sudo journalctl -u $APP -f --no-pager -n 10
        else
            echo "FAILED to start. Check: sudo journalctl -u $APP --no-pager -n 20"
        fi
        ;;

    status)
        echo "=== ANMK8639 Hangar Control ==="
        if systemctl is-active --quiet $APP; then
            echo "Service: RUNNING"
        else
            echo "Service: STOPPED"
        fi
        echo "Web: $WEB"
        echo ""
        # Use a temp python script to avoid bash escaping issues
        PYSCRIPT="/tmp/_hangar_status.py"
        cat > "$PYSCRIPT" << 'PYEOF'
import json, sys
try:
    h = json.load(sys.stdin)
    u = int(h.get("uptime", 0))
    print("UPTIME: " + str(u // 60) + "m" + str(u % 60) + "s  OVERALL: " + h.get("overall", "?").upper())
    print("MODULE      STATUS     AGE")
    print("-" * 35)
    for k in ["mavlink", "mqtt", "stm32", "camera"]:
        d = h.get(k, {})
        st = d.get("status", "?")
        keys = ["last_hb_sec", "last_msg_sec", "last_status_sec", "last_snapshot_sec"]
        sec = None
        for key in keys:
            if d.get(key) is not None:
                sec = d[key]
                break
        age = str(int(sec)) + "s" if sec is not None else "--"
        print(k.ljust(12) + st.ljust(10) + age)
    # System info
    s = h.get("system", {})
    if s:
        print("")
        print("CPU: " + str(s.get("cpu", "?")) + "%  RAM: " + str(s.get("ram_used", "?")) + "/" + str(s.get("ram_total", "?")) + "  Disk: " + str(s.get("disk_used", "?")) + "/" + str(s.get("disk_total", "?")))
except Exception as e:
    print("(waiting for API...)")
PYEOF
        curl -s "http://127.0.0.1:${PORT}/api/health" 2>/dev/null | python3 "$PYSCRIPT" 2>/dev/null || echo "(service not responding)"
        rm -f "$PYSCRIPT"
        ;;

    logs)    sudo journalctl -u $APP -f ;;

    check)
        if systemctl is-active --quiet $APP; then
            echo "RUNNING"
        else
            echo "STOPPED"
        fi
        echo "Web: $WEB"
        ;;

    config)  ${EDITOR:-nano} "/etc/hangar/config.yaml" ;;
    -h|--help|help|*)
        echo ""
        echo "  ANMK8639 Hangar Control CLI"
        echo "  ==========================="
        echo ""
        echo "  SERVICE CONTROL"
        echo "    hangar start      Start service"
        echo "    hangar stop       Stop service"
        echo "    hangar start      Start service"
    echo "    hangar run        Start + live data stream"
    echo "    hangar restart    Restart service"
        echo "    hangar reload     Hot-reload config (no restart)"
        echo ""
        echo "  MONITORING"
        echo "    hangar logs       Live data stream (journalctl -f)"
        echo "    hangar status     Full health + telemetry"
        echo "    hangar check      Quick running check"
        echo ""
        echo "  CONFIG"
        echo "    hangar config     Edit /etc/hangar/config.yaml"
        echo ""
        echo "  WEB UI"
        echo "    $WEB"
        echo "    (no auth needed if api_key is empty)"
        echo ""
        echo "  LOG FILES"
        echo "    /var/log/hangar/        App logs"
        echo "    /var/lib/hangar/         Snapshots"
        echo "    journalctl -u hangar     Systemd journal"
        echo 
esac
