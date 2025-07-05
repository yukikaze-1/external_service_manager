"""
ExternalServiceInit 核心模块
"""

# 兼容的导入方式
try:
    from .service_manager import ExternalServiceManager
except ImportError:
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from service_manager import ExternalServiceManager

__all__ = ['ExternalServiceManager']
