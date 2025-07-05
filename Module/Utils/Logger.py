# Project:      Agent
# Author:       yomu
# Time:         2024/12/23
# Version:      0.1
# Description:  agent logger module

"""
    负责产生一个Logger并将其返回
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import Literal
from dotenv import dotenv_values

def setup_logger(name: str, log_path: Literal['ExternalService', 'InternalModule', 'Other'])->logging.Logger:
    """
    配置并返回一个日志记录器
    """
    env_vars = dotenv_values("${AGENT_HOME}/Module/Utils/.env")
    log_dir: str = env_vars.get("LOG_DIR", "") 
    _log_path: str = os.path.join(log_dir, log_path)
    os.makedirs(_log_path, exist_ok=True) 
    # 创建日志处理器
    file_handler = TimedRotatingFileHandler(f"{_log_path}/logger_{name}.log", when="midnight", interval=1, encoding="utf-8")
    file_handler.suffix = "%Y-%m-%d"
    
    # 创建日志格式
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(logging.StreamHandler())  # 控制台输出

    return logger

