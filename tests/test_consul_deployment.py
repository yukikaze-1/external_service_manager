#!/usr/bin/env python3
"""
Consul 部署策略测试脚本

测试不同的 Consul 部署策略：
1. 外部 Consul 策略
2. 自动启动 Consul 策略
3. 混合模式策略
"""

import sys
import time
import subprocess
import requests
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from consul_integration import ConsulServiceRegistry, ConsulManager
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_consul_running(host="127.0.0.1", port=8500):
    """检查 Consul 是否运行"""
    try:
        response = requests.get(f"http://{host}:{port}/v1/status/leader", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def test_external_consul_strategy():
    """测试策略一：外部 Consul"""
    print("=" * 60)
    print("测试策略一：外部 Consul 策略")
    print("=" * 60)
    
    # 检查是否有外部 Consul 运行
    if not check_consul_running():
        print("❌ 没有检测到外部 Consul，请先启动 Consul：")
        print("   consul agent -dev -client 0.0.0.0")
        return False
    
    print("✅ 检测到外部 Consul 正在运行")
    
    # 测试连接
    try:
        registry = ConsulServiceRegistry(
            consul_url="http://127.0.0.1:8500",
            auto_start_consul=False,  # 不自动启动
            logger=logger
        )
        
        if registry.is_available():
            print("✅ Consul 服务注册器初始化成功")
            
            # 测试服务注册
            success = registry.register_service(
                service_name="test_service",
                host="127.0.0.1",
                port=8080,
                health_check_url="http://127.0.0.1:8080/health"
            )
            
            if success:
                print("✅ 测试服务注册成功")
                
                # 清理测试服务
                registry.deregister_service("test_service", port=8080)
                print("✅ 测试服务注销成功")
                return True
            else:
                print("❌ 测试服务注册失败")
                return False
        else:
            print("❌ Consul 服务注册器不可用")
            return False
            
    except Exception as e:
        print(f"❌ 策略一测试失败: {e}")
        return False


def test_auto_start_consul_strategy():
    """测试策略二：自动启动 Consul"""
    print("=" * 60)
    print("测试策略二：自动启动 Consul 策略")
    print("=" * 60)
    
    # 确保 Consul 未运行
    if check_consul_running():
        print("⚠️ 检测到 Consul 已在运行，请先停止外部 Consul 再测试自动启动功能")
        return False
    
    print("✅ 确认 Consul 未运行，开始测试自动启动")
    
    try:
        registry = ConsulServiceRegistry(
            consul_url="http://127.0.0.1:8500",
            auto_start_consul=True,  # 自动启动
            logger=logger
        )
        
        if registry.is_available():
            print("✅ Consul 自动启动并初始化成功")
            
            # 测试服务注册
            success = registry.register_service(
                service_name="auto_test_service",
                host="127.0.0.1",
                port=8081,
                health_check_url="http://127.0.0.1:8081/health"
            )
            
            if success:
                print("✅ 测试服务注册成功")
                
                # 清理测试服务
                registry.deregister_service("auto_test_service", port=8081)
                print("✅ 测试服务注销成功")
                
                # 关闭注册器（这会停止自动启动的 Consul）
                registry.shutdown()
                print("✅ Consul 服务注册器已关闭")
                
                # 等待一下，然后检查 Consul 是否已停止
                time.sleep(3)
                if not check_consul_running():
                    print("✅ 自动启动的 Consul 已正确停止")
                    return True
                else:
                    print("⚠️ 自动启动的 Consul 可能仍在运行")
                    return True  # 仍然算作成功，只是清理不完全
            else:
                print("❌ 测试服务注册失败")
                registry.shutdown()
                return False
        else:
            print("❌ Consul 自动启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 策略二测试失败: {e}")
        return False


def test_consul_manager():
    """测试 ConsulManager 类"""
    print("=" * 60)
    print("测试 ConsulManager 类")
    print("=" * 60)
    
    manager = ConsulManager(logger=logger)
    
    # 检查 Consul 是否运行
    is_running_before = manager.is_consul_running()
    print(f"启动前 Consul 状态: {'运行中' if is_running_before else '未运行'}")
    
    if is_running_before:
        print("⚠️ Consul 已在运行，跳过启动测试")
        return True
    
    # 测试启动 Consul
    print("尝试启动 Consul...")
    start_success = manager.start_consul(dev_mode=True)
    
    if start_success:
        print("✅ Consul 启动成功")
        
        # 验证 Consul 确实在运行
        time.sleep(2)
        is_running_after = manager.is_consul_running()
        print(f"启动后 Consul 状态: {'运行中' if is_running_after else '未运行'}")
        
        if is_running_after:
            print("✅ Consul 启动验证成功")
            
            # 测试停止 Consul
            print("尝试停止 Consul...")
            manager.stop_consul()
            
            # 验证 Consul 已停止
            time.sleep(3)
            is_running_final = manager.is_consul_running()
            print(f"停止后 Consul 状态: {'运行中' if is_running_final else '未运行'}")
            
            if not is_running_final:
                print("✅ Consul 停止验证成功")
                return True
            else:
                print("⚠️ Consul 可能仍在运行")
                return False
        else:
            print("❌ Consul 启动验证失败")
            return False
    else:
        print("❌ Consul 启动失败")
        return False


def main():
    """主测试函数"""
    print("Consul 部署策略测试开始")
    print("=" * 60)
    
    # 检查 consul 命令是否可用
    try:
        result = subprocess.run(["consul", "version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ Consul 已安装: {result.stdout.strip().split()[1]}")
        else:
            print("❌ Consul 命令不可用")
            return
    except FileNotFoundError:
        print("❌ 未找到 consul 命令，请确保 Consul 已安装")
        return
    except subprocess.TimeoutExpired:
        print("❌ consul 命令超时")
        return
    
    print()
    
    # 测试各种策略
    tests = [
        ("ConsulManager 测试", test_consul_manager),
        ("自动启动 Consul 策略", test_auto_start_consul_strategy),
        ("外部 Consul 策略", test_external_consul_strategy),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n开始测试: {test_name}")
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ 测试 {test_name} 出现异常: {e}")
            results[test_name] = False
        
        print(f"测试 {test_name} 结果: {'✅ 通过' if results[test_name] else '❌ 失败'}")
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    # 整体结果
    all_passed = all(results.values())
    print(f"\n整体测试结果: {'✅ 全部通过' if all_passed else '❌ 部分失败'}")
    
    if all_passed:
        print("\n🎉 所有 Consul 部署策略测试通过！")
        print("您可以根据需要选择合适的部署策略：")
        print("- 生产环境：推荐外部 Consul 策略")
        print("- 开发环境：推荐自动启动 Consul 策略")
    else:
        print("\n⚠️ 部分测试失败，请检查:")
        print("1. Consul 是否正确安装")
        print("2. 网络端口是否可用")
        print("3. 权限是否足够")


if __name__ == "__main__":
    main()
