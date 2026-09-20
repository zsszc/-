"""航迹云运营总览 API：聚合运单、知识、评测、失败复盘和观测数据。

各块依赖不同(MySQL / Milvus / 嵌入与聊天上游)。任何一块的依赖没起,
只让它自己那张卡显示读数失败,不连坐整页——后台首页的用处正是在依赖不齐的时候
也能一眼看出「哪一块现在是活的」。

每张卡的数都从各模块自己的读数函数来,这里只做汇总,不另算一份。
"""
import asyncio

from fastapi import APIRouter

from app.api import agent_eval, kb, logistics_overview, rageval
from app.core import observability as langfuse_observability
from app.db import repository

router = APIRouter(prefix="/api/admin")

REVIEW_STATES = ("待审", "通过", "驳回")
CONTENT_TYPE_LABELS = {
    "faq": "常见问答",
    "policy": "政策流程",
    "manual": "操作手册",
    "spec": "线路说明",
}


def _card(key: str, title: str, page: str, lede: str) -> dict:
    """页面上不标章节号:后台是一个系统的几块功能,读者看的是「哪块要干活」,不是它出自第几章。"""
    return {"key": key, "title": title, "page": page, "lede": lede,
            "status": "error", "headline": "读数失败", "metrics": [], "note": None}


async def _kb_card() -> dict:
    """知识库:块数、待向量化、Milvus 条数。双写一致 = 没有块卡 pending 且两边条数对得上。"""
    card = _card("kb", "知识库", "/kb",
                 "文档与对话挖出来的知识 → 切块 → 双写 MySQL 与 Milvus")
    try:
        stats = await repository.knowledge_stats()
    except Exception as e:
        card["note"] = f"{type(e).__name__}: {e}"
        return card
    milvus = await kb.milvus_state()
    card["metrics"] = [
        {"label": "知识块", "value": stats["total"]},
        {"label": "待向量化", "value": stats["pending"]},
        {"label": "Milvus", "value": milvus["count"] if milvus["online"] else "离线"},
        {"label": "关键条款", "value": stats["key_clause"]},
    ]
    if not stats["total"]:
        card["status"], card["headline"] = "missing", "库是空的,先录入或跑一次离线建库"
    elif not milvus["online"]:
        card["status"], card["headline"] = "attention", f"MySQL 有 {stats['total']} 块,Milvus 离线"
    elif stats["pending"] or stats["done"] != milvus["count"]:
        card["status"] = "attention"
        card["headline"] = (f"{stats['pending']} 块待向量化,"
                            f"MySQL 已向量化 {stats['done']} 对 Milvus {milvus['count']}")
    else:
        card["status"] = "ok"
        card["headline"] = f"{stats['total']} 块双写一致,可被语义检索"
    card["note"] = "类型分布 " + " · ".join(
        f"{CONTENT_TYPE_LABELS.get(key, key)} {value}"
        for key, value in stats["by_content_type"].items()
    )
    return card


async def _operations_card() -> dict:
    """物流运营态势：演示运单、承运商、工具和回归样例的当前读数。"""
    card = _card("operations", "物流运营态势", "/logistics-dashboard",
                 "运单状态、承运商履约、异常分布与 Agent 工具能力")
    try:
        ov = await logistics_overview.overview()
    except Exception as exc:
        card["note"] = f"{type(exc).__name__}: {exc}"
        return card
    metrics, operations = ov["metrics"], ov["operations"]
    carriers = operations.get("carrier_summary") or {}
    exceptions = operations.get("exception_distribution") or {}
    card["metrics"] = [
        {"label": "演示运单", "value": operations.get("shipment_total", 0)},
        {"label": "承运商", "value": len(carriers)},
        {"label": "物流工具", "value": metrics.get("registered_tools", 0)},
        {"label": "回归样例", "value": metrics.get("regression_cases", 0)},
    ]
    milvus = metrics.get("milvus") or {}
    if not operations.get("shipment_total"):
        card["status"], card["headline"] = "missing", "当前没有可展示的运单样例"
    elif milvus.get("status") != "ready":
        card["status"], card["headline"] = "attention", "运单工具可用，知识检索服务未就绪"
    else:
        card["status"] = "ok"
        card["headline"] = (f"{operations['shipment_total']} 票运单在线，"
                            f"{len(exceptions)} 类异常，知识库向量服务正常")
    card["note"] = "当前为可复现的本地演示数据，不连接真实承运商生产系统"
    return card


async def _rageval_card() -> dict:
    """当前物流传统检索指标，并附最近 Agent 行为抽测。"""
    card = _card("rageval", "RAG 检索评测", "/rag-eval",
                 "固定 ground truth：Recall、Precision、MRR、NDCG 与端到端行为抽测")
    try:
        ov = await rageval.overview()
    except Exception as exc:
        card["note"] = f"{type(exc).__name__}: {exc}"
        return card
    if not ov.get("present"):
        card["status"], card["headline"] = "missing", "暂无当前物流传统检索报告"
        card["note"] = ov.get("hint")
        return card
    active = ((ov.get("retrieval") or {}).get("hybrid_rerank") or {})
    overall = active.get("overall") or {}
    behavior = ov.get("behavior") or {}
    meta = ov.get("meta") or {}
    card["metrics"] = [
        {"label": "检索样本", "value": meta.get("samples", 0)},
        {"label": "Recall@5", "value": f"{round((overall.get('recall_at_5') or 0) * 100)}%"},
        {"label": "MRR@5", "value": f"{round((overall.get('mrr_at_5') or 0) * 100)}%"},
        {"label": "NDCG@5", "value": f"{round((overall.get('ndcg_at_5') or 0) * 100)}%"},
    ]
    card["status"] = "ok" if not active.get("errors") and (overall.get("recall_at_5") or 0) >= .9 else "attention"
    card["headline"] = (f"生产策略 Recall@5 {round((overall.get('recall_at_5') or 0) * 100)}%，"
                        f"行为抽测 {behavior.get('passed', 0)}/{behavior.get('total', 0)}")
    best = ov.get("best") or {}
    card["note"] = f"当前指标最优策略：{best.get('strategy') or '暂无'}；旧电商报告已隔离"
    return card


