#!/bin/bash
# ANMK8639 Hangar CLI
APP="hangar"
PORT=8080
IP=$(hostname -I | awk "{print $1}")
WEB="http://${IP}:${PORT}"

case "${1:-status}" in
    start)   sudo systemctl start $APP ;;
    stop)    sudo systemctl stop $APP ;;
    restart) sudo systemctl restart $APP ;;
    reload)  sudo systemctl reload $APP && echo "SIGHUP sent, config reloaded" ;;

    status)
        echo "=== ANMK8639 Hangar Control ==="
        systemctl is-active --quiet $APP && echo "Service: RUNNING" || echo "Service: STOPPED"
        echo "Web: $WEB"
        echo ""
        curl -s http://127.0.0.1:$PORT/api/health 2>/dev/null | python3 -c "
import json,sys
try:
    h=json.load(sys.stdin)
    u=int(h.get("uptime",0))
    print("UPTIME: " + str(u//60) + "m" + str(u%60) + "s  OVERALL: " + h.get("overall","?").upper())
    print("MODULE      STATUS     AGE")
    print("-"*35)
    for k in ["mavlink","mqtt","stm32","camera"]:
        d=h.get(k,{})
        st=d.get("status","?")
        sec=d.get("last_hb_sec") or d.get("last_msg_sec") or d.get("last_status_sec") or d.get("last_snapshot_sec")
        age=str(int(sec))+"s" if sec is not None else "--"
        print(f"{k:<12} {st:<10} {age}")
except Exception as e: print("(waiting for API...)")
" 2>/dev/null || echo "(service not responding)"
        ;;

    logs)    journalctl -u $APP -f ;;

    check)
        systemctl is-active --quiet $APP && echo -e "RUNNING" || echo -e "STOPPED"
        echo "Web: $WEB"
        ;;

    config)  ${EDITOR:-nano} "/etc/hangar/config.yaml" ;;
    *)
        echo "ANMK8639 Hangar CLI"
        echo "  hangar start/stop/restart/reload"
        echo "  hangar status   - detailed status"
        echo "  hangar logs     - live logs"
        echo "  hangar check    - quick check"
        echo "  hangar config   - edit config"
        ;;
esac
