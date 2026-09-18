# 物流 Agent 综合评测

评估集位于 `data/evals/logistics_agent_eval.jsonl`，共 300 条，分为政策流程、跨文档、工具操作、库外拒答和边界澄清五类。

## 离线验收

不调用模型，只检查数量、分类分布、字段和 query 唯一性：

```bash
.venv-m4-arm/bin/python scripts/eval_logistics_agent.py --offline
```

## 在线小规模抽测

先启动本地服务，再显式指定在线模式。建议先用 5 条确认链路：

```bash
.venv-m4-arm/bin/python scripts/eval_logistics_agent.py --live --limit 5
```

默认请求 `http://127.0.0.1:8000`，也可以通过 `MEWHELP_EVAL_BASE` 或 `--base-url` 修改。完整 300 条评测会产生较多模型调用，按需执行：

```bash
.venv-m4-arm/bin/python scripts/eval_logistics_agent.py --live
```

在线报告默认写入 `data/evals/logistics_agent_eval_report_live.json`，包含逐条响应和分类汇总。评测规则是行为回归指标，不等同于人工事实准确率；报告中的服务错误会按失败记录，不会输出环境变量或 API key。
