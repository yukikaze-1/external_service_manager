**项目简介**
- **名称**: External Service Manager
- **描述**: 一个独立的外部服务管理工具，用于在本地启动、停止、监控并（可选）将服务注册到 Consul。该工具将低层进程管理与 Consul 集成分离，便于在不同环境中独立运行外部依赖服务。

**主要功能**
- **启动/停止/查看状态**: 管理仓库 `service_config.yml` 中定义的 `base_services` 与 `optional_services`。
- **Consul 集成**: 可选地自动启动 Consul（需要系统安装 `consul` 命令或 Python 的 `python-consul` 库），并进行服务注册注销与发现。
- **进程管理**: 使用 `Module/Utils/process_runner.py` 进行进程启动与停止。
- **日志**: 使用 `Module/Utils/Logger.py` 记录到 `Log/` 目录并输出到控制台。

**文件结构（要点）**
- **`service_manager.py`**: 命令行入口与高层管理器 `ExternalServiceManager`，负责读取状态、保存 `service_state.json`、与 Consul 集成逻辑。
- **`consul_integration.py`**: Consul 启动/注册/发现的实现（`ConsulIntegrationManager`、`ConsulServiceRegistry` 等）。
- **`Module/Utils/process_runner.py`**: 轻量级的进程启动器/停止器，实现 `init_services`, `stop_all_services`, `get_service_status`。
- **`Module/Utils/Logger.py`**: 日志初始化助手 `setup_logger`。
- **`service_config.yml`**: 服务定义与 Consul 配置的主要位置。
- **`service_state.json`**: 运行时保存的服务状态（由 `ExternalServiceManager` 写入）。
- **`requirements.txt`**: 推荐的 Python 依赖。

**快速开始（环境准备）**

1. 克隆或进入仓库根目录（此 README 假设当前路径为仓库根）。

2. 安装 Python 依赖：

```bash
pip install -r requirements.txt
```

建议同时安装 `psutil` 以获得更可靠的进程检测和终止：

```bash
pip install psutil
```

3. 确保如需 Consul 自动启动/注册，则本机可用 `consul` 命令，或确保 `python-consul` 库在 `requirements.txt` 中已安装（仓库已推荐 `python-consul`）。

**配置说明**
- **主配置**: `service_config.yml`。其中键 `external_services.base_services` 与 `optional_services` 定义了要管理的服务。每个服务项可以包含：
  - `service_name` / 名称
  - `script` / 启动命令或 Python 脚本路径
  - `args` / 启动参数（Port 可从 `args` 中解析）
  - `use_python` / 是否通过 Conda 环境的 Python 启动
  - `conda_env` / Conda 环境路径（若 `use_python` 为 True）
  - `run_in_background` / 是否后台运行
  - `health_check_url` / Consul 健康检查 URL

- **Consul 配置**: 在 `service_config.yml` 的 `consul` 字段中配置：
  - `enabled`, `auto_register`, `auto_start`, `url`, `service_prefix`, `register_wait_timeout` 等。

**运行与用法示例**

- 启动所有服务：

```bash
python service_manager.py start
```

- 停止所有服务：

```bash
python service_manager.py stop
```

- 查看当前服务状态：

```bash
python service_manager.py status
```

- 重启（通过 stop + start）：

```bash
python service_manager.py stop && python service_manager.py start
```

- Consul 相关：

```bash
python service_manager.py consul-register      # 将当前运行服务注册到 Consul
python service_manager.py consul-unregister    # 从 Consul 注销服务
python service_manager.py consul-discover      # 列出 Consul 中的服务
```

注意：`service_manager.py` 接受可选参数 `--config` 指定配置文件路径，以及 `-v/--verbose` 打开更详细控制台输出。

**实现细节与设计要点**
- 高层管理器 `ExternalServiceManager` 使用 `Module/Utils/process_runner.ProcessRunner` 来启动/停止服务并记录 `service_state.json`。
- 日志目录：默认使用环境变量 `AGENT_HOME`（若未设置则为仓库根）下的 `Log/`。通过 `Module/Utils/Logger.setup_logger` 可读取 `Module/Utils/.env` 或环境变量 `LOG_DIR` 覆盖。
- 进程终止：若安装了 `psutil` 会使用更可靠的进程树终止策略；否则退回到 POSIX 信号 `kill`。
- Consul：当 `consul.auto_start` 为 `true` 且系统中不存在运行的 Consul，代码会尝试使用 `consul` 命令自动启动（需要系统中可用该二进制）。同时也支持仅使用 `python-consul` 客户端连接到已有 Consul 服务。

**已知限制与注意事项**
- 单个服务的 `start_service` / `stop_service` 在 `ExternalServiceManager` 中标记为 “待实现”。当前推荐通过 `start`/`stop` 操作管理所有服务。
- 自动启动 Consul 需要系统可执行 `consul`，否则请使用已部署的 Consul 并在 `service_config.yml` 设置 `url` 指向其地址。
- 进程启动时输出被重定向到 `/dev/null`（`ProcessRunner` 内），若需要查看子进程日志，请在服务配置中指定日志文件或禁用输出重定向并自行调整 `process_runner.py`。

**调试建议**
- 若遇到服务无法被识别或端口信息缺失：检查 `service_config.yml` 的 `ip_port` 与服务条目中是否包含 `script`、`args` 或 `health_check_url`。
- 若停止服务失败或残留僵尸进程：安装 `psutil` 并以 root 或能操作进程的用户运行管理脚本。

**开发与贡献**
- 代码风格保持简洁、模块化。若要扩展单服务管理（启动/停止/重启单个服务），建议在 `ProcessRunner` 中增加按名称查找与控制进程的接口，然后在 `ExternalServiceManager` 中调用。
- 提交变更前运行基本验证：

```bash
python service_manager.py status
```

并尽量保证 `service_state.json` 与 `service_config.yml` 在变更后保持一致。

**许可证**
- 本项目采用 MIT 许可证（详见 `LICENSE`）。

**作者**
- `yomu`
