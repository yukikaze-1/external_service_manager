# 外部服务管理器 🚀

一个独立的外部服务管理工具，用于启动、停止和管理多个外部服务。

## 📦 安装

推荐使用 `requirements.txt` 并直接运行脚本（无需将项目安装为包）。

```bash
# 克隆或下载项目
git clone <repository-url>
cd ExternalServiceManager

# 安装依赖
pip install -r requirements.txt

# 查看帮助（直接运行脚本）
python3 service_manager.py --help
```

## 🔄 本地化改进 (最新更新)

为了提高独立性和避免对 `discard` 目录的依赖，外部服务管理器现在包含了所有必要的依赖代码：

### 🔗 Consul集成 (第二阶段新增)

**最新功能：**
- ✅ **自动服务注册**：启动服务时自动注册到Consul
- ✅ **自动服务注销**：停止服务时自动从Consul注销
- ✅ **服务发现**：从Consul发现可用服务
- ✅ **健康检查集成**：自动配置健康检查端点
- ✅ **状态监控**：实时显示Consul集成状态

**新增命令：**
```bash
./manage_services.sh register    # 注册服务到Consul
./manage_services.sh unregister  # 从Consul注销服务
./manage_services.sh discover    # 发现Consul中的服务
```

### 目录结构
```
ExternalServiceManager/                 # 项目根目录
├── service_manager.py                  # 主要的服务管理器
├── consul_integration.py              # Consul集成模块
├── manage_services.sh                  # 便捷的 bash 脚本
├── config.yml                         # 主配置文件
├── service_state.json                 # 服务状态文件（自动生成）
├── requirements.txt                   # Python依赖
├── (不再包含 `setup.py`，使用 `requirements.txt` 管理依赖)
├── README.md                          # 本文档
├── LICENSE                           # 许可证
├── docs/                             # 📚 文档目录
│   ├── README.md                      # 文档导航
│   ├── CONSUL_DEPLOYMENT_GUIDE.md     # Consul部署指南
│   └── CONSUL_SOLUTION_SUMMARY.md     # 解决方案总结
├── tests/                            # 🧪 测试目录
│   ├── README.md                      # 测试说明
│   ├── test_consul_deployment.py      # Consul部署测试
│   ├── test_full_workflow.py          # 完整工作流程测试
│   └── test_simple_auto_start.py      # 自动启动测试
├── tools/                            # 🔧 工具目录
│   ├── README.md                      # 工具说明
│   └── migrate_consul_config.py       # 配置迁移工具
├── Module/                           # 依赖模块
│   └── Utils/
│       ├── Logger.py
│       └── ConfigTools.py
└── legacy/                           # 本地化的外部服务管理器组件
    ├── __init__.py
    ├── config.yml                   # 外部服务配置
    ├── core/
    │   ├── __init__.py
    │   └── service_manager.py
    ├── exceptions/
    │   ├── __init__.py
    │   └── service_exceptions.py
    └── utils/
        ├── __init__.py
        ├── config_validator.py
        ├── health_checker.py
        ├── process_manager.py
        └── retry_manager.py
```

### 主要改进
- ✅ **完全独立**: 不再依赖 `discard/ExternalServiceInit_legacy` 目录
- ✅ **本地化配置**: 包含独立的配置文件和组件
- ✅ **Consul集成**: 自动服务注册、发现和健康检查
- ✅ **循环依赖解决**: 提供多种 Consul 部署策略
- ✅ **向后兼容**: 如果本地配置不存在，会尝试使用传统配置作为后备
- ✅ **更好的维护性**: 所有相关代码都在同一个目录中
- ✅ **完整测试**: 包含全面的测试套件和文档

## ✨ 主要特性

- **🔄 完全独立运行**：与主应用分离，可以独立管理服务生命周期
- **⚡ 一键操作**：简单的命令行工具，支持启动/停止/重启/状态查看
- **📊 智能状态管理**：自动记录和恢复服务状态，支持健康检查
- **🛡️ 优雅关闭**：支持信号处理和优雅关闭，避免意外停止服务
- **🔧 自动配置**：自动复制和管理配置文件，无需手动配置
- **📈 实时监控**：支持服务运行时间、端口状态等信息查看

## 🎯 支持的服务

当前版本支持以下外部服务的自动化管理：

