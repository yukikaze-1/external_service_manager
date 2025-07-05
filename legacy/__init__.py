"""
ExternalServiceInit - 重构版外部服务管理器

这是一个重构后的外部服务管理系统，提供以下改进：

1. 模块化设计：将功能拆分为独立的模块
2. 完善的错误处理：定义了专门的异常类
3. 配置验证：自动验证服务配置的正确性
4. 健康检查：支持HTTP健康检查机制
5. 重试机制：带指数退避的自动重试
6. 进程管理：更安全的进程创建和终止

使用示例：
    from Init.ExternalServiceInit import ExternalServiceManager
    
    manager = ExternalServiceManager()
    base_services, optional_services = manager.init_services()
    
    # 列出运行中的服务
    status = manager.get_service_status()
    
    # 停止所有服务
    manager.stop_all_services()
"""

from .core import ExternalServiceManager
from .exceptions import (
    ServiceError,
    ServiceStartupError,
    ServiceHealthCheckError,
    ServiceConfigError,
    ServiceStopError,
    ServiceNotFoundError
)

__version__ = "2.0.0"
__author__ = "yomu"

__all__ = [
    'ExternalServiceManager',
    'ServiceError',
    'ServiceStartupError',
    'ServiceHealthCheckError',
    'ServiceConfigError',
    'ServiceStopError',
    'ServiceNotFoundError'
]
