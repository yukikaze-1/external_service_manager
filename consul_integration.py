#!/usr/bin/env python3
"""
Consul 服务注册和发现集成模块

这个模块提供了与 Consul 的集成功能，包括：
- 自动服务注册和注销
- 健康检查管理
- 服务发现
- 状态监控
"""

import time
import logging
import subprocess
import os
import signal
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    import consul
    HAS_CONSUL = True
except ImportError:
    HAS_CONSUL = False


@dataclass
class ServiceInfo:
    """服务信息数据类"""
    name: str
    service_id: str
    host: str
    port: int
    health_check_url: Optional[str] = None
    tags: Optional[List[str]] = None
    meta: Optional[Dict[str, str]] = None


class ConsulManager:
    """
    Consul 进程管理器
    
    负责在需要时自动启动和管理 Consul 进程
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.consul_process = None
        self.consul_pid = None
    
    def is_consul_running(self, host: str = "127.0.0.1", port: int = 8500) -> bool:
        """检查 Consul 是否正在运行"""
        try:
            import consul
            c = consul.Consul(host=host, port=port)
            # 尝试访问 Consul API
            c.status.leader()
            return True
        except Exception as e:
            self.logger.debug(f"Consul 连接检查失败: {e}")
            return False
    
    def start_consul(self, dev_mode: bool = True, client_addr: str = "0.0.0.0") -> bool:
        """
        启动 Consul 进程
        
        Args:
            dev_mode: 是否使用开发模式
            client_addr: 客户端监听地址
            
        Returns:
            bool: 启动是否成功
        """
        if self.is_consul_running():
            self.logger.info("Consul 已在运行，无需启动")
            return True
        
        try:
            # 构建 Consul 启动命令
            cmd = ["consul", "agent"]
            
            if dev_mode:
                cmd.extend(["-dev", "-client", client_addr])
            else:
                # 生产模式配置（需要额外配置文件）
                cmd.extend(["-server", "-bootstrap-expect=1", 
                           "-data-dir=/tmp/consul-data", 
                           "-client", client_addr])
            
            self.logger.info(f"启动 Consul: {' '.join(cmd)}")
            
            # 启动 Consul 进程
            self.consul_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # 创建新的进程组
            )
            
            self.consul_pid = self.consul_process.pid
            self.logger.info(f"Consul 进程已启动，PID: {self.consul_pid}")
            
            # 等待 Consul 启动完成
            max_wait = 30  # 最多等待30秒
            for i in range(max_wait):
                if self.is_consul_running():
                    self.logger.info(f"Consul 启动成功，耗时 {i+1} 秒")
                    return True
                time.sleep(1)
            
            self.logger.error("Consul 启动超时")
            self.stop_consul()
            return False
            
        except FileNotFoundError:
            self.logger.error("未找到 consul 命令，请确保 Consul 已安装并在 PATH 中")
            return False
        except Exception as e:
            self.logger.error(f"启动 Consul 失败: {e}")
            return False
    
    def stop_consul(self):
        """停止 Consul 进程"""
        if self.consul_process:
            try:
                # 发送 SIGTERM 信号到进程组
                os.killpg(os.getpgid(self.consul_process.pid), signal.SIGTERM)
                
                # 等待进程结束
                try:
                    self.consul_process.wait(timeout=10)
                    self.logger.info("Consul 进程已正常停止")
                except subprocess.TimeoutExpired:
                    # 强制终止
                    os.killpg(os.getpgid(self.consul_process.pid), signal.SIGKILL)
                    self.logger.info("Consul 进程已强制停止")
                    
            except Exception as e:
                self.logger.error(f"停止 Consul 进程失败: {e}")
            finally:
                self.consul_process = None
                self.consul_pid = None
    
    def __del__(self):
        """析构函数，确保 Consul 进程被清理"""
        # 原先在析构时会停止 Consul 进程，
        # 这会导致在脚本退出后已注册的服务从 Consul 中消失。
        # 为了让服务在脚本退出后保持在 Consul 中，移除自动停止逻辑。
        pass


class ConsulServiceRegistry:
    """
    Consul 服务注册器
    
    功能：
    1. 服务注册和注销
    2. 健康检查管理
    3. 服务发现
    4. 状态查询
    """
    
    def __init__(self, consul_url: str = "http://127.0.0.1:8500", 
                 service_prefix: str = "agent",
                 auto_start_consul: bool = False,
                 logger: Optional[logging.Logger] = None):
        """
        初始化 Consul 服务注册器
        
        Args:
            consul_url: Consul 服务器地址
            service_prefix: 服务名前缀
            auto_start_consul: 是否自动启动 Consul（如果未运行）
            logger: 日志记录器
        """
        self.consul_url = consul_url
        self.service_prefix = service_prefix
        self.auto_start_consul = auto_start_consul
        self.logger = logger or logging.getLogger(__name__)
        
        # 初始化 Consul 管理器
        self.consul_manager = ConsulManager(logger=self.logger)
        
        if not HAS_CONSUL:
            self.logger.warning("python-consul 未安装，Consul 功能将被禁用")
            self.consul = None
            return
        
        try:
            # 解析 Consul URL
            if consul_url.startswith("http://"):
                host_port = consul_url[7:]
            elif consul_url.startswith("https://"):
                host_port = consul_url[8:]
            else:
                host_port = consul_url
            
            if ":" in host_port:
                host, port = host_port.split(":", 1)
                port = int(port)
            else:
                host, port = host_port, 8500
            
            # 检查 Consul 是否运行，如果没有且允许自动启动，则启动它
            if not self.consul_manager.is_consul_running(host, port):
                if self.auto_start_consul:
                    self.logger.info("Consul 未运行，尝试自动启动...")
                    if not self.consul_manager.start_consul(dev_mode=True, client_addr="0.0.0.0"):
                        self.logger.error("自动启动 Consul 失败")
                        self.consul = None
                        return
                else:
                    self.logger.warning(f"Consul 未在 {host}:{port} 运行，且未启用自动启动")
                    self.consul = None
                    return
            
            self.consul = consul.Consul(host=host, port=port)
            self.logger.info(f"✅ Consul 客户端初始化成功: {consul_url}")
            
            # 测试连接
            self._test_connection()
            
        except Exception as e:
            self.logger.error(f"❌ Consul 初始化失败: {e}")
            self.consul = None
    
    def _test_connection(self) -> bool:
        """测试 Consul 连接"""
        if not self.consul:
            return False
        
        try:
            # 尝试获取 leader 信息
            self.consul.status.leader()
            self.logger.info("✅ Consul 连接测试成功")
            return True
        except Exception as e:
            self.logger.warning(f"⚠️ Consul 连接测试失败: {e}")
            return False
    
    def is_available(self) -> bool:
        """检查 Consul 是否可用"""
        return self.consul is not None and self._test_connection()
    
    def _generate_service_id(self, service_name: str, host: str, port: int) -> str:
        """生成唯一的服务ID"""
        if self.service_prefix:
            return f"{self.service_prefix}-{service_name}-{host}-{port}"
        else:
            return f"{service_name}-{host}-{port}"
    
    def register_service(self, service_name: str, host: str, port: int,
                        health_check_url: Optional[str] = None,
                        tags: Optional[List[str]] = None,
                        meta: Optional[Dict[str, str]] = None) -> bool:
        """
        注册服务到 Consul
        
        Args:
            service_name: 服务名称
            host: 服务主机
            port: 服务端口
            health_check_url: 健康检查URL
            tags: 服务标签
            meta: 服务元数据
            
        Returns:
            bool: 注册是否成功
        """
        if not self.consul:
            self.logger.warning(f"Consul 不可用，跳过服务注册: {service_name}")
            return False
        
        try:
            service_id = self._generate_service_id(service_name, host, port)
            
            # 检查服务是否已经注册（避免重复注册）
            existing_services = self.consul.agent.services()
            if service_id in existing_services:
                self.logger.info(f"服务已存在，跳过注册: {service_name} ({service_id})")
                return True
            
            # 同时检查是否有相同名称的服务已经注册（可能是服务自己注册的）
            service_display_name = service_name if not self.service_prefix else f"{self.service_prefix}-{service_name}"
            for existing_id, existing_service in existing_services.items():
                if (existing_service["Service"] == service_display_name and 
                    existing_service["Address"] == host and 
                    existing_service["Port"] == port):
                    self.logger.info(f"发现相同的服务已存在，跳过注册: {service_name} (已存在ID: {existing_id})")
                    return True
            
            # 准备服务注册参数
            register_kwargs = {
                "name": service_display_name,
                "service_id": service_id,
                "address": host,
                "port": port,
                "tags": tags or (["external-service"] if not self.service_prefix else [self.service_prefix, "external-service"])
            }
            
            # 添加健康检查
            if health_check_url:
                try:
                    # 对于某些服务，健康检查可能需要特殊处理
                    if service_name == "ollama_server":
                        # ollama的健康检查端点可能不稳定，使用TCP检查
                        register_kwargs["check"] = consul.Check.tcp(
                            host=host,
                            port=port,
                            interval="10s",
                            timeout="5s",
                            deregister="30s"
                        )
                        self.logger.debug(f"使用TCP健康检查: {host}:{port}")
                    else:
                        register_kwargs["check"] = consul.Check.http(
                            url=health_check_url,
                            interval="10s",
                            timeout="5s",
                            deregister="30s"
                        )
                        self.logger.debug(f"使用HTTP健康检查: {health_check_url}")
                except Exception as check_error:
                    self.logger.warning(f"添加健康检查失败 {service_name}: {check_error}")
                    # 即使健康检查失败，也尝试注册服务（不带健康检查）
            
            # 执行注册
            self.consul.agent.service.register(**register_kwargs)
            
            self.logger.info(f"✅ 服务注册成功: {service_name} ({service_id}) - {host}:{port}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 服务注册失败: {service_name} - {e}")
            return False
    
    def deregister_service(self, service_name: str, host: str = "127.0.0.1", 
                          port: Optional[int] = None) -> bool:
        """
        从 Consul 注销服务
        
        Args:
            service_name: 服务名称
            host: 服务主机
            port: 服务端口
            
        Returns:
            bool: 注销是否成功
        """
        if not self.consul:
            self.logger.warning(f"Consul 不可用，跳过服务注销: {service_name}")
            return False
        
        try:
            # 如果没有提供端口，尝试从现有服务中查找
            if port is None:
                services = self.list_services()
                for service in services:
                    if service.name.endswith(service_name):
                        port = service.port
                        break
                
                if port is None:
                    self.logger.warning(f"无法确定服务端口: {service_name}")
                    return False
            
            service_id = self._generate_service_id(service_name, host, port)
            
            # 执行注销
            self.consul.agent.service.deregister(service_id)
            
            self.logger.info(f"✅ 服务注销成功: {service_name} ({service_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 服务注销失败: {service_name} - {e}")
            return False
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """
        获取服务在 Consul 中的状态
        
        Args:
            service_name: 服务名称
            
        Returns:
            Dict: 服务状态信息
        """
        if not self.consul:
            return {"error": "Consul 不可用"}
        
        try:
            full_service_name = service_name if not self.service_prefix else f"{self.service_prefix}-{service_name}"
            
            # 获取服务信息
            services = self.consul.agent.services()
            health_checks = self.consul.agent.checks()
            
            service_status = {
                "registered": False,
                "healthy": False,
                "service_info": None,
                "health_info": None
            }
            
            # 查找服务
            for service_id, service_info in services.items():
                if service_info["Service"] == full_service_name:
                    service_status["registered"] = True
                    service_status["service_info"] = service_info
                    
                    # 查找健康检查
                    for check_id, check_info in health_checks.items():
                        if check_info.get("ServiceID") == service_id:
                            service_status["healthy"] = check_info["Status"] == "passing"
                            service_status["health_info"] = check_info
                            break
                    break
            
            return service_status
            
        except Exception as e:
            self.logger.error(f"❌ 获取服务状态失败: {service_name} - {e}")
            return {"error": str(e)}
    
    def list_services(self) -> List[ServiceInfo]:
        """
        列出所有已注册的服务
        
        Returns:
            List[ServiceInfo]: 服务信息列表
        """
        if not self.consul:
            return []
        
        try:
            services = self.consul.agent.services()
            service_list = []
            
            for service_id, service_info in services.items():
                # 如果没有前缀，返回所有服务；如果有前缀，只返回我们管理的服务
                if not self.service_prefix or service_info["Service"].startswith(self.service_prefix):
                    service_list.append(ServiceInfo(
                        name=service_info["Service"],
                        service_id=service_id,
                        host=service_info["Address"],
                        port=service_info["Port"],
                        tags=service_info.get("Tags", []),
                        meta=service_info.get("Meta", {})
                    ))
            
            return service_list
            
        except Exception as e:
            self.logger.error(f"❌ 获取服务列表失败: {e}")
            return []
    
    def discover_services(self, service_name: Optional[str] = None) -> List[ServiceInfo]:
        """
        服务发现 - 从 Consul 发现可用服务
        
        Args:
            service_name: 指定服务名称，如果为None则返回所有服务
            
        Returns:
            List[ServiceInfo]: 发现的服务列表
        """
        if not self.consul:
            return []
        
        try:
            if service_name:
                # 查找特定服务
                full_service_name = service_name if not self.service_prefix else f"{self.service_prefix}-{service_name}"
                _, service_data = self.consul.health.service(full_service_name, passing=False)  # 不仅仅是健康的服务
            else:
                # 获取所有服务（不仅仅是健康的）
                services = self.consul.agent.services()
                service_data = []
                
                # 转换为健康检查格式以保持兼容性
                for service_id, service_info in services.items():
                    if not self.service_prefix or service_info["Service"].startswith(self.service_prefix):
                        service_data.append({
                            "Service": {
                                "Service": service_info["Service"],
                                "ID": service_id,
                                "Address": service_info["Address"],
                                "Port": service_info["Port"],
                                "Tags": service_info.get("Tags", []),
                                "Meta": service_info.get("Meta", {})
                            }
                        })
            
            discovered_services = []
            for service in service_data:
                if "Service" in service:
                    discovered_services.append(ServiceInfo(
                        name=service["Service"]["Service"],
                        service_id=service["Service"]["ID"],
                        host=service["Service"]["Address"],
                        port=service["Service"]["Port"],
                        tags=service["Service"].get("Tags", []),
                        meta=service["Service"].get("Meta", {})
                    ))
            
            return discovered_services
            
        except Exception as e:
            self.logger.error(f"❌ 服务发现失败: {e}")
            return []
    
    def register_all_services(self, service_states: Dict[str, Dict]) -> Dict[str, bool]:
        """
        批量注册所有服务
        
        Args:
            service_states: 服务状态字典
            
        Returns:
            Dict[str, bool]: 每个服务的注册结果
        """
        results = {}
        
        for service_name, service_info in service_states.items():
            port = service_info.get("port")
            if not port:
                self.logger.warning(f"服务 {service_name} 缺少端口信息，跳过注册")
                results[service_name] = False
                continue
            
            # 获取健康检查URL（如果有的话）
            health_check_url = self._get_default_health_check_url(service_name, port)
            
            results[service_name] = self.register_service(
                service_name=service_name,
                host="127.0.0.1",
                port=port,
                health_check_url=health_check_url,
                tags=["external-service", service_info.get("type", "unknown")]
            )
        
        return results
    
    def _get_default_health_check_url(self, service_name: str, port: int) -> Optional[str]:
        """
        获取服务的默认健康检查URL
        
        Args:
            service_name: 服务名称
            port: 服务端口
            
        Returns:
            Optional[str]: 健康检查URL
        """
        # 预定义的健康检查URL模式
        health_check_patterns = {
            "Consul": f"http://127.0.0.1:{port}/v1/status/leader",
            "ollama_server": f"http://127.0.0.1:{port}/api/tags",
            "GPTSoVits_server": f"http://127.0.0.1:{port}/health",
            "SenseVoice_server": f"http://127.0.0.1:{port}/health",
            "MicroServiceGateway": f"http://127.0.0.1:{port}/health",
            "APIGateway": f"http://127.0.0.1:{port}/health",
            "MySQLAgent": f"http://127.0.0.1:{port}/health",
            "MySQLService": f"http://127.0.0.1:{port}/health", 
            "UserService": f"http://127.0.0.1:{port}/health"
        }
        
        return health_check_patterns.get(service_name)

    def deregister_all_services(self, service_states: Dict[str, Dict]) -> Dict[str, bool]:
        """
        批量注销所有服务
        
        Args:
            service_states: 服务状态字典
            
        Returns:
            Dict[str, bool]: 每个服务的注销结果
        """
        results = {}
        
        for service_name, service_info in service_states.items():
            port = service_info.get("port")
            results[service_name] = self.deregister_service(
                service_name=service_name,
                host="127.0.0.1",
                port=port
            )
        
        return results
    
    def shutdown(self, deregister_services: bool = True):
        """
        关闭 Consul 服务注册器并清理资源
        
        Args:
            deregister_services: 是否注销所有已注册的服务，默认为True
        """
        self.logger.info("正在关闭 Consul 服务注册器...")
        
        if deregister_services:
            try:
                # 注销所有已注册的服务
                if self.consul:
                    registered_services = self._get_registered_services()
                    for service in registered_services:
                        service_id = service.get("ID", "")
                        # 如果没有前缀，注销所有服务；如果有前缀，只注销我们管理的服务
                        if not self.service_prefix or service_id.startswith(f"{self.service_prefix}-"):
                            self.logger.info(f"注销服务: {service_id}")
                            self.consul.agent.service.deregister(service_id)
            except Exception as e:
                self.logger.warning(f"注销服务时出错: {e}")

        try:
            # 如果是自动启动的 Consul，则停止它
            if hasattr(self, 'consul_manager') and self.consul_manager:
                self.consul_manager.stop_consul()
        except Exception as e:
            self.logger.warning(f"停止 Consul 进程时出错: {e}")
        
        self.logger.info("Consul 服务注册器已关闭")
    
    def _get_registered_services(self) -> List[Dict[str, Any]]:
        """获取已注册的服务列表"""
        if not self.consul:
            return []
        
        try:
            services = self.consul.agent.services()
            return list(services.values()) if services else []
        except Exception as e:
            self.logger.warning(f"获取已注册服务列表失败: {e}")
            return []
    
    def __del__(self):
        """析构函数，确保资源被清理"""
        # 不在析构时停止 Consul 或注销服务，保留运行状态以便长期可见性。
        return


class ConsulIntegrationManager:
    """
    Consul 集成管理器
    
    这个类将 Consul 功能集成到现有的服务管理器中
    """
    
    def __init__(self, consul_config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        初始化 Consul 集成管理器
        
        Args:
            consul_config: Consul 配置
            logger: 日志记录器
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = consul_config
        
        # 初始化 Consul 注册器
        self.registry = ConsulServiceRegistry(
            consul_url=consul_config.get("url", "http://127.0.0.1:8500"),
            service_prefix=consul_config.get("service_prefix", "agent"),
            auto_start_consul=consul_config.get("auto_start", False),
            logger=self.logger
        )
        
        # 启用/禁用自动注册
        self.auto_register = consul_config.get("auto_register", False)
        
        self.logger.info(f"Consul 集成管理器初始化完成 (auto_register: {self.auto_register})")
    
    def on_service_started(self, service_name: str, service_info: Dict[str, Any]) -> bool:
        """
        服务启动时的回调函数
        
        Args:
            service_name: 服务名称
            service_info: 服务信息
            
        Returns:
            bool: 处理是否成功
        """
        if not self.auto_register or not self.registry.is_available():
            return True
        
        # 跳过Consul服务，因为它在开发模式下会自动注册自己
        if service_name.lower() == "consul":
            self.logger.info(f"跳过Consul服务注册，它会自动注册自己")
            return True
        
        port = service_info.get("port")
        if not port:
            self.logger.warning(f"服务 {service_name} 缺少端口信息，跳过 Consul 注册")
            return False
        
        # 获取健康检查URL（如果有的话）
        health_check_url = self._get_health_check_url(service_name, port)
        
        return self.registry.register_service(
            service_name=service_name,
            host="127.0.0.1",
            port=port,
            health_check_url=health_check_url,
            tags=["external-service", service_info.get("type", "unknown")]
        )
    
    def on_service_stopped(self, service_name: str, service_info: Dict[str, Any]) -> bool:
        """
        服务停止时的回调函数
        
        Args:
            service_name: 服务名称
            service_info: 服务信息
            
        Returns:
            bool: 处理是否成功
        """
        if not self.auto_register or not self.registry.is_available():
            return True
        
        # 跳过Consul服务，因为它在开发模式下会自动管理自己
        if service_name.lower() == "consul":
            self.logger.info(f"跳过Consul服务注销，它会自动管理自己")
            return True
        
        port = service_info.get("port")
        return self.registry.deregister_service(
            service_name=service_name,
            host="127.0.0.1",
            port=port
        )
    
    def _get_health_check_url(self, service_name: str, port: int) -> Optional[str]:
        """
        获取服务的健康检查URL
        
        Args:
            service_name: 服务名称
            port: 服务端口
            
        Returns:
            Optional[str]: 健康检查URL
        """
        # 预定义的健康检查URL模式
        health_check_patterns = {
            "Consul": f"http://127.0.0.1:{port}/v1/status/leader",
            "ollama_server": f"http://127.0.0.1:{port}/api/tags",
            "GPTSoVits_server": f"http://127.0.0.1:{port}/health",
            "SenseVoice_server": f"http://127.0.0.1:{port}/health",
            "MicroServiceGateway": f"http://127.0.0.1:{port}/health",
            "APIGateway": f"http://127.0.0.1:{port}/health",
            "MySQLAgent": f"http://127.0.0.1:{port}/health",
            "MySQLService": f"http://127.0.0.1:{port}/health",
            "UserService": f"http://127.0.0.1:{port}/health"
        }
        
        return health_check_patterns.get(service_name)
