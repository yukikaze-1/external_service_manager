#!/usr/bin/env python3
"""
Consul集成快速测试脚本
"""

import sys
import os
sys.path.insert(0, '.')

def test_consul_integration():
    try:
        from consul_integration import ConsulServiceRegistry
        
        print("=== Consul服务注册器测试 ===")
        registry = ConsulServiceRegistry()
        
        print(f"Consul可用性: {registry.is_available()}")
        
        if registry.is_available():
            services = registry.list_services()
            print(f"发现服务数量: {len(services)}")
            
            for service in services:
                print(f"  • {service.name}")
                print(f"    ID: {service.service_id}")
                print(f"    地址: {service.host}:{service.port}")
                print(f"    标签: {service.tags}")
                print()
        else:
            print("Consul不可用，无法测试")
            
        return True
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_consul_integration()
