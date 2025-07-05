#!/usr/bin/env python3
"""
完整的 Consul 集成工作流程测试

测试从服务启动到Consul注册的完整流程
"""

import sys
import time
import subprocess
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n📋 {description}")
    print(f"💻 命令: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.stdout:
            print("✅ 输出:")
            print(result.stdout)
        
        if result.stderr:
            print("⚠️ 错误:")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - 成功")
            return True
        else:
            print(f"❌ {description} - 失败 (退出码: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - 超时")
        return False
    except Exception as e:
        print(f"❌ {description} - 异常: {e}")
        return False

def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 Consul 集成完整工作流程测试")
    print("=" * 60)
    
    # Python命令前缀
    python_cmd = "conda run -p /home/yomu/data/anaconda3 --no-capture-output python"
    
    tests = [
        # 1. 检查配置
        (f"{python_cmd} -c \"import yaml; print('✅ YAML配置支持正常')\"", 
         "检查 YAML 配置支持"),
        
        # 2. 检查 Consul 集成模块
        (f"{python_cmd} -c \"from consul_integration import ConsulServiceRegistry; print('✅ Consul集成模块正常')\"",
         "检查 Consul 集成模块"),
        
        # 3. 测试服务状态
        (f"{python_cmd} service_manager.py status",
         "检查当前服务状态"),
        
        # 4. 测试 Consul 发现（会自动启动 Consul）
        (f"{python_cmd} service_manager.py consul-discover",
         "测试 Consul 服务发现（含自动启动）"),
        
        # 5. 注册所有服务到 Consul
        (f"{python_cmd} service_manager.py consul-register",
         "注册所有服务到 Consul"),
        
        # 6. 再次检查服务发现
        (f"{python_cmd} service_manager.py consul-discover",
         "再次检查 Consul 服务发现"),
        
        # 7. 注销服务
        (f"{python_cmd} service_manager.py consul-unregister", 
         "从 Consul 注销所有服务")
    ]
    
    # 运行测试
    results = []
    for cmd, desc in tests:
        success = run_command(cmd, desc)
        results.append((desc, success))
        
        # 在某些步骤后稍作等待
        if "Consul" in desc:
            time.sleep(2)
    
    # 输出测试结果总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    all_passed = True
    for desc, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{desc}: {status}")
        if not success:
            all_passed = False
    
    print(f"\n🎯 整体结果: {'✅ 全部通过' if all_passed else '❌ 部分失败'}")
    
    if all_passed:
        print("\n🎉 恭喜！Consul 集成完全正常工作！")
        print("\n📋 您现在可以：")
        print("1. 使用外部 Consul 模式（生产环境推荐）")
        print("2. 使用自动启动模式（开发环境推荐）")
        print("3. 自动服务注册和发现")
        print("4. 健康检查监控")
        print("\n🔧 常用命令：")
        print("- python service_manager.py consul-register   # 注册服务")
        print("- python service_manager.py consul-discover   # 发现服务")
        print("- python service_manager.py consul-unregister # 注销服务")
        print("- python service_manager.py status            # 查看状态")
    else:
        print("\n⚠️ 部分测试失败，请检查:")
        print("1. Python 环境配置")
        print("2. 依赖包安装 (python-consul, pyyaml)")
        print("3. Consul 是否正确安装")
        print("4. 网络和权限设置")

if __name__ == "__main__":
    main()
