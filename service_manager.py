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
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
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
    
    def start_all_services(self) -> bool:
        """启动所有服务"""
        self.logger.info("🚀 开始启动所有外部服务...")
        
        try:
            # 使用传统管理器启动服务
            base_services, optional_services = self.legacy_manager.init_services()
            
            # 记录启动的服务
            started_services = {}
            
            if base_services:
                for name, port in base_services:
                    started_services[name] = {
                        "type": "base",
                        "port": port,
                        "start_time": time.time(),
                        "status": "running"
                    }
                self.logger.info(f"✅ 基础服务启动成功: {[name for name, _ in base_services]}")
            
            if optional_services:
                for name, port in optional_services:
                    started_services[name] = {
                        "type": "optional", 
                        "port": port,
                        "start_time": time.time(),
                        "status": "running"
                    }
                self.logger.info(f"✅ 可选服务启动成功: {[name for name, _ in optional_services]}")
            
            # 更新状态
            self.running_services.update(started_services)
            self._save_service_state()
            
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
  python service_manager.py start ollama_server      # 启动指定服务 (待实现)
  python service_manager.py stop ollama_server       # 停止指定服务 (待实现)
        """
    )
    
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'status', 'restart'],
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