- **Consul** - 服务发现和配置中心 (端口: 8500)
- **Ollama Server** - 本地LLM服务 (端口: 11434)  
- **GPTSoVits Server** - TTS语音合成服务 (端口: 9880)
- **SenseVoice Server** - STT语音识别服务 (端口: 20042)
- **MicroServiceGateway** - 微服务网关 (端口: 20000)
- **APIGateway** - API网关 (端口: 20001)
- **MySQLAgent** - 数据库服务代理 (端口: 20050)
- **UserService** - 用户服务 (端口: 20010)

## 📁 文件结构

```
Tools/ExternalServiceManager/
├── service_manager.py      # 主要的服务管理器
├── consul_integration.py   # Consul集成模块
├── manage_services.sh      # 便捷的 bash 脚本
├── config.yml             # 主配置文件
├── service_state.json     # 服务状态文件（自动生成）
├── README.md              # 本文档
├── legacy/                # 本地化的外部服务管理器组件
│   ├── __init__.py
│   ├── config.yml         # 外部服务配置
│   ├── core/
│   │   ├── __init__.py
│   │   └── service_manager.py
│   ├── exceptions/
│   │   ├── __init__.py
│   │   └── service_exceptions.py
│   └── utils/
│       ├── __init__.py
│       ├── config_validator.py
│       ├── health_checker.py
│       ├── process_manager.py
│       └── retry_manager.py
└── logs/                  # 日志目录（自动创建）
```

## 🚀 快速开始

### 第一步：安装依赖
```bash
pip install -r requirements.txt
```

### 第二步：配置 Consul 集成（解决循环依赖）
```bash
# 运行配置迁移工具
python tools/migrate_consul_config.py

# 选择部署策略：
# 1 - 外部 Consul 模式（生产环境推荐）
# 2 - 自动启动模式（开发环境推荐）
```

### 第三步：启动服务
```bash
# 查看服务状态（会自动启动 Consul 如果配置了自动启动）
python service_manager.py status

# 注册服务到 Consul
python service_manager.py consul-register

# 发现 Consul 中的服务
python service_manager.py consul-discover
```

### 快速验证
```bash
# 运行完整测试验证所有功能
python tests/test_full_workflow.py
```

## 📋 状态示例

运行 `./manage_services.sh status` 后的典型输出：

```
============================================================
📊 外部服务状态
============================================================
总服务数: 8
检查时间: 2025-07-04 22:41:35

🔧 服务详情:
  • Consul
    类型: base
    端口: 8500
    状态: running
    运行时间: 0h 13m 6s
  • ollama_server
    类型: base
    端口: 11434
    状态: running
    运行时间: 0h 13m 6s
  [... 其他服务信息 ...]
============================================================
```

```bash
# 进入工具目录
cd Tools/ExternalServiceManager/

# 启动所有服务
python3 service_manager.py start

# 查看服务状态
python3 service_manager.py status

# 停止所有服务
python3 service_manager.py stop

# 重启所有服务
python3 service_manager.py restart

# 查看详细帮助
python3 service_manager.py --help
```

## 🔧 技术实现

### 核心组件

- **service_manager.py**: 主要的Python服务管理器
  - 基于传统外部服务管理器的包装实现
  - 提供现代化的CLI接口和状态管理
  - 支持优雅的服务生命周期管理

- **manage_services.sh**: Bash便捷脚本
  - 简化常用操作的命令行接口
  - 自动环境变量设置和依赖检查
  - 用户友好的输出和错误处理

### 自动化功能

- **智能配置管理**: 自动复制和管理传统配置文件
- **环境设置**: 自动设置AGENT_HOME和工作目录
- **进程管理**: 智能的进程启动、监控和停止
- **健康检查**: 各服务的HTTP健康检查端点验证
- **状态持久化**: JSON格式的服务状态文件

## 📊 服务状态

工具会自动维护服务状态文件 `service_state.json`，包含：

- 运行中的服务列表
- 服务启动时间
- 服务端口信息
- 服务类型（基础/可选）

## 🏗️ 实现状态

### ✅ 第一阶段：基础功能（已完成）

- [x] **服务生命周期管理**：完整的启动/停止/重启功能
- [x] **传统管理器集成**：复用现有的外部服务管理逻辑
- [x] **命令行接口**：用户友好的CLI工具
- [x] **状态持久化**：自动保存和恢复服务运行状态
- [x] **便捷脚本**：Bash包装脚本，简化操作
- [x] **信号处理**：优雅的程序退出，避免服务意外停止
- [x] **自动配置**：智能配置文件管理和环境设置
- [x] **健康检查**：服务启动验证和状态监控
- [x] **错误处理**：完善的错误处理和故障排除
- [x] **多服务支持**：同时管理8个不同类型的外部服务

