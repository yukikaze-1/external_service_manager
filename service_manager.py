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

# 旧的 `legacy` 实现已弃用。这里提供一个最小的替代实现
# NewExternalServiceManager 提供 init_services/stop_all_services/get_service_status
# 的最小功能，足以让 CLI 在移除 legacy 之后继续工作。
import subprocess
import shlex
import signal


class NewExternalServiceManager:
    """最小化的外部服务管理器替代实现

    特性：
    - 读取 `Init/ExternalServiceInit/config.yml` 或仓库根 `config.yml` 中的 external_services
    - 启动后台服务（使用简单的 subprocess.Popen）
    - 停止已启动的服务（通过进程组 SIGTERM -> SIGKILL）
    - 返回基本的服务状态信息
    注意：此实现不包含复杂的重试/健康检查/配置验证逻辑。
    """

    def __init__(self):
        self.base_processes = []  # List[Tuple[name, Popen]]
        self.optional_processes = []
        self.config = {}

    def _load_config(self):
        project_root = Path(__file__).parent
        cfg_path = Path(os.environ.get('AGENT_HOME', project_root)) / "Init" / "ExternalServiceInit" / "config.yml"
        if not cfg_path.exists():
            cfg_path = project_root / "config.yml"

        if not cfg_path.exists():
            self.config = {'external_services': {'base_services': [], 'optional_services': []}}
            return

        import yaml
        try:
            with open(cfg_path, 'r', encoding='utf-8') as f:
                full = yaml.safe_load(f) or {}
                self.config = full.get('external_services', full)
        except Exception:
            self.config = {'external_services': {'base_services': [], 'optional_services': []}}

    def _start_service_from_config(self, svc_item, is_base: bool, state_dict=None):
        # svc_item 通常是 {name: config}
        try:
            if isinstance(svc_item, dict) and len(svc_item) == 1:
                svc_name = list(svc_item.keys())[0]
                svc_conf = svc_item[svc_name]
            elif isinstance(svc_item, dict) and 'service_name' in svc_item:
                svc_name = svc_item.get('service_name')
                svc_conf = svc_item
            else:
                return ("unknown", -1)

            script = svc_conf.get('script')
            args = svc_conf.get('args', []) or []
            use_python = svc_conf.get('use_python', False)
            conda_env = svc_conf.get('conda_env', '')
            run_bg = svc_conf.get('run_in_background', True)

            if use_python and conda_env and script:
                python_bin = os.path.join(conda_env, 'bin', 'python')
                cmd = [python_bin, script] + args
                shell = False
            else:
                if isinstance(script, str):
                    cmd = [script] + args
                    shell = True
                else:
                    return (svc_name, -1)

            cwd = None
            if isinstance(script, str) and os.path.isabs(script):
                cwd = os.path.dirname(script) or None

            # 自动从 args 里提取端口号
            def extract_port(args_list):
                port = None
                for i, a in enumerate(args_list):
                    if a in ('-p', '--port') and i + 1 < len(args_list):
                        try:
                            port_candidate = args_list[i + 1]
                            if isinstance(port_candidate, str) and port_candidate.isdigit():
                                port = int(port_candidate)
                        except Exception:
                            continue
                return port

            port = extract_port(args)
            # 兜底：部分服务端口写死
            if not port and svc_name == 'ollama_server':
                port = 11434
            if not port and svc_name == 'Consul':
                port = 8500

            if run_bg:
                if shell:
                    proc = subprocess.Popen(' '.join(shlex.quote(a) for a in cmd), shell=True,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             preexec_fn=os.setsid, cwd=cwd)
                else:
                    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                             preexec_fn=os.setsid, cwd=cwd)

                pid = proc.pid
                if is_base:
                    self.base_processes.append((svc_name, proc))
                else:
                    self.optional_processes.append((svc_name, proc))

                # 记录 pid 和端口到 state_dict
                if state_dict is not None:
                    state_dict[svc_name] = {
                        'pid': pid,
                        'start_time': time.time(),
                        'script': script,
                        'args': args,
                        'cwd': cwd,
                        'port': port
                    }

                return (svc_name, pid)
            else:
                # 前台运行：同步执行
                if shell:
                    subprocess.run(' '.join(shlex.quote(a) for a in cmd), shell=True, check=True, cwd=cwd)
                else:
                    subprocess.run(cmd, check=True, cwd=cwd)
                return (svc_name, -1)

        except Exception:
            return (svc_name if 'svc_name' in locals() else 'unknown', -1)

    def init_services(self, state_dict=None):
        self._load_config()
        base_cfg = self.config.get('base_services', [])
        optional_cfg = self.config.get('optional_services') or []

        base_results = []
        optional_results = []

        for item in base_cfg:
            base_results.append(self._start_service_from_config(item, True, state_dict=state_dict))

        for item in optional_cfg:
            optional_results.append(self._start_service_from_config(item, False, state_dict=state_dict))

        return base_results, optional_results

    def stop_all_services(self):
        # 停止可选服务
        for name, proc in self.optional_processes.copy():
            try:
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass

        # 停止基础服务
        for name, proc in self.base_processes.copy():
            try:
                if proc.poll() is None:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                pass

        self.base_processes.clear()
        self.optional_processes.clear()

    def get_service_status(self):
        base_status = []
        for name, proc in self.base_processes:
            base_status.append({
                'name': name,
                'pid': proc.pid,
                'status': 'running' if proc.poll() is None else 'stopped'
            })

        optional_status = []
        for name, proc in self.optional_processes:
            optional_status.append({
                'name': name,
                'pid': proc.pid,
                'status': 'running' if proc.poll() is None else 'stopped'
            })

        return {'base_services': base_status, 'optional_services': optional_status}

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
        
        # 初始化新的最小化外部服务管理器（替代 legacy）
        try:
            self.manager = NewExternalServiceManager()
            self.logger.info("✅ 外部服务管理器（新实现）初始化成功")
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
        
        # 不修改 Consul registry 的析构行为，避免在运行时意外停止 Consul 进程。
        # 如果需要持久化注册，请通过配置或显式调用注册/注销接口来控制。
    
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
        
        # 如果目标配置文件不存在，使用仓库根目录的配置文件作为回退
        if not target_config.exists():
            local_config = Path(__file__).parent / "config.yml"
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
            # 优先从 Init/ExternalServiceInit/config.yml 查找配置，回退到仓库根 config.yml
            config_file = Path(__file__).parent / "Init" / "ExternalServiceInit" / "config.yml"
            if not config_file.exists():
                config_file = Path(__file__).parent / "config.yml"

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
            # 新增：启动时记录详细进程信息
            self.running_services = {}
            base_results, optional_results = self.manager.init_services(state_dict=self.running_services)

            # 丰富运行时信息：类型、端口、状态
            try:
                import psutil
            except Exception:
                psutil = None

            # helper to set fields
            def _enrich(name, pid, svc_type):
                entry = self.running_services.get(name, {})
                entry.setdefault('pid', pid)
                entry['type'] = svc_type
                # 端口优先从配置获取
                try:
                    port = self._get_service_port_from_config(name)
                except Exception:
                    port = None
                # 如果端口获取失败，尝试从 entry 里找
                if not port:
                    port = entry.get('port')
                # 如果端口依然无效，警告并设置为 None
                if not port or port == 'unknown':
                    self.logger.warning(f"服务 {name} 缺少有效端口信息，Consul 注册可能失败！")
                    port = None
                entry['port'] = port

                # 状态：检查 pid 是否存活
                status = 'stopped'
                if pid and pid > 0 and psutil is not None:
                    try:
                        p = psutil.Process(pid)
                        status = 'running' if p.is_running() and p.status() != psutil.STATUS_ZOMBIE else 'stopped'
                    except Exception:
                        status = 'stopped'
                elif pid and pid > 0:
                    # 没有 psutil 的退路：尝试 os.kill 0
                    try:
                        os.kill(pid, 0)
                        status = 'running'
                    except Exception:
                        status = 'stopped'

                entry['status'] = status
                self.running_services[name] = entry

            for name, pid in (base_results or []):
                _enrich(name, pid, 'base')
            for name, pid in (optional_results or []):
                _enrich(name, pid, 'optional')

            self._save_service_state()
            self.logger.info(f"✅ 服务启动完成！共启动 {len(self.running_services)} 个服务")
            # 启动后自动注册到 Consul
            if self.consul_manager:
                try:
                    self.logger.info("🔗 启动后自动注册所有服务到 Consul...")
                    self.consul_register_all()
                except Exception as e:
                    self.logger.warning(f"自动注册到 Consul 失败: {e}")
            else:
                self.logger.info("Consul 集成未启用，跳过注册步骤")
            return True
        except Exception as e:
            self.logger.error(f"❌ 服务启动失败: {e}")
            return False
    
    # def stop_all_services(self) -> bool:
    #     """停止所有服务"""
    #     self.logger.info("🛑 开始停止所有外部服务...")
        
    #     try:
    #         # Consul集成：注销服务
    #         if self.consul_manager and self.running_services:
    #             self.logger.info("🔗 开始从Consul注销服务...")
    #             self._deregister_services_from_consul(self.running_services)
            
    #         # 使用新管理器停止服务
    #         if hasattr(self, 'manager') and hasattr(self.manager, 'stop_all_services'):
    #             self.manager.stop_all_services()
    #         else:
    #             self.logger.warning("管理器不支持停止服务功能")
            
    #         # 清空状态
    #         stopped_count = len(self.running_services)
    #         self.running_services.clear()
    #         self._save_service_state()
            
    #         self.logger.info(f"✅ 服务停止完成！共停止 {stopped_count} 个服务")
    #         return True
            
    #     except Exception as e:
    #         self.logger.error(f"❌ 服务停止失败: {e}")
    #         return False
    
    def get_service_status(self) -> Dict:
        """获取服务状态"""
        status = {
            "timestamp": time.time(),
            "total_services": len(self.running_services),
            "services": {}
        }
        
        # 获取详细状态
        try:
            if hasattr(self, 'manager') and hasattr(self.manager, 'get_service_status'):
                legacy_status = self.manager.get_service_status()
                status["legacy_status"] = legacy_status
        except Exception as e:
            self.logger.warning(f"获取管理器状态失败: {e}")
        
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

    def stop_all_services(self) -> bool:
        """停止所有服务（递归 kill 进程树，确保彻底杀死）"""
        self.logger.info("🛑 开始停止所有外部服务...")
        try:
            # Consul集成：注销服务
            if self.consul_manager and self.running_services:
                self.logger.info("🔗 开始从Consul注销服务...")
                self._deregister_services_from_consul(self.running_services)

            # Prefer using psutil for reliable process inspection and termination.
            try:
                import psutil
            except Exception:
                psutil = None

            killed = 0

            if psutil is None:
                self.logger.warning("psutil 未安装，无法按命令或端口精确匹配进程；将调用管理器的 stop_all_services() 作为退路")
            # 遍历已记录的服务，尝试多种方式终止
            for svc_name, info in list(self.running_services.items()):
                pid = info.get('pid')
                stopped = False

                # 方式1：按照记录的 pid 终止
                if pid and psutil is not None:
                    try:
                        p = psutil.Process(pid)
                        children = p.children(recursive=True)
                        for child in children:
                            try:
                                child.terminate()
                            except Exception:
                                pass
                        try:
                            p.terminate()
                        except Exception:
                            pass
                        gone, alive = psutil.wait_procs([p] + children, timeout=3)
                        for proc in alive:
                            try:
                                proc.kill()
                            except Exception:
                                pass
                        stopped = True
                        killed += 1
                        self.logger.info(f"已基于 pid 终止服务 {svc_name} (pid={pid})")
                    except psutil.NoSuchProcess:
                        self.logger.info(f"记录的 pid 不存在: {svc_name} (pid={pid})，将尝试按命令/端口匹配")
                    except Exception as e:
                        self.logger.warning(f"按 pid 终止服务失败 {svc_name} (pid={pid}): {e}")

                # 方式2：按命令行或服务名或端口匹配进程
                if not stopped and psutil is not None:
                    try:
                        script = info.get('script') or ''
                        port = None
                        try:
                            # port 可能是 'unknown' 或字符串
                            pval = info.get('port')
                            if isinstance(pval, int):
                                port = pval
                            elif isinstance(pval, str) and pval.isdigit():
                                port = int(pval)
                        except Exception:
                            port = None

                        candidates = []
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            try:
                                cmdline_list = proc.info.get('cmdline') or []
                                cmdline = ' '.join(cmdline_list)
                                pname = proc.info.get('name') or ''

                                matched = False
                                if script and script in cmdline:
                                    matched = True
                                if not matched and svc_name and (svc_name in pname or svc_name in cmdline):
                                    matched = True

                                # 检查端口监听
                                if not matched and port:
                                    try:
                                        for c in proc.connections(kind='inet'):
                                            laddr = c.laddr
                                            if laddr and getattr(laddr, 'port', None) == port:
                                                matched = True
                                                break
                                    except Exception:
                                        pass

                                if matched:
                                    candidates.append(proc)
                            except Exception:
                                continue

                        if candidates:
                            for proc in candidates:
                                try:
                                    children = proc.children(recursive=True)
                                    for child in children:
                                        try:
                                            child.terminate()
                                        except Exception:
                                            pass
                                    try:
                                        proc.terminate()
                                    except Exception:
                                        pass
                                    gone, alive = psutil.wait_procs([proc] + children, timeout=3)
                                    for pleft in alive:
                                        try:
                                            pleft.kill()
                                        except Exception:
                                            pass
                                    killed += 1
                                    stopped = True
                                    self.logger.info(f"通过命令/端口匹配终止服务 {svc_name} (pid={proc.pid})")
                                except Exception as e:
                                    self.logger.warning(f"通过命令/端口终止进程失败 {svc_name} (pid={proc.pid}): {e}")
                        else:
                            self.logger.warning(f"无法找到匹配的进程以终止 {svc_name} (pid={pid})")
                    except Exception as e:
                        self.logger.warning(f"尝试按命令或端口匹配终止 {svc_name} 失败: {e}")

                # 记录停止失败也继续循环，最后统一调用 manager 的 stop_all_services 作为额外保障

            # 使用新管理器停止本进程内的服务（如果它在本次运行中启动过）
            if hasattr(self, 'manager') and hasattr(self.manager, 'stop_all_services'):
                try:
                    self.manager.stop_all_services()
                except Exception as e:
                    self.logger.warning(f"调用内部管理器停止服务失败: {e}")
            else:
                self.logger.warning("管理器不支持停止服务功能")

            stopped_count = len(self.running_services)
            self.running_services.clear()
            self._save_service_state()

            self.logger.info(f"✅ 服务停止完成！共停止 {stopped_count} 个服务，尝试终止 {killed} 个进程或进程树")
            return True

        except Exception as e:
            self.logger.error(f"❌ 服务停止失败: {e}")
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
        
        # elif args.action == 'restart':
        #     success = manager.restart_all_services()
        
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
