"""
服务管理相关异常定义
"""


class ServiceError(Exception):
    """服务相关异常的基类"""
    pass


class ServiceStartupError(ServiceError):
    """服务启动异常"""
    def __init__(self, service_name: str, message: str = ""):
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' startup failed: {message}")


class ServiceHealthCheckError(ServiceError):
    """服务健康检查异常"""
    def __init__(self, service_name: str, message: str = ""):
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' health check failed: {message}")


class ServiceConfigError(ServiceError):
    """服务配置异常"""
    def __init__(self, service_name: str, message: str = ""):
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' config error: {message}")


class ServiceStopError(ServiceError):
    """服务停止异常"""
    def __init__(self, service_name: str, message: str = ""):
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' stop failed: {message}")


class ServiceNotFoundError(ServiceError):
    """服务未找到异常"""
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Service '{service_name}' not found")