### 🔄 第二阶段：Consul集成（规划中）

- [ ] 自动服务注册到 Consul
- [ ] 服务发现集成
- [ ] 健康检查自动化
- [ ] 服务注销功能
- [ ] 动态配置更新

### 🚀 第三阶段：高级功能（未来）

- [ ] 单个服务管理（启动/停止指定服务）
- [ ] 配置模板生成和管理
- [ ] Web 管理界面
- [ ] RESTful API 接口
- [ ] 监控和告警集成
- [ ] 容器化支持

## ⚠️ 使用须知

### 环境要求

1. **系统要求**：
   - Linux操作系统（已测试Ubuntu/CentOS）
   - Python 3.7+
   - Bash shell

2. **依赖要求**：
   - 传统外部服务管理器代码（`discard/ExternalServiceInit_legacy/`）
   - 各服务的运行环境（Conda环境、Python包等）
   - 网络端口可用性（8500, 11434, 9880, 20000-20050等）

3. **权限要求**：
   - 启动服务进程的权限
   - 写入日志和状态文件的权限
   - 网络端口绑定权限

### 验证安装

运行以下命令验证工具是否正确安装：

```bash
# 检查帮助信息
./manage_services.sh help

# 检查依赖
./manage_services.sh status
```

## � 故障排除

### 常见问题

#### 1. 导入错误
```
错误：无法导入传统外部服务管理器
```
**解决方案**: 确保 `discard/ExternalServiceInit_legacy` 目录存在且包含完整代码

#### 2. 配置文件问题
```
No configuration file found
```
**解决方案**: 工具会自动复制配置文件，确保传统配置文件存在

#### 3. 端口冲突
```
Service startup failed: Health check failed
```
**解决方案**: 检查端口是否被占用：`netstat -tlnp | grep <端口号>`

#### 4. 权限问题
```
Permission denied
```
**解决方案**: 
- 确保脚本可执行：`chmod +x manage_services.sh`
- 检查文件写入权限
- 确保可以启动网络服务

### 调试方法

1. **查看详细日志**：
   ```bash
   python3 service_manager.py start --verbose
   ```

2. **检查服务日志**：
   ```bash
   tail -f ../../Log/ExternalService/*.log
   ```

3. **验证服务状态**：
   ```bash
   # 检查进程
   ps aux | grep -E "(consul|ollama|GPTSoVits)"
   
   # 检查端口
   netstat -tlnp | grep -E "(8500|11434|9880)"
   
   # 测试健康检查
   curl http://127.0.0.1:8500/v1/status/leader
   ```

## 📞 获取帮助

### 命令行帮助
```bash
# 查看总体帮助
./manage_services.sh help

# 查看Python脚本详细选项
python3 service_manager.py --help
```

### 日志和状态文件
- **服务日志**: `../../Log/ExternalService/*.log`
- **状态文件**: `service_state.json`
- **配置文件**: `config.yml`

## 🎉 成功案例

外部服务管理器已经在以下场景中验证可用：

- ✅ **开发环境**: 本地开发时的服务管理
- ✅ **多服务启动**: 一次性启动8个外部服务
- ✅ **服务持久化**: 程序退出后服务继续运行
- ✅ **健康检查**: 所有服务的健康状态验证
- ✅ **优雅停止**: 安全停止所有服务而不丢失数据

## 🔮 未来发展

### 短期目标（1-2周）
1. **单服务管理**: 支持启动/停止单个指定服务
2. **Consul集成**: 自动服务注册和发现
3. **健康监控**: 实时健康状态监控和告警

### 中期目标（1个月）
1. **Web界面**: 简单的Web管理界面
2. **API接口**: RESTful API支持
3. **配置热更新**: 动态配置更新和验证

### 长期目标（3个月）
1. **容器化**: Docker和docker-compose支持
2. **多环境**: 开发/测试/生产环境管理
3. **监控集成**: Prometheus/Grafana集成

---

## 📄 许可证

本项目遵循与主项目相同的许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个工具！

---

**🎯 外部服务管理器 - 让服务管理变得简单高效！**
