#!/usr/bin/env python3
"""
项目独立化完成验证脚本
"""

import os
import sys
from pathlib import Path

def cleanup_extra_dirs():
    """清理多余的目录"""
    current_dir = Path(__file__).parent
    extra_dirs = ["ExternalService", "Log", "Tools", "Other"]
    
    for dir_name in extra_dirs:
        dir_path = current_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"🧹 清理多余目录: {dir_name}")
            import shutil
            shutil.rmtree(str(dir_path))

def verify_structure():
    """验证项目结构"""
    current_dir = Path(__file__).parent
    
    expected_structure = {
        "files": [
            "service_manager.py",
            "manage_services.sh",
            "README.md",
            "requirements.txt",
            "setup.py",
            "LICENSE",
            ".gitignore",
            "MANIFEST.in",
            "__init__.py"
        ],
        "dirs": [
            "Module/Utils",
            # legacy 已弃用并会被删除
        ]
    }
    
    print("🔍 验证项目结构...")
    
    # 检查文件
    missing_files = []
    for file_name in expected_structure["files"]:
        if not (current_dir / file_name).exists():
            missing_files.append(file_name)
    
    # 检查目录
    missing_dirs = []
    for dir_path in expected_structure["dirs"]:
        if not (current_dir / dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    
    if missing_dirs:
        print(f"❌ 缺少目录: {missing_dirs}")
        return False
    
    print("✅ 项目结构正确")
    return True

def main():
    print("🚀 独立化项目验证和清理...")
    
    # 清理多余目录
    cleanup_extra_dirs()
    
    # 验证结构
    if verify_structure():
        print("\n🎉 项目独立化完成！")
        print("\n📁 最终项目结构:")
        print("ExternalServiceManager/")
        print("├── service_manager.py       # 主服务管理器")
        print("├── manage_services.sh       # Bash便捷脚本")
        print("├── README.md               # 项目文档")
        print("├── requirements.txt        # Python依赖")
        print("├── setup.py               # 安装脚本") 
        print("├── LICENSE                # MIT许可证")
        print("├── .gitignore             # Git忽略文件")
        print("├── MANIFEST.in            # 打包清单")
        print("├── __init__.py            # 包初始化")
        print("├── Module/                # 依赖模块")
        print("│   └── Utils/")
        print("│       ├── Logger.py")
        print("│       └── ConfigTools.py")
        print("└── (legacy 已弃用)")
        print("\n🎯 现在可以将此目录移动到任何地方并独立运行！")
        print("\n使用方法:")
        print("  python service_manager.py --help")
        print("  ./manage_services.sh help")
        return True
    else:
        print("❌ 项目结构验证失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
