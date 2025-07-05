"""
服务配置验证模块
"""

import os
from typing import Dict, List, Any

# 兼容的导入方式
try:
    from ..exceptions import ServiceConfigError
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(os.path.dirname(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from exceptions.service_exceptions import ServiceConfigError


class ServiceConfigValidator:
    """服务配置验证器"""
    
    REQUIRED_FIELDS = {
        "service_name": str,
        "script": str,
        "conda_env": str
    }
    
    OPTIONAL_FIELDS = {
        "args": list,
        "use_python": bool,
        "run_in_background": bool,
        "is_base": bool,
        "log_file": str,
        "startup_timeout": int,
        "health_check_url": str,
        "dependencies": list
    }
    
    @classmethod
    def validate_service_config(cls, service_config: Dict[str, Any]) -> bool:
        """
        验证单个服务配置
        
        :param service_config: 服务配置字典
        :return: 验证是否通过
        :raises ServiceConfigError: 配置验证失败时抛出
        """
        service_name = service_config.get("service_name", "Unknown")
        
        # 检查必需字段
        for field, field_type in cls.REQUIRED_FIELDS.items():
            if field not in service_config:
                raise ServiceConfigError(
                    service_name, 
                    f"Missing required field: {field}"
                )
            
            if not isinstance(service_config[field], field_type):
                raise ServiceConfigError(
                    service_name,
                    f"Field '{field}' should be of type {field_type.__name__}, got {type(service_config[field]).__name__}"
                )
        
        # 检查可选字段类型
        for field, field_type in cls.OPTIONAL_FIELDS.items():
            if field in service_config and service_config[field] is not None:
                if not isinstance(service_config[field], field_type):
                    raise ServiceConfigError(
                        service_name,
                        f"Field '{field}' should be of type {field_type.__name__}, got {type(service_config[field]).__name__}"
                    )
        
        # 检查脚本文件是否存在（如果使用Python且不是命令）
        if service_config.get("use_python", False):
            script_path = service_config["script"]
            if not script_path.startswith("/") and not os.path.exists(script_path):
                # 尝试绝对路径
                if not os.path.exists(script_path):
                    raise ServiceConfigError(
                        service_name,
                        f"Script file not found: {script_path}"
                    )
        
        # 检查Conda环境路径
        conda_env = service_config["conda_env"]
        if service_config.get("use_python", False):
            python_path = os.path.join(conda_env, "bin", "python")
            if not os.path.exists(python_path):
                raise ServiceConfigError(
                    service_name,
                    f"Python executable not found in conda environment: {python_path}"
                )
        
        return True
    
    @classmethod
    def validate_services_list(cls, services: List[Dict[str, Any]]) -> bool:
        """
        验证服务列表
        
        :param services: 服务配置列表
        :return: 验证是否通过
        """
        service_names = set()
        
        for service in services:
            # 验证单个服务配置
            cls.validate_service_config(service)
            
            # 检查服务名重复
            service_name = service["service_name"]
            if service_name in service_names:
                raise ServiceConfigError(
                    service_name,
                    f"Duplicate service name: {service_name}"
                )
            service_names.add(service_name)
        
        return True
    
    @classmethod
    def normalize_service_config(cls, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化服务配置，添加默认值
        
        :param service_config: 原始服务配置
        :return: 标准化后的服务配置
        """
        normalized = service_config.copy()
        
        # 设置默认值
        defaults = {
            "args": [],
            "use_python": False,
            "run_in_background": True,
            "is_base": False,
            "log_file": f"{service_config['service_name']}.log",
            "startup_timeout": 60,
            "health_check_url": None,
            "dependencies": []
        }
        
        for key, default_value in defaults.items():
            if key not in normalized:
                normalized[key] = default_value
        
        return normalized
