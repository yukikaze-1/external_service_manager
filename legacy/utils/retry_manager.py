"""
重试机制工具模块
"""

import time
import logging
from typing import Callable, Any, Optional, Dict

# 兼容的导入方式
try:
    from ..exceptions import ServiceStartupError
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(os.path.dirname(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from exceptions import ServiceStartupError


class RetryManager:
    """重试管理器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def retry_with_backoff(self,
                          func: Callable,
                          max_retries: int = 3,
                          base_delay: float = 1.0,
                          max_delay: float = 60.0,
                          backoff_factor: float = 2.0,
                          service_name: str = "Unknown") -> Any:
        """
        带指数退避的重试机制
        
        :param func: 要重试的函数
        :param max_retries: 最大重试次数
        :param base_delay: 基础延迟时间（秒）
        :param max_delay: 最大延迟时间（秒）
        :param backoff_factor: 退避因子
        :param service_name: 服务名称（用于日志）
        :return: 函数执行结果
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                result = func()
                if attempt > 0:
                    self.logger.info(f"Service {service_name} succeeded on attempt {attempt + 1}")
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    # 计算延迟时间（指数退避）
                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    
                    self.logger.warning(
                        f"Service {service_name} attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"Service {service_name} failed after {max_retries + 1} attempts: {e}"
                    )
        
        # 所有重试都失败了
        raise ServiceStartupError(
            service_name,
            f"Failed after {max_retries + 1} attempts. Last error: {last_exception}"
        )
    
    def retry_service_start(self, 
                          start_func: Callable,
                          health_check_func: Optional[Callable] = None,
                          service_name: str = "Unknown",
                          max_retries: int = 3) -> Any:
        """
        专门用于服务启动的重试机制
        
        :param start_func: 启动函数
        :param health_check_func: 健康检查函数
        :param service_name: 服务名称
        :param max_retries: 最大重试次数
        :return: 启动结果
        """
        def combined_func():
            # 执行启动
            start_result = start_func()
            
            # 如果有健康检查函数，执行健康检查
            if health_check_func:
                if not health_check_func():
                    raise ServiceStartupError(service_name, "Health check failed")
            
            return start_result
        
        return self.retry_with_backoff(
            func=combined_func,
            max_retries=max_retries,
            service_name=service_name
        )
