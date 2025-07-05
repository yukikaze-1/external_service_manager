#!/usr/bin/env python3
"""
测试独立外部服务管理器项目
"""

import sys
import os
from pathlib import Path

def test_dependencies():
    """测试依赖模块"""
    print("🔍 测试依赖模块...")
    try:
        from Module.Utils.Logger import setup_logger
        from Module.Utils.ConfigTools import load_config
        print("✅ 依赖模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 依赖模块导入失败: {e}")
        return False

def test_legacy_import():
    """测试传统管理器导入"""
    print("🔍 测试传统管理器导入...")
    try:
        from legacy.core import ExternalServiceManager
        print("✅ 传统管理器导入成功")
        return True
    except ImportError as e:
        print(f"❌ 传统管理器导入失败: {e}")
        return False

def test_main_manager():
    """测试主服务管理器"""
    print("🔍 测试主服务管理器...")
    try:
        from service_manager import ExternalServiceManager
        print("✅ 主服务管理器导入成功")
        return True
    except ImportError as e:
        print(f"❌ 主服务管理器导入失败: {e}")
        return False

def test_files_exist():
    """测试必要文件是否存在"""
    print("🔍 检查必要文件...")
    current_dir = Path(__file__).parent
    
    required_files = [
        "service_manager.py",
        "manage_services.sh", 
        "requirements.txt",
        "setup.py",
        "legacy/config.yml",
        "Module/Utils/Logger.py",
        "Module/Utils/ConfigTools.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (current_dir / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    else:
        print("✅ 所有必要文件都存在")
        return True

def main():
    print("🚀 开始测试独立外部服务管理器项目...")
    
    tests = [
        test_files_exist,
        test_dependencies,
        test_legacy_import,
        test_main_manager
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{len(tests)} 通过")
    
    if passed == len(tests):
        print("🎉 所有测试通过！项目可以独立运行。")
        return True
    else:
        print("❌ 部分测试失败，请检查项目配置。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
