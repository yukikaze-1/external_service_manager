#!/usr/bin/env python3

import sys
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from consul_integration import ConsulServiceRegistry

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auto_start():
    print("测试自动启动 Consul...")
    
    try:
        registry = ConsulServiceRegistry(
            auto_start_consul=True,
            logger=logger
        )
        
        if registry.is_available():
            print("✅ Consul 自动启动成功")
            
            # 测试服务注册
            success = registry.register_service(
                service_name="auto_test",
                host="127.0.0.1",
                port=9999
            )
            
            if success:
                print("✅ 服务注册成功")
                registry.deregister_service("auto_test", port=9999)
                print("✅ 服务注销成功")
            
            # 关闭注册器
            registry.shutdown()
            print("✅ 注册器已关闭")
            
        else:
            print("❌ Consul 自动启动失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_auto_start()
