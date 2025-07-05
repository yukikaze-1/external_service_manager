# Project:      Agent
# Author:       yomu
# Time:         2024/12/27
# Version:      0.1
# Description:  load config

"""
    1. load_config负责从指定yml文件读取配置信息
    2. validate_config负责验证配置文件是否包含所有必需的配置项
"""

import yaml
from typing import Optional
from pathlib import Path
from typing import Dict, Any, List
from logging import Logger


def load_config(config_path: Optional[str], config_name: str, logger: Logger) -> Dict[str, Any]:
        """
        从 config_path 中读取指定的配置 (YAML 文件).

        参数:
            config_path (str): 配置文件的路径。
            config_name (str): 配置项的名称。
            logger (Logger): 用于记录日志的 Logger 实例。

        返回:
            Dict[str, Any]: 指定配置项的字典表示。

        异常:
            ValueError: 当 config_path 为空或 YAML 文件内容为空时。
            FileNotFoundError: 当配置文件不存在或路径不正确时。
            KeyError: 当指定的 config_name 不存在于 YAML 文件中时。
            TypeError: 当指定的 config_name 对应的内容不是字典时。
            yaml.YAMLError: 当 YAML 文件解析出错时。
        """
        # 检查 _config_path 是否为空
        if not config_path:
            logger.error("Config path is empty.")
            raise ValueError("Config path is empty.")
        
        _config_path: Path = Path(config_path)
        
        # 检查配置文件是否存在且是一个文件
        if not _config_path.is_file():
            logger.error(f"Config file '{_config_path}' is empty.")
            raise ValueError(f"Config file '{_config_path}' is empty.")
        
        try:
            with open(_config_path, 'r', encoding='utf-8') as file:
                config: Dict = yaml.safe_load(file)  # 使用 safe_load 安全地加载 YAML 数据
                
                if config is None:
                    logger.error(f"The YAML config file {_config_path} is empty.")
                    raise ValueError(f"The YAML config file {_config_path} is empty.")
                
                res = config.get(config_name, {})
                
                if res is None:
                    logger.error(f"Config name '{config_name}' not found in '{_config_path}'.")
                    raise KeyError(f"Config name '{config_name}' not found in '{_config_path}'.")
                
                if not isinstance(res, dict):
                    logger.error(f"Config '{config_name}' is not a dictionary.")
                    raise TypeError(f"Config '{config_name}' is not a dictionary.")
                
                return res
        
        except FileNotFoundError as e:
            logger.error(f"Config file '{_config_path}' was not found during file opening.")
            raise FileNotFoundError(f"Config file '{_config_path}' was not found during file opening.") from e
        
        except yaml.YAMLError as e:
            logger.error(f"Error parsing the YAML config file: {e}")
            raise ValueError(f"Error parsing the YAML config file '{_config_path}': {e}") from e 



def validate_config(required_keys: List[str], config: Dict, logger: Logger):
    """
    验证配置字典是否包含所有必需的配置项。

    参数:
        required_keys (List[str]): 必需的配置键列表。
        config (Dict): 配置字典，通常从配置文件或环境变量中加载。
        logger (Logger): 用于记录日志的日志记录器实例。

    行为:
        检查 `config` 中是否包含所有 `required_keys` 中列出的键。
        如果缺少任何必需的键，则对每个缺失的键记录一个错误日志，
        并抛出一个 KeyError，列出所有缺失的键。

    异常:
        KeyError: 如果缺少一个或多个必需的配置键。

    示例:
        required = ['host', 'port', 'username']
        config = {'host': 'localhost', 'port': 8080}
        validate_config(required, config, logger)
        # 这将记录缺少 'username' 的错误并抛出 KeyError
    """
    # 使用列表推导找出所有缺失的必需键
    missing_keys = [key for key in required_keys if key not in config]
    
    # 如果有缺失的键，则记录错误并抛出异常
    if missing_keys:
        for key in missing_keys:
            logger.error(f"缺少必需的配置键: {key}")  # 记录每个缺失键的错误日志
        # 抛出包含所有缺失键的 KeyError 异常
        raise KeyError(f"缺少必需的配置键: {', '.join(missing_keys)}")