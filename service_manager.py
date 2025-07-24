#!/usr/bin/env python3
"""
独立外部服务管理器

这是一个独立的外部服务管理工具，用于启动、停止和管理外部服务。
设计为与主应用分离，可以独立运行和管理服务生命周期。

使用方式：
    python service_manager.py start     # 启动所有服务
    python service_manager.py stop      # 停止所有服务
    python service_manager.py status    # 查看服务状态
    python service_manager.py restart   # 重启所有服务
    
    # 管理单个服务
    python service_manager.py start ollama_server
    python service_manager.py stop ollama_server
    python service_manager.py status ollama_server
"""

import os
import sys
import json
import time
import argparse
import signal
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# 添加当前目录到路径（用于独立项目）
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入本地化的外部服务管理器
try:
    from legacy.core import ExternalServiceManager as LegacyExternalServiceManager
    from legacy.exceptions import *
except ImportError as e:
    print(f"错误：无法导入本地化的外部服务管理器: {e}")
    print("请确保 legacy 目录存在并包含必要文件")
    sys.exit(1)

# 导入Consul集成模块
try:
    from consul_integration import ConsulIntegrationManager
    HAS_CONSUL_INTEGRATION = True
except ImportError as e:
    print(f"警告：Consul集成模块导入失败: {e}")
    HAS_CONSUL_INTEGRATION = False

from Module.Utils.Logger import setup_logger


