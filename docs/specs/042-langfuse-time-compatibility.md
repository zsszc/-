# Spec 042：本地 Langfuse 时间戳兼容性修复

## 问题与证据

本地 Langfuse v3 使用未固定版本的 ClickHouse，实际拉到 26.8.6.5。测试对话的 Trace 和观测在 ClickHouse 内显示为 `9999-12-31`，`toUnixTimestamp64Milli` 得到的数值恰好是正确 UTC 毫秒值的 1000 倍。Langfuse Web/Worker 容器时钟正常。官方当前 Compose 固定 ClickHouse 25.12，不使用 `latest`。

## 范围

1. 将本项目自部署 Langfuse 的 ClickHouse 镜像固定到 25.12，避免新安装继续拉取浮动版本。
2. 不降级或覆盖现有 ClickHouse 数据卷。先停止旧观测栈，再以独立 Compose 项目名启动同配置的新栈，保留旧容器及数据卷可回退。
3. 新栈就绪后重启客服应用，发起不含真实运单/个人信息的测试对话，验证 Langfuse Trace 时间戳、Token、延迟和反馈 Score。
4. 时间正确后重跑成本报告；若仍异常，恢复旧栈并在页面保持异常提示，不直接修改 ClickHouse 表数据。少于 5 次请求时不生成可能误导的模型读图结论。

## 验收标准

- 新 Trace 的时间接近本机 UTC，且不再显示 `9999-12-31`。
- `/api/observability/overview` 在线，近期窗口内包含新 Trace，Score 能关联。
- 原有客服聊天不因观测栈替换而失败。
- 相关测试通过，`.env` 与运行数据不进入 Git。

## 实现记录

- `docker-compose.langfuse.yml` 将 ClickHouse 固定为 `25.12`；客服 MySQL 与 Langfuse PostgreSQL 分别使用 `DATABASE_URL` / `LANGFUSE_DATABASE_URL`。
- 旧 Compose 项目 `mewhelp-langfuse` 已停止，但五个数据卷仍保留；新项目 `mewhelp-langfuse-compat` 使用独立数据卷运行。没有迁移或改写旧 Trace 数据。
- 新栈产生的清关咨询测试 Trace 时间为 `2026-09-19T07:00:53.754Z`，不再是 9999 年；会话标签、5643 Token、8.965 秒延迟和 `user_feedback=1` Score 均可查询。客服对话返回成功。
- `/api/observability/overview` 返回 `online`、近期请求 1、错误 0、平均/P95 延迟 8.965 秒、Token 5643、时间异常 `false`。7 天成本报告重跑后仅统计新 Trace；样本量 1，读图小注留空。
- `app/core/observability.py` 对正常 Trace 直接使用秒级延迟，仅对旧异常时间戳兼容换算，防止新栈延迟被缩小 1000 倍。
- 浏览器实测发现有 Trace 详情链接时观测页会对 `const status` 重新赋值，导致整页渲染失败；改为分别追加链接或状态节点，并再次打开页面验收。
- 本地 Langfuse Web/MinIO 原配置监听所有网卡，且使用开发默认密钥；调整为仅监听 `127.0.0.1`。由于 WPS Office 占用本机 `9090`，MinIO 主机端口及外部访问地址同步改为 `9190`。保留数据卷重建后，Compose 显示 Web `127.0.0.1:3000`、MinIO `127.0.0.1:9190`；观测 API 仍为 `online`，浏览器页面正常显示指标与 Trace。远程部署需另行配置强密钥与访问控制。
- 相关测试 `38 passed`。`uv.lock` 的意外重排已清理；业务 `.env` 保持忽略，未提交或上传任何数据。

回退方式：停止 `mewhelp-langfuse-compat`，再启动旧项目 `mewhelp-langfuse`。旧数据卷仍在；旧栈的异常时间戳问题也会随之恢复，故仅作为故障回退，不作为正常长期方案。

交付边界：本轮未提交、未推送、未部署服务器。`data/ch09/reports/cost_by_intent.*` 是旧仓库已追踪的文件，本地报告已刷新；后续整理提交时必须单独审查，不应把运行产物或 `.env` 连同源码上传。
