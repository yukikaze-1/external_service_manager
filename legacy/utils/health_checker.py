"""
服务健康检查模块
"""

import time
import logging
from typing import Dict, Optional

# 兼容的导入方式
try:
    from ..exceptions import ServiceHealthCheckError
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(os.path.dirname(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from exceptions import ServiceHealthCheckError

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class ServiceHealthChecker:
    """服务健康检查器"""
    
    # 预定义的健康检查配置
    DEFAULT_HEALTH_CHECK_CONFIGS = {
        "ollama_server": {
            "url": "http://127.0.0.1:11434/api/tags",
            "method": "GET",
            "timeout": 5,
            "expected_status": 200
        },
        "GPTSoVits_server": {
            "url": "http://127.0.0.1:9880/health",
            "method": "GET", 
            "timeout": 5,
            "expected_status": 200
        },
        "SenseVoice_server": {
            "url": "http://127.0.0.1:8001/health",
            "method": "GET",
            "timeout": 5,
            "expected_status": 200
        },
        "Consul": {
            "url": "http://127.0.0.1:8500/v1/status/leader",
            "method": "GET",
            "timeout": 5,
            "expected_status": 200
        }
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        if not HAS_REQUESTS:
            self.logger.warning("requests module not available, HTTP health checks will be skipped")
    
    def check_service_health(self, service_name: str, 
                           custom_config: Optional[Dict] = None,
                           timeout: int = 30) -> bool:
        """
        检查服务健康状态
        
        :param service_name: 服务名称
        :param custom_config: 自定义健康检查配置
        :param timeout: 总超时时间
        :return: 健康检查是否通过
        """
        if not HAS_REQUESTS:
            self.logger.warning(f"Skipping health check for {service_name} (requests not available)")
            return True
        
        # 获取健康检查配置
        config = custom_config or self.DEFAULT_HEALTH_CHECK_CONFIGS.get(service_name)
        
        if not config:
            self.logger.warning(f"No health check config for service: {service_name}")
            return True  # 假设服务正常
        
        return self._perform_http_health_check(service_name, config, timeout)
    
    def _perform_http_health_check(self, service_name: str, 
                                 config: Dict, 
                                 timeout: int) -> bool:
        """
        执行HTTP健康检查
        
        :param service_name: 服务名称
        :param config: 健康检查配置
        :param timeout: 超时时间
        :return: 检查是否通过
        """
        url = config["url"]
        method = config.get("method", "GET")
        request_timeout = config.get("timeout", 5)
        expected_status = config.get("expected_status", 200)
        
        start_time = time.time()
        check_interval = 2  # 每2秒检查一次
        
        self.logger.info(f"Starting health check for {service_name} at {url}")
        
        while time.time() - start_time < timeout:
            try:
                if method.upper() == "GET":
                    response = requests.get(url, timeout=request_timeout)
                elif method.upper() == "POST":
                    response = requests.post(url, timeout=request_timeout)
                else:
                    self.logger.error(f"Unsupported HTTP method: {method}")
                    return False
                
                if response.status_code == expected_status:
                    self.logger.info(f"Service {service_name} health check passed")
                    return True
                else:
                    self.logger.debug(f"Service {service_name} returned status {response.status_code}, expected {expected_status}")
                    
            except requests.RequestException as e:
                self.logger.debug(f"Health check attempt failed for {service_name}: {e}")
            
            time.sleep(check_interval)
        
        self.logger.error(f"Service {service_name} health check failed after {timeout}s")
        return False
    
    def wait_for_service_ready(self, service_name: str,
                             custom_config: Optional[Dict] = None,
                             timeout: int = 60) -> bool:
        """
        等待服务完全启动
        
        :param service_name: 服务名称
        :param custom_config: 自定义健康检查配置
        :param timeout: 超时时间
        :return: 服务是否就绪
        """
        self.logger.info(f"Waiting for service {service_name} to be ready...")
        
        if self.check_service_health(service_name, custom_config, timeout):
            self.logger.info(f"Service {service_name} is ready")
            return True
        else:
            raise ServiceHealthCheckError(
                service_name, 
                f"Service failed to become ready within {timeout}s"
            )