class ExternalServiceManager:
    """
    独立外部服务管理器
    
    基于传统的 ExternalServiceInit 实现，提供命令行接口来管理外部服务
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化服务管理器
        
        Args:
            config_path: 配置文件路径，如果不提供则使用默认配置
        """
        self.logger = setup_logger(name="ExternalServiceManager", log_path="Other")
        
        # 设置配置路径环境变量，确保传统管理器能找到正确的配置
        self._setup_environment(config_path)
        
        # 初始化传统的外部服务管理器
        try:
            self.legacy_manager = LegacyExternalServiceManager()
            # 禁用传统管理器的自动清理，避免程序结束时自动停止服务
            self.legacy_manager._auto_cleanup = False
            self.logger.info("✅ 外部服务管理器初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 外部服务管理器初始化失败: {e}")
            raise
        
        # 状态文件路径
        self.state_file = Path(__file__).parent / "service_state.json"
        
        # 服务状态
        self.running_services = self._load_service_state()
        
        # 初始化Consul集成
        self.consul_manager = None
        self._init_consul_integration()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 禁用Consul集成的自动清理，让服务在程序退出后继续在Consul中注册
        if self.consul_manager and hasattr(self.consul_manager, 'registry'):
            # 替换原有的__del__方法，避免自动注销服务
            original_del = self.consul_manager.registry.__class__.__del__
            def safe_del(obj_self):
                try:
                    # 只停止Consul进程，不注销服务
                    if hasattr(obj_self, 'consul_manager') and obj_self.consul_manager:
                        obj_self.consul_manager.stop_consul()
                except Exception:
                    pass
            self.consul_manager.registry.__class__.__del__ = safe_del
    
    def _signal_handler(self, signum, frame):
        """处理系统信号，优雅关闭"""
        self.logger.info(f"收到信号 {signum}，正在关闭所有服务...")
        self.stop_all_services()
        sys.exit(0)
    
    def _load_service_state(self) -> Dict:
        """加载服务状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"加载服务状态失败: {e}")
        return {}
    
    def _save_service_state(self):
        """保存服务状态"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.running_services, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存服务状态失败: {e}")
    
    def _setup_environment(self, config_path: Optional[str] = None):
        """
        设置环境变量，确保传统管理器能找到正确的配置
        
        Args:
            config_path: 用户指定的配置文件路径
        """
        # 项目根目录现在就是当前目录
        project_root = Path(__file__).parent
        
        # 设置 AGENT_HOME 环境变量（如果未设置）
        if 'AGENT_HOME' not in os.environ:
            os.environ['AGENT_HOME'] = str(project_root)
            self.logger.info(f"设置 AGENT_HOME = {project_root}")
        
        # 切换工作目录到项目根目录，确保相对路径正确解析
        original_cwd = os.getcwd()
        os.chdir(str(project_root))
        self.logger.info(f"工作目录从 {original_cwd} 切换到 {project_root}")
        
        # 确保传统管理器能找到配置文件
        # 传统管理器会查找: ${AGENT_HOME}/Init/ExternalServiceInit/config.yml
        init_external_service_dir = project_root / "Init" / "ExternalServiceInit"
        init_external_service_dir.mkdir(parents=True, exist_ok=True)
        
        target_config = init_external_service_dir / "config.yml"
        
        if config_path:
            # 用户指定了配置文件
            if not os.path.isabs(config_path):
                config_path = os.path.join(str(project_root), config_path)
            
            if os.path.exists(config_path):
                # 复制用户指定的配置文件
                import shutil
                shutil.copy2(config_path, str(target_config))
                self.logger.info(f"使用用户指定的配置文件: {config_path}")
            else:
                self.logger.warning(f"用户指定的配置文件不存在: {config_path}")
        
        # 如果目标配置文件不存在，使用本地配置文件
        if not target_config.exists():
            local_config = Path(__file__).parent / "legacy" / "config.yml"
            if local_config.exists():
                import shutil
                shutil.copy2(str(local_config), str(target_config))
                self.logger.info(f"使用本地配置文件: {local_config}")
            else:
                self.logger.error(f"找不到本地配置文件: {local_config}")
                raise FileNotFoundError(f"配置文件不存在: {local_config}")
        
        self.logger.info(f"传统管理器将使用配置文件: {target_config}")
    
    def _get_service_port_from_config(self, service_name: str) -> Optional[int]:
        """从配置文件获取服务的真实端口"""
        try:
            import yaml
            config_file = Path(__file__).parent / "legacy" / "config.yml"
            
            if not config_file.exists():
                return None
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 从ip_port配置中获取端口
            ip_ports = config.get("external_services", {}).get("ip_port", [])
            
            for port_config in ip_ports:
                if isinstance(port_config, dict):
                    for svc_name, port_info in port_config.items():
                        # 处理服务名映射
                        if (svc_name == service_name or 
                            (svc_name == "GPTSoVits" and service_name == "GPTSoVits_server") or
                            (svc_name == "SenseVoice" and service_name == "SenseVoice_server")):
                            if isinstance(port_info, list) and len(port_info) >= 2:
                                return int(port_info[1])
            
            # 如果在ip_port中没找到，尝试从健康检查URL中提取
            base_services = config.get("external_services", {}).get("base_services", [])
            for service_config in base_services:
                if isinstance(service_config, dict):
                    svc_name = list(service_config.keys())[0]
                    if svc_name == service_name:
                        health_url = service_config[svc_name].get("health_check_url", "")
                        if health_url:
                            # 从URL中提取端口，例如 http://127.0.0.1:8500/v1/status/leader
                            import re
                            match = re.search(r':(\d+)/', health_url)
                            if match:
                                return int(match.group(1))
            
        except Exception as e:
            self.logger.warning(f"从配置获取端口失败 {service_name}: {e}")
        
        return None
    
    def _init_consul_integration(self):
        """初始化Consul集成"""
        if not HAS_CONSUL_INTEGRATION:
            self.logger.warning("Consul集成模块不可用，跳过Consul功能")
            return
        
        try:
            # 加载Consul配置
            consul_config = self._load_consul_config()
            
            if consul_config.get("enabled", False):
                self.consul_manager = ConsulIntegrationManager(
                    consul_config=consul_config,
                    logger=self.logger
                )
                self.logger.info("✅ Consul集成初始化成功")
            else:
                self.logger.info("Consul集成已禁用")
        except Exception as e:
            self.logger.warning(f"⚠️ Consul集成初始化失败: {e}")
    
    def _load_consul_config(self) -> Dict:
        """加载Consul配置"""
        config_file = Path(__file__).parent / "config.yml"
        
        if not config_file.exists():
            return {"enabled": False}
        
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            consul_config = config.get("consul", {})
            # 默认启用Consul集成
            consul_config.setdefault("enabled", True)
            
            return consul_config
        except Exception as e:
            self.logger.warning(f"加载Consul配置失败: {e}")
            return {"enabled": False}
    
    def start_all_services(self) -> bool:
        """启动所有服务"""
        self.logger.info("🚀 开始启动所有外部服务...")
        
        try:
            # 使用传统管理器启动服务
            base_services, optional_services = self.legacy_manager.init_services()
            
            # 记录启动的服务
            started_services = {}
            
            if base_services:
                for name, process_id in base_services:
                    # 获取真实的服务端口
                    real_port = self._get_service_port_from_config(name)
                    port = real_port if real_port else process_id  # 如果找不到真实端口，使用进程ID作为后备
                    
                    started_services[name] = {
                        "type": "base",
                        "port": port,
                        "process_id": process_id,  # 保存进程ID以便管理
                        "start_time": time.time(),
                        "status": "running"
                    }
                self.logger.info(f"✅ 基础服务启动成功: {[name for name, _ in base_services]}")
            
            if optional_services:
                for name, process_id in optional_services:
                    # 获取真实的服务端口
                    real_port = self._get_service_port_from_config(name)
                    port = real_port if real_port else process_id
                    
                    started_services[name] = {
                        "type": "optional", 
                        "port": port,
                        "process_id": process_id,  # 保存进程ID以便管理
                        "start_time": time.time(),
                        "status": "running"
                    }
                self.logger.info(f"✅ 可选服务启动成功: {[name for name, _ in optional_services]}")
            
            # 更新状态
            self.running_services.update(started_services)
            self._save_service_state()
            
            # Consul集成：注册启动的服务
            if self.consul_manager and started_services:
                self.logger.info("🔗 开始向Consul注册服务...")
                self._register_services_to_consul(started_services)
            
            total_services = len(base_services) + len(optional_services)
            self.logger.info(f"🎉 服务启动完成！共启动 {total_services} 个服务")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 服务启动失败: {e}")
            return False
    
    def stop_all_services(self) -> bool:
        """停止所有服务"""
        self.logger.info("🛑 开始停止所有外部服务...")
        
        try:
            # Consul集成：注销服务
            if self.consul_manager and self.running_services:
                self.logger.info("🔗 开始从Consul注销服务...")
                self._deregister_services_from_consul(self.running_services)
            
            if hasattr(self.legacy_manager, 'stop_all_services'):
                self.legacy_manager.stop_all_services()
            else:
                self.logger.warning("传统管理器不支持停止服务功能")
            
            # 清空状态
            stopped_count = len(self.running_services)
            self.running_services.clear()
            self._save_service_state()
            
            self.logger.info(f"✅ 服务停止完成！共停止 {stopped_count} 个服务")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 服务停止失败: {e}")
            return False
    
    def get_service_status(self) -> Dict:
        """获取服务状态"""
        status = {
            "timestamp": time.time(),
            "total_services": len(self.running_services),
            "services": {}
        }
        
        # 获取详细状态
        try:
            if hasattr(self.legacy_manager, 'get_service_status'):
                legacy_status = self.legacy_manager.get_service_status()
                status["legacy_status"] = legacy_status
        except Exception as e:
            self.logger.warning(f"获取传统状态失败: {e}")
        
        # 添加记录的服务信息
        for service_name, service_info in self.running_services.items():
            status["services"][service_name] = {
                **service_info,
                "uptime": time.time() - service_info.get("start_time", 0)
            }
        
        # 添加Consul状态信息
        if self.consul_manager:
            status["consul"] = self._get_consul_status()
        
        return status
    
    def start_service(self, service_name: str) -> bool:
        """启动单个服务"""
        self.logger.info(f"🚀 启动服务: {service_name}")
        
        # TODO: 实现单个服务启动
        # 当前传统管理器不支持单个服务启动，这将在后续版本实现
        self.logger.warning("单个服务启动功能待实现，请使用 start 命令启动所有服务")
        return False
    
    def stop_service(self, service_name: str) -> bool:
        """停止单个服务"""
        self.logger.info(f"🛑 停止服务: {service_name}")
        
        # TODO: 实现单个服务停止
        # 当前传统管理器不支持单个服务停止，这将在后续版本实现
        self.logger.warning("单个服务停止功能待实现，请使用 stop 命令停止所有服务")
        return False
    
    def consul_register_all(self) -> bool:
        """向Consul注册所有服务"""
        self.logger.info("🔗 开始向Consul注册所有服务...")
        
        try:
            if not self.consul_manager:
                self.logger.warning("Consul集成未初始化，无法注册服务")
                return False
            
            for service_name, service_info in self.running_services.items():
                try:
                    self.consul_manager.on_service_started(service_name, service_info)
                    self.logger.info(f"✅ 服务已注册到Consul: {service_name}")
                except Exception as e:
                    self.logger.warning(f"向Consul注册服务失败 {service_name}: {e}")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ 服务注册到Consul失败: {e}")
            return False
    
    def consul_unregister_all(self) -> bool:
        """从Consul注销所有服务"""
        self.logger.info("🔗 开始从Consul注销所有服务...")
        
        try:
            if not self.consul_manager:
                self.logger.warning("Consul集成未初始化，无法注销服务")
                return False
            
            for service_name, service_info in self.running_services.items():
                try:
                    self.consul_manager.on_service_stopped(service_name, service_info)
                    self.logger.info(f"✅ 服务已从Consul注销: {service_name}")
                except Exception as e:
                    self.logger.warning(f"从Consul注销服务失败 {service_name}: {e}")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ 服务从Consul注销失败: {e}")
            return False
    
    def consul_discover_services(self) -> List[Dict]:
        """从Consul发现服务"""
        self.logger.info("🔍 从Consul发现服务...")
        
        if not self.consul_manager:
            self.logger.warning("Consul集成未初始化，无法发现服务")
            return []
        
        try:
            # 先尝试列出已注册的服务
            services = self.consul_manager.registry.list_services()
            self.logger.info(f"✅ 从Consul发现服务: {len(services)} 个服务")
            
            return [
                {
                    "name": service.name,
                    "id": service.service_id,
                    "host": service.host,
                    "port": service.port,
                    "tags": service.tags,
                    "meta": service.meta
                } 
                for service in services
            ]
        except Exception as e:
            self.logger.warning(f"从Consul发现服务失败: {e}")
            return []
    
    def _register_services_to_consul(self, services: Dict[str, Dict]):
        """向Consul注册服务"""
        if not self.consul_manager:
            return
        
        for service_name, service_info in services.items():
            try:
                self.consul_manager.on_service_started(service_name, service_info)
            except Exception as e:
                self.logger.warning(f"向Consul注册服务失败 {service_name}: {e}")
    
    def _deregister_services_from_consul(self, services: Dict[str, Dict]):
        """从Consul注销服务"""
        if not self.consul_manager:
            return
        
        for service_name, service_info in services.items():
            try:
                self.consul_manager.on_service_stopped(service_name, service_info)
            except Exception as e:
                self.logger.warning(f"从Consul注销服务失败 {service_name}: {e}")
    
    def _get_consul_status(self) -> Dict:
        """获取Consul状态信息"""
        consul_status = {
            "available": False,
            "auto_register": False,
            "registered_services": [],
            "discovered_services": []
        }
        
        if not self.consul_manager:
            return consul_status
        
        try:
            consul_status["available"] = self.consul_manager.registry.is_available()
            consul_status["auto_register"] = self.consul_manager.auto_register
            
            if consul_status["available"]:
                # 获取已注册的服务
                registered_services = self.consul_manager.registry.list_services()
                consul_status["registered_services"] = [
                    {
                        "name": service.name,
                        "id": service.service_id,
                        "host": service.host,
                        "port": service.port
                    } 
                    for service in registered_services
                ]
                
                # 获取发现的服务
                discovered_services = self.consul_manager.registry.discover_services()
                consul_status["discovered_services"] = [
                    {
                        "name": service.name,
                        "id": service.service_id,
                        "host": service.host,
                        "port": service.port
                    } 
                    for service in discovered_services
                ]
        except Exception as e:
            self.logger.warning(f"获取Consul状态失败: {e}")
        
        return consul_status

    def restart_all_services(self) -> bool:
        """重启所有服务"""
        self.logger.info("🔄 重启所有服务...")
        
        # 先停止，再启动
        if self.stop_all_services():
            # 等待一段时间确保服务完全停止
            time.sleep(3)
            return self.start_all_services()
        
        return False


