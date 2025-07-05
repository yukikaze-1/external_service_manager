# 测试文件目录

这个目录包含了外部服务管理器的所有测试文件。

## 测试文件说明

### Consul 集成测试

- **`test_consul_deployment.py`** - Consul 部署策略测试
  - 测试外部 Consul 模式
  - 测试自动启动 Consul 模式
  - 测试 ConsulManager 类功能

- **`test_full_workflow.py`** - 完整工作流程测试
  - 端到端测试整个 Consul 集成流程
  - 验证服务注册、发现、注销功能
  - 检查配置和依赖

- **`test_simple_auto_start.py`** - 简单的自动启动功能测试
  - 快速验证 Consul 自动启动功能
  - 测试服务注册和注销基本功能

### 运行测试

```bash
# 运行所有 Consul 部署策略测试
python tests/test_consul_deployment.py

# 运行完整工作流程测试
python tests/test_full_workflow.py

# 运行简单自动启动测试
python tests/test_simple_auto_start.py
```

### 测试环境要求

1. **依赖包**：
   - `python-consul`
   - `requests`
   - `pyyaml`

2. **系统要求**：
   - Consul 已安装并在 PATH 中
   - 端口 8500 可用（Consul 默认端口）

3. **权限要求**：
   - 能够启动和停止进程
   - 网络访问权限

### 测试策略

- **外部 Consul 测试**：需要手动启动 Consul 后运行
- **自动启动测试**：确保 Consul 未运行，让测试自动启动
- **集成测试**：测试与现有服务管理器的集成

### 故障排除

如果测试失败，请检查：

1. Consul 是否正确安装：`consul version`
2. Python 依赖是否安装：`pip list | grep consul`
3. 端口是否被占用：`lsof -i :8500`
4. 日志文件中的错误信息

### 注意事项

- 测试可能会自动启动和停止 Consul 进程
- 某些测试需要网络连接
- 建议在测试环境中运行，避免影响生产服务
