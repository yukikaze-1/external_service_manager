# 工具目录

这个目录包含了外部服务管理器的配置和维护工具。

## 工具说明

### 配置迁移工具

- **`migrate_consul_config.py`** - Consul 配置迁移脚本
  - 解决 Consul 循环依赖问题
  - 提供交互式配置选择
  - 自动备份原配置文件

## 使用方法

### Consul 配置迁移

```bash
python tools/migrate_consul_config.py
```

脚本提供以下选项：

1. **外部 Consul 模式（推荐生产环境）**
   - 将 Consul 配置从 legacy/config.yml 中移除
   - 配置主配置文件使用外部 Consul
   - 适合生产环境部署

2. **自动启动模式（推荐开发环境）**
   - 移除 legacy 配置中的 Consul
   - 配置自动启动 Consul 功能
   - 适合开发环境使用

3. **仅移除 legacy 配置**
   - 只从 legacy/config.yml 中移除 Consul 配置
   - 手动配置主配置文件

### 配置文件备份

工具会自动创建配置文件备份：
- `config.backup_YYYYMMDD_HHMMSS`
- `legacy/config.backup_YYYYMMDD_HHMMSS`

### 使用场景

#### 新部署
如果是全新部署，建议：
- 开发环境：选择"自动启动模式"
- 生产环境：选择"外部 Consul 模式"

#### 现有系统升级
如果已有系统存在 Consul 循环依赖问题：
1. 运行迁移脚本
2. 选择合适的部署模式
3. 重启服务管理器

### 注意事项

- 运行前请确保没有正在运行的服务
- 工具会自动备份配置文件
- 如需回滚，可使用备份文件恢复
- 建议先在测试环境验证配置

### 故障恢复

如果迁移后出现问题：

1. **恢复配置文件**：
   ```bash
   cp config.backup_* config.yml
   cp legacy/config.backup_* legacy/config.yml
   ```

2. **检查配置语法**：
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yml'))"
   ```

3. **验证服务状态**：
   ```bash
   python service_manager.py status
   ```
