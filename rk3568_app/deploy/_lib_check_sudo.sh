#!/bin/bash
# =============================================
# 检查 sudo NOPASSWD 权限 (供 Web UI [应用配置] 按钮用)
# 被 setup_all.sh / setup_network.sh / setup_tailscale.sh / setup_camera.sh source
# 用法: source "$(dirname "$0")/_lib_check_sudo.sh"; _check_sudo_nopasswd
# =============================================

_check_sudo_nopasswd() {
    # 仅在 root 身份下检查
    if [ "$(id -u)" -ne 0 ]; then
        return 0
    fi
    local real_user="${SUDO_USER:-root}"
    if [ "$real_user" = "root" ]; then
        return 0
    fi
    # 测试 real_user 能否 sudo -n (非交互) 跑命令
    if sudo -n -u "$real_user" sudo -n true 2>/dev/null; then
        return 0
    fi
    echo -e "\033[1;33m============================================\033[0m"
    echo -e "\033[1;33m⚠ 当前用户 ${real_user} 没有 sudo NOPASSWD 权限\033[0m"
    echo -e "\033[1;33m============================================\033[0m"
    echo ""
    echo "Web UI 的 [应用配置] 按钮会调用 'sudo -n bash' 跑本脚本,"
    echo "如未配置 NOPASSWD 会失败. 解决方法 (任选其一):"
    echo ""
    echo "  方法 1: 给 ${real_user} 加完整 NOPASSWD"
    echo "    sudo bash -c 'echo \"${real_user} ALL=(ALL) NOPASSWD: ALL\" > /etc/sudoers.d/${real_user}'"
    echo "    sudo chmod 440 /etc/sudoers.d/${real_user}"
    echo ""
    echo "  方法 2: 只允许 ${real_user} 跑 deploy/setup_*.sh (更安全)"
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    echo "    sudo bash -c 'cat > /etc/sudoers.d/${real_user}-hangar << EOF"
    echo "${real_user} ALL=(ALL) NOPASSWD: /bin/bash ${script_dir}/setup_*.sh"
    echo "EOF'"
    echo "    sudo chmod 440 /etc/sudoers.d/${real_user}-hangar"
    echo ""
    echo "  方法 3: 忽略此警告, 每次手动 SSH 跑 setup 脚本 (见 dashboard 提示)"
    echo ""
    echo -n "按 Enter 继续 (脚本仍会跑), 或 Ctrl+C 退出先配置 sudo..."
    read -t 5 -r _ || true
    echo ""
    return 0
}