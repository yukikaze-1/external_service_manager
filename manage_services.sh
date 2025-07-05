#!/bin/bash
# 外部服务管理器便捷脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/service_manager.py"

# 检查Python脚本是否存在
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ 错误：找不到 service_manager.py"
    exit 1
fi

# 设置AGENT_HOME环境变量（指向当前目录）
export AGENT_HOME="$SCRIPT_DIR"

# 函数：显示帮助信息
show_help() {
    echo "外部服务管理器便捷脚本"
    echo ""
    echo "使用方式:"
    echo "  $0 start     # 启动所有外部服务"
    echo "  $0 stop      # 停止所有外部服务"
    echo "  $0 restart   # 重启所有外部服务"
    echo "  $0 status    # 查看服务状态"
    echo "  $0 register  # 注册服务到Consul"
    echo "  $0 unregister # 从Consul注销服务"
    echo "  $0 discover  # 从Consul发现服务"
    echo "  $0 help      # 显示帮助信息"
    echo ""
    echo "环境变量:"
    echo "  AGENT_HOME=$AGENT_HOME"
}

# 函数：检查依赖
check_dependencies() {
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ 错误：未找到 python3"
        exit 1
    fi
    
    # 检查传统管理器目录
    if [ ! -d "$AGENT_HOME/legacy" ]; then
        echo "❌ 错误：未找到本地化外部服务管理器"
        echo "请确保 legacy 目录存在"
        exit 1
    fi
}

# 主逻辑
case "$1" in
    (start)
        echo "🚀 启动外部服务..."
        check_dependencies
        python3 "$PYTHON_SCRIPT" start
        ;;
    (stop)
        echo "🛑 停止外部服务..."
        check_dependencies
        python3 "$PYTHON_SCRIPT" stop
        ;;
    (restart)
        echo "🔄 重启外部服务..."
        check_dependencies
        python3 "$PYTHON_SCRIPT" restart
        ;;
    (status)
        echo "📊 检查服务状态..."
        check_dependencies
        python3 "$PYTHON_SCRIPT" status
        ;;
    (register)
        echo "🔗 注册服务到Consul..."
        check_dependencies
        python3 "$PYTHON_SCRIPT" consul-register
        ;;
    (unregister)
        echo "🔗 从Consul注销服务..."
        check_dependencies
        python3 "$PYTHON_SCRIPT" consul-unregister
        ;;
    (discover)
        echo "🔍 从Consul发现服务..."
        check_dependencies
        python3 "$PYTHON_SCRIPT" consul-discover
        ;;
    (help|--help|-h)
        show_help
        ;;
    ("")
        echo "❌ 错误：请指定操作"
        echo "使用 '$0 help' 查看帮助信息"
        exit 1
        ;;
    (*)
        echo "❌ 错误：未知操作 '$1'"
        echo "使用 '$0 help' 查看帮助信息"
        exit 1
        ;;
esac
