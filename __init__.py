"""
External Service Manager

一个独立的外部服务管理工具，用于启动、停止和管理多个外部服务。

主要功能：
- 启动/停止/重启所有服务
- 查看服务状态和运行时间
- 自动健康检查和监控
- 配置文件管理
- 日志记录和错误处理

使用示例：
    python service_manager.py start      # 启动所有服务
    python service_manager.py stop       # 停止所有服务
    python service_manager.py status     # 查看服务状态
    python service_manager.py restart    # 重启所有服务
    
    # 或使用便捷脚本
    ./manage_services.sh start
    ./manage_services.sh status
"""

__version__ = "1.0.0"
__author__ = "yomu"
__description__ = "独立的外部服务管理工具"
