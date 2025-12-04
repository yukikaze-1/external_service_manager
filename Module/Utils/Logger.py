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
from typing import Optional
from dotenv import dotenv_values
from pathlib import Path


def setup_logger(name: str, log_path: str = "Log") -> logging.Logger:
    """
    配置并返回一个日志记录器
    """
    # 优先读取 .env 中的 LOG_DIR，其次读取环境变量 LOG_DIR，最后回退到 ${AGENT_HOME}/Log
    agent_home = os.environ.get('AGENT_HOME', '.')
    env_path = os.path.join(agent_home, 'Module', 'Utils', '.env')
    env_vars = dotenv_values(env_path) if os.path.exists(env_path) else {}
    configured_log_dir = env_vars.get("LOG_DIR") or os.environ.get("LOG_DIR")

    if configured_log_dir:
        base_log_dir = configured_log_dir
    else:
        base_log_dir = os.path.join(agent_home, 'Log')

    # 如果用户传入的 log_path 是 'Log'，使用 base_log_dir，否则将其作为子目录
    if log_path and log_path != 'Log':
        _log_path = os.path.join(base_log_dir, log_path)
    else:
        _log_path = base_log_dir

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