def print_status(status: Dict):
    """格式化打印服务状态"""
    print("\n" + "=" * 60)
    print("📊 外部服务状态")
    print("=" * 60)
    
    print(f"总服务数: {status['total_services']}")
    print(f"检查时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['timestamp']))}")
    
    if status.get("services"):
        print("\n🔧 服务详情:")
        for service_name, service_info in status["services"].items():
            uptime = service_info.get("uptime", 0)
            uptime_str = f"{int(uptime//3600)}h {int((uptime%3600)//60)}m {int(uptime%60)}s"
            
            print(f"  • {service_name}")
            print(f"    类型: {service_info.get('type', 'unknown')}")
            print(f"    端口: {service_info.get('port', 'unknown')}")
            print(f"    状态: {service_info.get('status', 'unknown')}")
            print(f"    运行时间: {uptime_str}")
    
    if status.get("legacy_status"):
        print("\n📋 传统状态信息:")
        legacy_status = status["legacy_status"]
        if isinstance(legacy_status, dict):
            for key, value in legacy_status.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {legacy_status}")
    
    # 显示Consul状态信息
    if status.get("consul"):
        print("\n🔗 Consul集成状态:")
        consul_status = status["consul"]
        print(f"  可用性: {'✅ 可用' if consul_status['available'] else '❌ 不可用'}")
        print(f"  自动注册: {'✅ 启用' if consul_status['auto_register'] else '❌ 禁用'}")
        
        if consul_status['available']:
            registered_count = len(consul_status['registered_services'])
            discovered_count = len(consul_status['discovered_services'])
            print(f"  已注册服务数: {registered_count}")
            print(f"  发现服务数: {discovered_count}")
            
            if consul_status['registered_services']:
                print("  已注册服务:")
                for service in consul_status['registered_services']:
                    print(f"    • {service['name']} ({service['host']}:{service['port']})")
    
    print("=" * 60)


