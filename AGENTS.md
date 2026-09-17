# 项目协作说明

## 项目定位

这是一个跨境物流智能运营助手。核心能力包括运单问答、业务工具调用、清关知识库检索、异常分流、质量评估与运行观测。

## SDD 开发流程

- 每次功能修改先在 `docs/specs/` 新增或更新 Spec，明确范围、接口契约和验收标准。
- 实现后补充测试，完成启动/接口验收，再在 Spec 的“实现记录”写入结果。
- 未完成验收前，不把 Spec 标记为完成；每个功能独立提交并推送。

## 开发约定

- Python 版本要求见 `pyproject.toml`，优先使用 `uv` 管理依赖。
- 所有命令从项目根目录 `/Users/zc/Desktop/MewHelp/python` 执行。
- API 密钥只放在 `.env`，不得写入源码、测试数据或提交记录。
- 修改后优先运行相关测试；涉及接口或配置时补充启动/冒烟验证。
- 数据库结构变更同步更新 `sql/` 和对应测试。
- 不要提交 `data/` 运行产物、日志、缓存、模型文件或本地密钥。

## 启动依赖

首次运行前复制 `.env.example` 为 `.env`，在 `/Users/zc/Desktop/MewHelp/python/.env` 填写聊天、嵌入和重排服务配置。完整运行还需要 Docker Desktop 提供 MySQL 和 Milvus。

## 常用验证

```bash
make test
make smoke-rag
```

## 提交前检查

- 确认 `git status` 中没有 `.env`、密钥和运行产物。
- 确认 README 与实际启动命令一致。
- 确认新增配置同时更新 `.env.example`。
