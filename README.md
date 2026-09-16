# 智能客服平台

面向电商业务的智能客服系统，提供订单与物流查询、售后政策问答、退款流程、知识库管理、质量评估、运行观测和主题分类能力。

## 功能概览

- 基于 FastAPI 的聊天与管理接口，并提供浏览器聊天页面
- 通过工具调用查询订单、商品、物流和售后信息
- 支持 FAQ/政策/商品资料的切块、向量化、混合检索与重排
- 支持退款确认、工单创建等需要用户确认的操作
- 支持低置信问题收集、人工复核和知识库回补
- 支持 LangGraph 工作流、Langfuse 观测以及主题分类器训练/推理

## 技术栈

FastAPI、LangGraph/LangChain、SQLAlchemy、MySQL、Milvus、MCP、Langfuse。

## 快速启动

项目命令均在本目录执行：`/Users/zc/Desktop/MewHelp/python`。

1. 准备配置文件：

   ```bash
   cp .env.example .env
   ```

   然后编辑 `/Users/zc/Desktop/MewHelp/python/.env`，填写 `CHAT_*`、`EMBED_API_KEY` 和 `RERANK_API_KEY`。如果使用其他模型服务，也请同步调整对应的 `*_BASE_URL` 和模型名。不要把真实密钥提交到 Git。

2. 确保 Docker Desktop 已启动，然后启动 MySQL、Milvus 及应用：

   ```bash
   docker compose up -d
   make seed
   make dev
   ```

3. 浏览器打开 <http://localhost:8000>。

如果只想先验证代码结构，可以运行：

```bash
make test
```

完整功能需要 API 配置和 Docker 依赖服务；缺少配置时，应用会在启动阶段明确提示对应环境变量。

## 配置说明

配置模板：`/Users/zc/Desktop/MewHelp/python/.env.example`  
实际配置：`/Users/zc/Desktop/MewHelp/python/.env`

- `CHAT_*`：对话、意图识别和摘要模型
- `EMBED_*`：知识库嵌入模型
- `RERANK_*`：检索重排模型
- `DATABASE_URL`：业务数据库连接串，可按需覆盖默认值
- `MCP_*_URL`：物流和售后 MCP 服务地址
- `LANGFUSE_*`：可选的本地观测服务配置

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `app/api/` | HTTP API 与页面路由 |
| `app/graph/` | Agent 状态、节点、路由和工作流组装 |
| `app/core/` | 模型客户端、检索、上下文、意图和观测能力 |
| `app/kb/` | 知识库切块、嵌入、双写、去重和知识挖掘 |
| `app/tools/` | 内置工具、MCP 工具注册与执行 |
| `app/db/` | 数据模型与数据库仓储 |
| `app/static/` | Web 页面和静态资源 |
| `mcp_servers/` | 物流与售后业务工具服务 |
| `sql/` | 数据库建表与初始化脚本 |
| `scripts/` | 建库、评估、数据处理和模型相关命令 |
| `tests/` | 自动化测试 |

## 常用命令

```bash
make help          # 查看全部命令
make test          # 运行测试
make dev           # 启动开发服务
make milvus-up     # 单独启动 Milvus
make mcp-up        # 启动业务工具服务
make kb-build      # 构建知识库
make kb-vectorize  # 写入向量索引
make smoke-rag     # 检查检索链路
```

## 服务端口

| 端口 | 服务 |
| --- | --- |
| 8000 | Web 应用 |
| 8101 | 物流 MCP 服务 |
| 8102 | 售后 MCP 服务 |
| 8110 | 主题分类器推理服务 |
| 19530 | Milvus |
| 3000 | Langfuse（可选） |

## 安全与部署

- `.env`、数据库文件、日志和模型运行产物默认不会进入 Git。
- 生产环境请替换数据库密码、观测服务密钥和容器默认凭据，并在反向代理层配置认证与 HTTPS。
- 部署细节见 [`DEPLOY.md`](DEPLOY.md)。