def print_consul_services(services: List[Dict]):
    """格式化打印Consul发现的服务"""
    print("\n" + "=" * 60)
    print("🔍 Consul 服务发现")
    print("=" * 60)
    
    if not services:
        print("未发现任何服务")
        print("=" * 60)
        return
    
    print(f"发现服务数: {len(services)}")
    print(f"发现时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    
    print("\n🌐 发现的服务:")
    for service in services:
        print(f"  • {service['name']}")
        print(f"    ID: {service['id']}")
        print(f"    地址: {service['host']}:{service['port']}")
        if service.get('tags'):
            print(f"    标签: {', '.join(service['tags'])}")
        if service.get('meta'):
            print(f"    元数据: {service['meta']}")
        print()
    
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="外部服务管理器 - 管理 Agent 系统的外部服务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python service_manager.py start                    # 启动所有服务
  python service_manager.py stop                     # 停止所有服务
  python service_manager.py status                   # 查看服务状态
  python service_manager.py restart                  # 重启所有服务
  python service_manager.py consul-register          # 注册服务到Consul
  python service_manager.py consul-unregister        # 从Consul注销服务
  python service_manager.py consul-discover          # 从Consul发现服务
  python service_manager.py start ollama_server      # 启动指定服务 (待实现)
  python service_manager.py stop ollama_server       # 停止指定服务 (待实现)
        """
    )
    
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'status', 'restart', 'consul-register', 'consul-unregister', 'consul-discover'],
        help='要执行的操作'
    )
    
    parser.add_argument(
        'service_name',
        nargs='?',
        help='服务名称（可选，用于操作单个服务）'
    )
    
    parser.add_argument(
        '--config',
        help='配置文件路径'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    try:
        # 创建服务管理器
        manager = ExternalServiceManager(config_path=args.config)
        
        # 执行操作
        if args.action == 'start':
            if args.service_name:
                success = manager.start_service(args.service_name)
            else:
                success = manager.start_all_services()
        
        elif args.action == 'stop':
            if args.service_name:
                success = manager.stop_service(args.service_name)
            else:
                success = manager.stop_all_services()
        
        elif args.action == 'restart':
            success = manager.restart_all_services()
        
        elif args.action == 'status':
            status = manager.get_service_status()
            print_status(status)
            success = True
        
        elif args.action == 'consul-register':
            success = manager.consul_register_all()
        
        elif args.action == 'consul-unregister':
            success = manager.consul_unregister_all()
        
        elif args.action == 'consul-discover':
            services = manager.consul_discover_services()
            print_consul_services(services)
            success = True
        
        # 返回适当的退出码
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
