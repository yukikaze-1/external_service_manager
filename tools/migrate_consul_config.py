#!/usr/bin/env python3
"""
Consul 配置迁移脚本

此脚本帮助用户从 legacy/config.yml 中移除 Consul 服务配置，
避免循环依赖问题。
"""

import yaml
import shutil
import time
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_config(config_path: Path) -> Path:
    """备份配置文件"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = config_path.with_suffix(f".backup_{timestamp}")
    shutil.copy2(config_path, backup_path)
    logger.info(f"配置文件已备份到: {backup_path}")
    return backup_path


def remove_consul_from_legacy_config():
    """从 legacy/config.yml 中移除 Consul 配置"""
    legacy_config_path = Path(__file__).parent.parent / "legacy" / "config.yml"
    
    if not legacy_config_path.exists():
        logger.warning(f"配置文件不存在: {legacy_config_path}")
        return False
    
    try:
        # 备份原配置
        backup_config(legacy_config_path)
        
        # 读取配置
        with open(legacy_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 查找并移除 Consul 配置
        consul_removed = False
        
        if 'external_services' in config:
            if 'base_services' in config['external_services']:
                base_services = config['external_services']['base_services']
                
                # 查找 Consul 配置
                new_base_services = []
                for service in base_services:
                    if isinstance(service, dict) and 'Consul' in service:
                        logger.info("找到 Consul 配置，将其移除")
                        consul_removed = True
                        # 添加注释说明
                        continue
                    else:
                        new_base_services.append(service)
                
                if consul_removed:
                    config['external_services']['base_services'] = new_base_services
        
        if consul_removed:
            # 写入更新后的配置
            with open(legacy_config_path, 'w', encoding='utf-8') as f:
                f.write("# 外部服务配置文件\n")
                f.write("# 注意: Consul 配置已移除，避免循环依赖\n")
                f.write("# Consul 现在通过主配置文件 config.yml 管理\n\n")
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info("✅ Consul 配置已从 legacy/config.yml 中移除")
            return True
        else:
            logger.info("未在 legacy/config.yml 中找到 Consul 配置")
            return True
            
    except Exception as e:
        logger.error(f"移除 Consul 配置失败: {e}")
        return False


def update_main_config_for_external_consul():
    """更新主配置文件，设置为外部 Consul 模式"""
    config_path = Path(__file__).parent.parent / "config.yml"
    
    if not config_path.exists():
        logger.warning(f"主配置文件不存在: {config_path}")
        return False
    
    try:
        # 备份原配置
        backup_config(config_path)
        
        # 读取配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新 Consul 配置
        if 'consul' not in config:
            config['consul'] = {}
        
        consul_config = config['consul']
        consul_config['enabled'] = True
        consul_config['auto_start'] = False  # 外部管理模式
        consul_config['auto_register'] = True
        consul_config.setdefault('url', 'http://127.0.0.1:8500')
        consul_config.setdefault('service_prefix', 'agent')
        
        # 写入更新后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        logger.info("✅ 主配置文件已更新为外部 Consul 模式")
        return True
        
    except Exception as e:
        logger.error(f"更新主配置文件失败: {e}")
        return False


def update_main_config_for_auto_start():
    """更新主配置文件，设置为自动启动模式"""
    config_path = Path(__file__).parent.parent / "config.yml"
    
    if not config_path.exists():
        logger.warning(f"主配置文件不存在: {config_path}")
        return False
    
    try:
        # 备份原配置
        backup_config(config_path)
        
        # 读取配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新 Consul 配置
        if 'consul' not in config:
            config['consul'] = {}
        
        consul_config = config['consul']
        consul_config['enabled'] = True
        consul_config['auto_start'] = True  # 自动启动模式
        consul_config['auto_register'] = True
        consul_config.setdefault('url', 'http://127.0.0.1:8500')
        consul_config.setdefault('service_prefix', 'agent')
        
        # 写入更新后的配置
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        logger.info("✅ 主配置文件已更新为自动启动模式")
        return True
        
    except Exception as e:
        logger.error(f"更新主配置文件失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Consul 配置迁移脚本")
    print("=" * 60)
    
    print("\n此脚本将帮助您解决 Consul 循环依赖问题。")
    print("选择部署策略：")
    print("1. 外部 Consul 模式（推荐生产环境）")
    print("2. 自动启动模式（推荐开发环境）")
    print("3. 仅移除 legacy 配置中的 Consul")
    print("4. 退出")
    
    while True:
        try:
            choice = input("\n请选择 (1-4): ").strip()
            
            if choice == '1':
                print("\n配置外部 Consul 模式...")
                if remove_consul_from_legacy_config() and update_main_config_for_external_consul():
                    print("\n✅ 外部 Consul 模式配置完成！")
                    print("\n后续步骤：")
                    print("1. 启动 Consul: consul agent -dev -client 0.0.0.0")
                    print("2. 验证 Consul: curl http://127.0.0.1:8500/v1/status/leader")
                    print("3. 启动服务管理器: python service_manager.py start_all")
                else:
                    print("❌ 配置失败")
                break
                
            elif choice == '2':
                print("\n配置自动启动模式...")
                if remove_consul_from_legacy_config() and update_main_config_for_auto_start():
                    print("\n✅ 自动启动模式配置完成！")
                    print("\n后续步骤：")
                    print("1. 直接启动服务管理器: python service_manager.py start_all")
                    print("2. 系统会自动检查并启动 Consul（如果需要）")
                else:
                    print("❌ 配置失败")
                break
                
            elif choice == '3':
                print("\n仅移除 legacy 配置中的 Consul...")
                if remove_consul_from_legacy_config():
                    print("\n✅ Consul 配置已从 legacy/config.yml 中移除")
                    print("您可以手动编辑 config.yml 选择合适的 Consul 模式")
                else:
                    print("❌ 移除失败")
                break
                
            elif choice == '4':
                print("退出配置脚本")
                break
                
            else:
                print("无效选择，请输入 1-4")
                
        except KeyboardInterrupt:
            print("\n\n用户中断，退出脚本")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            break


if __name__ == "__main__":
    main()