async def _review_card() -> dict:
    """飞轮待审:答不上的问题标准化查重后攒在队列里,等人审。待审有货就是要干活。"""
    card = _card("review", "失败复盘", "/review",
                 "低置信度问题 → 标准化查重 → 人工审核 → 补充物流知识")
    try:
        counts = {st: len(await repository.list_review_queue(st)) for st in REVIEW_STATES}
    except Exception as e:
        card["note"] = f"{type(e).__name__}: {e}"
        return card
    card["metrics"] = [{"label": st, "value": counts[st]} for st in REVIEW_STATES]
    total = sum(counts.values())
    if not total:
        card["status"], card["headline"] = "missing", "队列还没有货,先在聊天页问几个答不上的问题"
    elif counts["待审"]:
        card["status"], card["headline"] = "attention", f"{counts['待审']} 条等着审"
    else:
        card["status"], card["headline"] = "ok", f"待审清零,累计处理 {total} 条"
    card["note"] = "审核通过即写回知识库并即时向量化,下一轮就能召回"
    return card


async def _topics_card() -> dict:
    """问题主题：旁路识别低置信度问题，用于决定下一批知识补充方向。"""
    card = _card("topics", "问题主题", "/topics",
                 "低置信度问题 → 主题识别 → 按缺口优先级补充物流知识")
    try:
        dist = await repository.topic_distribution()
    except Exception as e:
        card["note"] = f"{type(e).__name__}: {e}"
        return card
    hit = sum(1 for c in dist["classes"] if c["count"])
    # classes 是权威类目表的固定顺序,不是排行榜;要说「占前三」得自己按问题量排
    top = sorted((c for c in dist["classes"] if c["count"]),
                 key=lambda c: c["count"], reverse=True)[:3]
    card["metrics"] = [{"label": "已归类问题", "value": dist["total"]},
                       {"label": "命中类目", "value": f"{hit}/{len(dist['classes'])}"}]
    if not dist["total"]:
        card["status"], card["headline"] = "missing", "暂无主题样本，先积累几条低置信度问题"
    else:
        card["status"] = "ok"
        card["headline"] = "占前三:" + "、".join(f"{c['label']} {c['count']}" for c in top)
    return card


async def _agent_eval_card() -> dict:
    """Agent 综合评测:数据集就绪与最近在线行为指标,不在后台请求中重跑模型。"""
    card = _card("agent-eval", "Agent 综合评测", "/agent-eval",
                 "300 条物流问题 → 工具选择、库外拒答、边界澄清、证据表现")
    try:
        ov = agent_eval.build_overview()
    except Exception as e:
        card["note"] = f"{type(e).__name__}: {e}"
        return card
    dataset, live = ov["dataset"], ov["live"]
    card["metrics"] = [{"label": "评估集", "value": f"{dataset['total']} 条"},
                       {"label": "类别", "value": f"{len(dataset['categories'])} 类"}]
    if dataset["status"] != "ok":
        card["status"], card["headline"] = "attention", "评估集不完整,请先运行离线验收"
    elif live["status"] == "ok":
        summary = live["summary"] or {}
        card["status"] = "ok"
        card["headline"] = f"最近在线通过率 {round((summary.get('pass_rate') or 0) * 100)}%"
        card["metrics"].append({"label": "在线样本", "value": summary.get("total", "—")})
    elif live["status"] == "error":
        card["status"], card["headline"] = "error", "在线报告无法读取"
        card["note"] = live.get("note")
    else:
        card["status"], card["headline"] = "missing", "数据集已就绪,尚未在线评测"
        card["note"] = "建议先执行 5 条抽测,再决定是否跑完整 300 条"
    return card


async def _observability_card() -> dict:
    """Langfuse 是可选观测依赖：离线只标记降级，不代表 Agent 不可用。"""
    card = _card("observability", "链路观测", "/observability",
                 "LangGraph Trace、工具路由、延迟、Token、错误与用户反馈")
    runtime = await asyncio.to_thread(langfuse_observability.runtime_snapshot)
    metrics = runtime["metrics"]
    card["metrics"] = [
        {"label": "24h 近期样本", "value": metrics["requests"]},
        {"label": "错误", "value": metrics["errors"]},
        {"label": "平均延迟", "value": f"{metrics['avg_latency']:.2f}s"},
        {"label": "Token", "value": metrics["total_tokens"]},
    ]
    if runtime["status"] == "online":
        card["status"] = "attention" if metrics["errors"] else "ok"
        card["headline"] = (f"Langfuse 在线，P95 {metrics['p95_latency']:.2f}s，"
                            f"近期 {len(runtime['traces'])} 条链路可追溯")
    elif runtime["status"] == "unconfigured":
        card["status"], card["headline"] = "missing", "Langfuse 尚未配置，Agent 主链路不受影响"
    else:
        card["status"], card["headline"] = "attention", "Langfuse 已配置但当前不可达"
    card["note"] = runtime.get("note") or "点击进入查看最近 Trace 与意图成本分布"
    return card


@router.get("/overview")
async def overview() -> dict:
    return {"modules": [await _operations_card(), await _kb_card(), await _agent_eval_card(),
                        await _rageval_card(), await _observability_card(),
                        await _review_card(), await _topics_card()]}
