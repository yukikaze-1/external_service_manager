#!/usr/bin/env python3
"""
ExternalServiceManager - 外部服务管理器

一个独立的外部服务管理工具，用于启动、停止和管理多个外部服务。
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="external-service-manager",
    version="1.0.0",
    author="yomu",
    author_email="",
    description="独立的外部服务管理工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
    install_requires=[
        "pyyaml>=6.0",
        "python-dotenv>=0.19.0",
        "requests>=2.25.0",
        "python-consul>=1.1.0",
    ],
    entry_points={
        "console_scripts": [
            "external-service-manager=service_manager:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yml", "*.yaml", "*.md", "*.sh"],
    },
)
