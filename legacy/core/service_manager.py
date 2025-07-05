"""
重构后的外部服务管理器 - 核心模块
"""

import os
import json
import logging
import yaml
from threading import Lock
from typing import List, Dict, Optional, Tuple, Any
from subprocess import Popen
from dotenv import dotenv_values

from Module.Utils.Logger import setup_logger
from Module.Utils.ConfigTools import load_config

# 使用兼容的导入方式
try:
    # 尝试相对导入（作为包使用时）
    from ..exceptions import (
        ServiceStartupError, 
        ServiceConfigError, 
        ServiceNotFoundError,
        ServiceStopError
    )
    from ..utils import (
        ServiceConfigValidator,
        ServiceHealthChecker,
        ProcessManager,
        RetryManager
    )
except ImportError:
    # 如果相对导入失败，使用绝对导入（直接导入时）
    import sys
    import os
    
    # 添加当前目录到路径
    current_dir = os.path.dirname(os.path.dirname(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from exceptions.service_exceptions import (
        ServiceStartupError, 
        ServiceConfigError, 
        ServiceNotFoundError,
        ServiceStopError
    )
    from utils.config_validator import ServiceConfigValidator
    from utils.health_checker import ServiceHealthChecker
    from utils.process_manager import ProcessManager
    from utils.retry_manager import RetryManager


class ExternalServiceManager:
    """
    重构后的外部服务管理器
    
    功能特点：
    1. 完善的错误处理和异常管理
    2. 服务健康检查机制
    3. 重试机制支持
    4. 配置验证
    5. 更好的代码组织结构
    """
    
    def __init__(self):
        # 初始化日志
        self.logger = setup_logger(name="ExternalService", log_path="ExternalService")
        
        # 加载配置
        self._load_configuration()
        
        # 初始化工具组件
        self.config_validator = ServiceConfigValidator()
        self.health_checker = ServiceHealthChecker(self.logger)
        self.process_manager = ProcessManager(self.logger)
        self.retry_manager = RetryManager(self.logger)
        
        # 进程管理
        self.lock = Lock()
        self.base_processes: List[Tuple[str, Popen]] = []
        self.optional_processes: List[Tuple[str, Popen]] = []
        
        # 控制自动清理行为
        self._auto_cleanup = True
        
        self.logger.info("ExternalServiceManager initialized successfully")
    
    def _load_configuration(self):
        """加载配置文件"""
        try:
            # 获取 AGENT_HOME 环境变量
            agent_home = os.environ.get('AGENT_HOME', os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            
            # 优先使用 ExternalServiceInit 目录下的配置文件
            external_service_config = os.path.join(agent_home, "Init", "ExternalServiceInit", "config.yml")
            external_service_env = os.path.join(agent_home, "Init", "ExternalServiceInit", ".env")
            
            # 加载环境变量
            if os.path.exists(external_service_env):
                self.env_vars = dotenv_values(external_service_env)
            else:
                init_env = os.path.join(agent_home, "Init", ".env")
                if os.path.exists(init_env):
                    self.env_vars = dotenv_values(init_env)
                else:
                    self.env_vars = {}
            
            if os.path.exists(external_service_config):
                # 使用专门的外部服务配置文件
                with open(external_service_config, 'r', encoding='utf-8') as f:
                    full_config = yaml.safe_load(f)
                    self.config = full_config
                self.config_path = external_service_config
                self.logger.info(f"Using dedicated external service config: {external_service_config}")
                # 从完整配置中获取external_services部分
                external_services_config = self.config.get('external_services', {})
            else:
                # 回退到原来的配置方式
                fallback_config_path = os.path.join(agent_home, "Init", "config.yml")
                if os.path.exists(fallback_config_path):
                    # load_config 返回的是 external_services 子配置
                    external_services_config = load_config(
                        config_path=fallback_config_path, 
                        config_name='external_services', 
                        logger=self.logger
                    )
                    # 为了保持一致性，将其包装在完整配置结构中
                    self.config = {'external_services': external_services_config}
                    self.config_path = fallback_config_path
                    self.logger.warning("Using fallback configuration from Init directory")
                else:
                    # 如果都没有找到配置文件，创建一个最小配置
                    self.logger.error("No configuration file found. Creating minimal config.")
                    self.config = {'external_services': {'base_services': [], 'optional_services': []}}
                    external_services_config = self.config['external_services']
                    self.config_path = "minimal_config"  # 设置一个默认值
            
            self.support_services: List[str] = external_services_config.get('support_services', [])
            
            # 设置日志目录
            # 优先从配置文件获取，否则使用环境变量
            if hasattr(self, 'env_vars') and self.env_vars:
                log_base = self.env_vars.get("LOG_PATH")
                if log_base and "${AGENT_HOME}" in log_base:
                    log_base = log_base.replace("${AGENT_HOME}", agent_home)
            else:
                log_base = os.environ.get("LOG_PATH", os.path.join(agent_home, "Log"))
            
            if log_base is None:
                log_base = os.path.join(agent_home, "Log")
            
            self.log_dir = os.path.join(log_base, "ExternalService")
            os.makedirs(self.log_dir, exist_ok=True)
            
        except Exception as e:
            raise ServiceConfigError("Configuration", f"Failed to load configuration: {e}")
    
    def init_services(self) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
        """
        初始化并启动所有配置的服务
        
        :return: (成功启动的基础服务, 成功启动的可选服务)
        """
        self.logger.info("Starting service initialization...")
        
        base_success, base_fail = self._init_base_services()
        optional_success, optional_fail = self._init_optional_services()
        
        self.logger.info(f"Service initialization completed. "
                        f"Base: {len(base_success)} success, {len(base_fail)} failed. "
                        f"Optional: {len(optional_success)} success, {len(optional_fail)} failed.")
        
        return base_success, optional_success
    
    def _get_services(self, is_base_services: bool) -> List[Dict]:
        """
        获取服务配置列表
        
        :param is_base_services: True为基础服务，False为可选服务
        :return: 服务配置列表
        """
        services_key = "base_services" if is_base_services else "optional_services"
        external_services = self.config.get("external_services", {})
        services_list = external_services.get(services_key, [])
        
        if not services_list:
            if is_base_services:
                raise ServiceConfigError(
                    "Configuration", 
                    f"base_services is empty. Please check {self.config_path}"
                )
            return []
        
        # 提取服务配置并验证
        service_configs = []
        for service_item in services_list:
            if isinstance(service_item, dict) and len(service_item) == 1:
                service_config = next(iter(service_item.values()))
                
                # 标准化配置
                normalized_config = self.config_validator.normalize_service_config(service_config)
                
                # 验证配置
                self.config_validator.validate_service_config(normalized_config)
                
                service_configs.append(normalized_config)
        
        return service_configs
    
    def _start_single_service(self, service_config: Dict) -> Tuple[bool, Tuple[str, int]]:
        """
        启动单个服务（带重试和健康检查）
        
        :param service_config: 服务配置
        :return: (启动成功, (服务名, PID))
        """
        service_name = service_config["service_name"]
        script_path = service_config["script"]
        
        # 清理已存在的进程
        cleaned = self.process_manager.cleanup_existing_processes(service_name, script_path)
        if cleaned:
            self.logger.info(f"Cleaned up existing processes for {service_name}")
        
        def start_func():
            return self.process_manager.create_process(service_config, self.log_dir)
        
        def health_check_func():
            health_check_url = service_config.get("health_check_url")
            custom_config = None
            if health_check_url:
                custom_config = {"url": health_check_url, "method": "GET"}
            
            return self.health_checker.check_service_health(
                service_name, 
                custom_config,
                timeout=service_config.get("startup_timeout", 30)
            )
        
        try:
            success, result = self.retry_manager.retry_service_start(
                start_func=start_func,
                health_check_func=health_check_func,
                service_name=service_name,
                max_retries=3
            )
            
            if success:
                # 将进程添加到管理列表
                service_name, pid = result
                process = self._find_process_by_name_and_pid(service_name, pid)
                if process:
                    if service_config.get("is_base", False):
                        self.base_processes.append((service_name, process))
                    else:
                        self.optional_processes.append((service_name, process))
            
            return success, result
            
        except Exception as e:
            self.logger.error(f"Failed to start service {service_name}: {e}")
            return False, (service_name, -1)
    
    def _find_process_by_name_and_pid(self, service_name: str, pid: int) -> Optional[Popen]:
        """
        根据服务名和PID查找进程对象
        注意：这是一个简化实现，实际使用中可能需要更复杂的进程跟踪
        """
        # 这里简化处理，实际应该维护一个PID到Popen对象的映射
        return None
    
    def _start_services_sequentially(self, services: List[Dict]) -> Tuple[bool, List[Tuple[str, int]], List[Tuple[str, int]]]:
        """
        按顺序启动多个服务
        
        :param services: 服务配置列表
        :return: (全部成功, 成功列表, 失败列表)
        """
        if not services:
            return True, [], []
        
        success_list = []
        fail_list = []
        
        for service_config in services:
            try:
                success, result = self._start_single_service(service_config)
                if success:
                    success_list.append(result)
                else:
                    fail_list.append(result)
            except Exception as e:
                service_name = service_config.get("service_name", "Unknown")
                self.logger.error(f"Service {service_name} startup failed: {e}")
                fail_list.append((service_name, -1))
        
        return len(fail_list) == 0, success_list, fail_list
    
    def _init_base_services(self) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
        """初始化基础服务"""
        self.logger.info("Initializing base services...")
        
        base_services = self._get_services(is_base_services=True)
        _, success, fail = self._start_services_sequentially(base_services)
        
        if fail:
            # 基础服务启动失败是严重问题
            self.logger.error(f"Critical: Base services failed to start: {fail}")
            # 可以选择抛出异常或继续
        
        return success, fail
    
    def _init_optional_services(self) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]]]:
        """初始化可选服务"""
        self.logger.info("Initializing optional services...")
        
        optional_services = self._get_services(is_base_services=False)
        if not optional_services:
            self.logger.info("No optional services configured")
            return [], []
        
        _, success, fail = self._start_services_sequentially(optional_services)
        
        if fail:
            self.logger.warning(f"Some optional services failed to start: {fail}")
        
        return success, fail
    
    def stop_single_service(self, service_name: str) -> bool:
        """
        停止单个可选服务
        
        :param service_name: 服务名称
        :return: 是否成功停止
        """
        return self._stop_single_service_internal(service_name, is_base_service=False)
    
    def _stop_single_service_internal(self, service_name: str, is_base_service: bool) -> bool:
        """
        内部停止服务方法
        
        :param service_name: 服务名称
        :param is_base_service: 是否为基础服务
        :return: 是否成功停止
        """
        processes = self.base_processes if is_base_service else self.optional_processes
        service_type = "base" if is_base_service else "optional"
        
        for i, (name, process) in enumerate(processes):
            if name == service_name:
                try:
                    if process.poll() is None:  # 进程仍在运行
                        self.logger.info(f"Stopping {service_type} service: {service_name}")
                        self.process_manager.terminate_process(process, service_name)
                    else:
                        self.logger.info(f"{service_type} service {service_name} already stopped")
                    
                    # 从列表中移除
                    processes.pop(i)
                    return True
                    
                except Exception as e:
                    raise ServiceStopError(service_name, str(e))
        
        self.logger.warning(f"{service_type} service '{service_name}' not found in running processes")
        return False
    
    def list_started_services(self, is_base_service: Optional[bool] = None) -> List[Tuple[str, int]]:
        """
        列出已启动的服务
        
        :param is_base_service: None=全部, True=基础服务, False=可选服务
        :return: 服务名和PID的列表
        """
        if is_base_service is None:
            base_list = [(name, proc.pid) for name, proc in self.base_processes]
            optional_list = [(name, proc.pid) for name, proc in self.optional_processes]
            return base_list + optional_list
        elif is_base_service:
            return [(name, proc.pid) for name, proc in self.base_processes]
        else:
            return [(name, proc.pid) for name, proc in self.optional_processes]
    
    def stop_all_services(self):
        """停止所有服务"""
        self.logger.info("Stopping all services...")
        
        # 如果内存中有进程列表，优先使用
        if self.base_processes or self.optional_processes:
            # 停止可选服务
            for service_name, _ in self.optional_processes.copy():
                self._stop_single_service_internal(service_name, is_base_service=False)
            
            # 停止基础服务
            for service_name, _ in self.base_processes.copy():
                self._stop_single_service_internal(service_name, is_base_service=True)
        else:
            # 如果内存中没有进程列表，通过进程名称查找并停止
            self.logger.warning("No processes in memory, attempting to find and stop services by name")
            self._stop_services_by_name()
        
        self.logger.info("All services stopped")
    
    def _stop_services_by_name(self):
        """通过进程名查找并停止服务"""
        # 从配置中获取服务列表
        all_services = []
        
        if 'external_services' in self.config:
            base_services = self.config['external_services'].get('base_services', [])
            optional_services = self.config['external_services'].get('optional_services', [])
            
            # 确保服务列表不为None
            if base_services is None:
                base_services = []
            if optional_services is None:
                optional_services = []
            
            # 解析服务配置
            for service_item in base_services + optional_services:
                if isinstance(service_item, dict) and len(service_item) == 1:
                    service_config = next(iter(service_item.values()))
                    service_name = service_config.get('service_name')
                    script_path = service_config.get('script')
                    
                    if service_name and script_path:
                        all_services.append((service_name, script_path))
        
        # 停止找到的服务
        for service_name, script_path in all_services:
            try:
                self.logger.info(f"Attempting to stop service: {service_name}")
                cleaned = self.process_manager.cleanup_existing_processes(service_name, script_path)
                if cleaned:
                    self.logger.info(f"Successfully stopped service: {service_name}")
                else:
                    self.logger.info(f"No running processes found for service: {service_name}")
            except Exception as e:
                self.logger.error(f"Failed to stop service {service_name}: {e}")
        
        self.logger.info(f"Processed {len(all_services)} services for termination")
    
    def get_service_status(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取服务状态信息
        
        :return: 服务状态字典
        """
        base_status = []
        for name, process in self.base_processes:
            base_status.append({
                "name": name,
                "pid": process.pid,
                "status": "running" if process.poll() is None else "stopped"
            })
        
        optional_status = []
        for name, process in self.optional_processes:
            optional_status.append({
                "name": name,
                "pid": process.pid,
                "status": "running" if process.poll() is None else "stopped"
            })
        
        return {
            "base_services": base_status,
            "optional_services": optional_status
        }
    
    def __del__(self):
        """析构函数，确保资源清理"""
        if getattr(self, '_auto_cleanup', True):
            try:
                self.stop_all_services()
            except Exception as e:
                print(f"Error during cleanup: {e}")
            print("ExternalServiceManager cleaned up")
        else:
            print("ExternalServiceManager auto-cleanup disabled")
