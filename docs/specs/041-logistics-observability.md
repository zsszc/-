# Spec 041：物流 Agent 全链路观测闭环

## 背景

项目已经在 LangGraph 编译阶段挂载 Langfuse Callback，并记录会话、意图与 token，
但 `/observability` 仍重定向到 Agent 评测页，后台看不到 Langfuse 是否在线、近期调用链、
延迟与错误；用户点赞/点踩也没有回写为 Langfuse Score。已有观测能力因此难以演示和排障。

## 目标

1. 恢复 `/observability` 为当前跨境物流版本的全链路观测页面。
2. 展示 Langfuse 配置/连接状态、24 小时请求量、错误数、平均延迟、P95 延迟和 token。
3. 展示最近 Trace 的会话、意图标签、延迟、token、错误和 Langfuse 详情入口。
4. 用户点赞/点踩继续执行现有知识飞轮逻辑，同时尽力写入 `user_feedback` Score。
5. 在后台导航和运营总览中恢复“链路观测”入口。

## 接口契约

### `GET /api/observability/overview`

保留原有 `cost`、`trend`、`calibration`，新增 `runtime`：

- `status`: `online | unconfigured | unreachable`
- `enabled`: 是否配置三项 Langfuse 环境变量
- `base_url`: Langfuse 地址，不包含密钥
- `window_hours`: 聚合窗口
- `metrics`: 请求数、错误数、平均/P95 延迟、token
- `traces`: 最近 Trace 的安全摘要，不返回输入输出正文

Langfuse 未配置或不可达时返回 200 和降级状态，不影响其他三块报表。

### `POST /api/feedback`

响应新增 `scored: bool`。启用 Langfuse 时按 `conversation_id` 查最近 Trace，写入：

- score 名称：`user_feedback`
- 类型：BOOLEAN
- 点赞为 `true`，点踩为 `false`

Score 写入失败不得影响点赞/点踩和低置信度问题入池。

## 安全与边界

- 后台摘要不展示用户问题、模型完整输入输出和 API 密钥。
- Langfuse 是可选增强，故障时业务主链路继续运行。
- 不改变 MCP 接入方式，不将主题分类器接入实时主链路。
- 页面只读取 Langfuse；详细 Trace 仍在 Langfuse 原生界面查看。

## 验收标准

- `/observability` 返回 200，并出现在后台导航。
- 未配置 Langfuse 时页面明确显示“未配置”，无 500。
- 模拟 Langfuse 数据时 API 正确计算请求量、错误数、平均/P95 延迟和 token。
- 最近 Trace 不包含 input/output，但包含可点击详情地址。
- 点赞与点踩都会尝试写 Score；失败时原反馈接口仍正常返回。
- 相关 API、核心函数和静态页面测试通过。

## 实现记录

已实现：

- `/observability` 恢复为物流业务观测页，后台导航和总览新增入口；页面读取近期 Trace 安全摘要、状态和指标，原有成本、趋势、阈值模块保留。
- 点赞/点踩尽力将 `user_feedback` 写入该会话最新 Trace；失败不阻断原反馈流程。
- 隔离含旧电商意图的成本产物，避免在物流页面展示过期数据。
- 本地 Langfuse compose 与业务 `.env` 都有 `DATABASE_URL`；首次启动时 MySQL URL 覆盖了 Langfuse 所需的 PostgreSQL URL。已改为独立的 `LANGFUSE_DATABASE_URL` 覆盖项，默认 PostgreSQL URL。镜像拉取后，数据库迁移成功、Web/Worker 容器启动、首页返回 200。
- 本机 Python HTTP 客户端继承代理时会让回环地址的 Langfuse 请求得到空 502。只对 localhost/127.0.0.1/::1 的 SDK API、Score 与 OTLP Trace 上报禁用环境代理；远程实例保留原行为。
- 自部署 v3 正常 Trace 的延迟按秒展示；仅对旧栈异常时间戳记录做千倍兼容换算。Token 通过 v3 生成观测接口批量汇总（最多 5 页×100 条），不将缺失汇总字段误判为零用量。
- 对异常未来时间戳标记“时间异常”，提示近期窗口不精确，不直接展示 9999 年为正常时间。

验收情况：相关观测、反馈、后台、页面测试 37 项通过。实际发起“德国清关通常需要准备哪些资料？”测试对话，回复成功、Langfuse 生成一条带 `清关咨询` 意图和会话 ID 的 Trace；摘要返回 `online`、请求 1、错误 0、平均/P95 7.877 秒、Token 5,644。点赞接口返回 `scored=true`，随后在该 Trace 查到 `user_feedback=1`。页面此前已本地渲染验证；本轮新增“时间异常”标记后 API 和测试通过，页面需刷新查看。

后续修复：见 Spec 042。新栈固定 ClickHouse 25.12，重新生成的 Trace 时间正常，24 小时窗口已能纳入该条新 Trace；旧异常数据留在已停止的旧栈数据卷，不混入当前统计。成本报告也已基于新 Trace 重跑。根因未从底层代码完全证实，但版本替换后的实测已消除复现；仍保留异常时间提示用于防回归。

指标口径：当前为最多 50 条近期 Trace 的窗口样本统计，不是无限分页后的全量统计；若未来再出现异常时间戳，页面会提示。Token 来自最近最多 500 条生成观测，同样是样本。`runtime.traces` 不返回 input/output，但 Langfuse 原生 Trace 页面可能包含原始内容，仅本机或受控网络开放。
