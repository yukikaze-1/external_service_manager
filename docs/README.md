# 文档目录

这个目录包含了外部服务管理器的详细文档。

## 文档列表

### Consul 集成文档

- **`CONSUL_DEPLOYMENT_GUIDE.md`** - Consul 部署策略详细指南
  - 三种部署策略对比
  - 配置步骤说明
  - 故障排除指南
  - 使用示例

- **`CONSUL_SOLUTION_SUMMARY.md`** - Consul 循环依赖解决方案总结
  - 问题分析和解决方案
  - 技术实现细节
  - 成果展示
  - 使用指南

## 快速导航

### 新用户入门

1. 阅读 [Consul 解决方案总结](CONSUL_SOLUTION_SUMMARY.md) 了解整体方案
2. 参考 [部署指南](CONSUL_DEPLOYMENT_GUIDE.md) 选择合适的部署策略
3. 使用 `tools/migrate_consul_config.py` 进行配置迁移

### 部署策略选择

- **开发环境**：推荐自动启动模式
- **生产环境**：推荐外部 Consul 模式
- **测试环境**：可根据需要选择

### 常见问题

#### Consul 循环依赖问题
- **问题**：Consul 既作为被管理服务又作为注册中心
- **解决**：使用配置迁移工具分离 Consul 管理

#### 端口冲突问题
- **问题**：Consul 默认端口 8500 被占用
- **解决**：修改配置文件中的 Consul URL

#### 权限问题
- **问题**：无法启动 Consul 进程
- **解决**：检查用户权限和防火墙设置

### 技术架构

```
外部服务管理器
├── 核心模块
│   ├── service_manager.py      # 主服务管理器
│   └── consul_integration.py   # Consul 集成模块
├── 配置文件
│   ├── config.yml             # 主配置文件
│   └── legacy/config.yml      # 传统服务配置
├── 工具 (tools/)
│   └── migrate_consul_config.py
├── 测试 (tests/)
│   ├── test_consul_deployment.py
│   └── test_full_workflow.py
└── 文档 (docs/)
    ├── CONSUL_DEPLOYMENT_GUIDE.md
    └── CONSUL_SOLUTION_SUMMARY.md
```

### 相关链接

- [项目主 README](../README.md)
- [工具文档](../tools/README.md)
- [测试文档](../tests/README.md)
