# Consul 部署指南

## 问题概述
当前项目中 Consul 既作为被管理的服务，又作为服务注册中心，存在循环依赖问题。

## 部署策略

### 策略一：Consul 作为外部服务（推荐用于生产环境）

**概述**：Consul 由外部独立启动和管理，外部服务管理器仅作为客户端使用 Consul。

**优点**：
- 避免循环依赖
- Consul 高可用性
- 更符合微服务架构最佳实践
- 便于集群部署

**配置步骤**：

1. **从被管理服务中移除 Consul**：
   ```yaml
   # 在 legacy/config.yml 中注释掉或删除 Consul 服务配置
   external_services:
     base_services:
     # - Consul:  # 移除此配置
     - ollama_server:
       # 保留其他服务
   ```

2. **外部启动 Consul**：
   ```bash
   # 开发环境
   consul agent -dev -client 0.0.0.0
   
   # 生产环境
   consul agent -server -bootstrap-expect=1 -data-dir=/opt/consul/data -config-dir=/opt/consul/config
   ```

3. **验证 Consul 可用性**：
   ```bash
   curl http://127.0.0.1:8500/v1/status/leader
   ```

4. **配置外部服务管理器**：
   ```yaml
   # 在 config.yml 中配置
   consul:
     enabled: true
     url: "http://127.0.0.1:8500"
     auto_register: true
     auto_start: false  # 不自动启动，依赖外部 Consul
     service_prefix: "agent"
   ```

### 策略二：条件性 Consul 管理（推荐用于开发环境）

**概述**：外部服务管理器在启动时检查 Consul 是否已运行，如果没有则启动它。

**优点**：
- 开发环境便利性
- 自动化程度高
- 避免手动管理

**配置步骤**：

1. **从被管理服务中移除 Consul**：
   ```yaml
   # 在 legacy/config.yml 中注释掉或删除 Consul 服务配置
   external_services:
     base_services:
     # - Consul:  # 移除此配置
   ```

2. **启用自动 Consul 管理**：
   ```yaml
   # 在 config.yml 中配置
   consul:
     enabled: true
     url: "http://127.0.0.1:8500"
     auto_register: true
     auto_start: true  # 启用自动启动
     service_prefix: "agent"
   ```

3. **启动外部服务管理器**：
   ```bash
   # 如果 Consul 未运行，系统会自动启动它
   python service_manager.py start_all
   ```

### 策略三：混合模式（高级用户）

**概述**：结合两种策略，提供最大的灵活性。

**配置步骤**：

1. **智能检测配置**：
   ```yaml
   consul:
     enabled: true
     url: "http://127.0.0.1:8500"
     auto_register: true
     # 开发环境启用自动启动，生产环境禁用
     auto_start: ${CONSUL_AUTO_START:-false}
     service_prefix: "agent"
   ```

2. **环境变量控制**：
   ```bash
   # 开发环境
   export CONSUL_AUTO_START=true
   python service_manager.py start_all
   
   # 生产环境
   export CONSUL_AUTO_START=false
   # 先启动 Consul
   consul agent -server -config-dir=/etc/consul.d
   # 再启动服务管理器
   python service_manager.py start_all
   ```

## 实现细节

### 自动 Consul 管理功能

项目现在包含以下增强功能：

1. **ConsulManager 类**：
   - 检测 Consul 是否运行
   - 自动启动 Consul（开发模式）
   - 自动停止自启动的 Consul 进程

2. **增强的 ConsulServiceRegistry**：
   - 支持 `auto_start_consul` 参数
   - 启动时自动检查并启动 Consul
   - 关闭时清理资源

3. **配置文件支持**：
   - `consul.auto_start` 配置项
   - 环境变量支持（预留）

### 使用示例

```python
# 自动启动模式
registry = ConsulServiceRegistry(
    consul_url="http://127.0.0.1:8500",
    auto_start_consul=True,  # 如果 Consul 未运行则自动启动
    logger=logger
)

# 手动管理模式
registry = ConsulServiceRegistry(
    consul_url="http://127.0.0.1:8500",
    auto_start_consul=False,  # 依赖外部 Consul
    logger=logger
)
```

## 推荐配置

### 开发环境
```yaml
consul:
  enabled: true
  auto_start: true
  auto_register: true
```

### 生产环境
```yaml
consul:
  enabled: true
  auto_start: false
  auto_register: true
```

## 故障排除

### 常见问题

1. **Consul 启动失败**：
   ```bash
   # 检查 Consul 是否安装
   which consul
   
   # 检查端口是否被占用
   lsof -i :8500
   ```

2. **权限问题**：
   ```bash
   # 确保有写入权限（数据目录）
   sudo mkdir -p /tmp/consul-data
   sudo chown $USER:$USER /tmp/consul-data
   ```

3. **网络问题**：
   ```bash
   # 检查防火墙设置
   sudo ufw status
   
   # 检查 Consul 监听地址
   curl http://127.0.0.1:8500/v1/status/leader
   ```

### 日志分析

查看详细日志以诊断问题：
```bash
# 查看外部服务管理器日志
tail -f external_service_manager.log

# 查看 Consul 日志（如果是自动启动的）
# 日志会在外部服务管理器的日志中显示
```

## 总结

- **生产环境**：推荐使用策略一，外部独立管理 Consul
- **开发环境**：推荐使用策略二，自动管理 Consul
- **测试环境**：可使用策略二或策略三，根据需要选择

通过这些策略，可以完全避免 Consul 的循环依赖问题，同时保持系统的可用性和可维护性。
