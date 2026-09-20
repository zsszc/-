"""ch09 可观测:Langfuse 挂载与 trace 标注,全部可选降级。

观测通过三个环境变量配置，并在工作流编译时挂载一次回调，节点业务代码无需侵入。
项目配置经 pydantic-settings(.env),不依赖 os.environ,故显式传参初始化单例。
所有对外函数在未配置 Langfuse 时必须是安全 no-op——观测是增强,不是依赖。

实装 SDK 为 langfuse 4.x:构造参 base_url(host 已弃用);给运行中的 trace 补
metadata/tags 用 propagate_attributes 上下文管理器(v3 的 update_current_trace 已移除)。
"""
import logging
import math
import base64
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger(__name__)
_client = None


def langfuse_enabled() -> bool:
    return bool(settings.langfuse_public_key and settings.langfuse_secret_key
                and settings.langfuse_base_url)


def _init_client():
    """初始化(或复用)Langfuse 单例。"""
    global _client
    if _client is None:
        from langfuse import Langfuse
        options = {}
        # 部分 macOS 环境的代理会截获 Python 发往回环地址的请求并返回空 502；
        # 只为本机 Langfuse 禁用环境代理，远程实例仍使用 SDK 默认连接方式。
        if urlparse(settings.langfuse_base_url).hostname in {"localhost", "127.0.0.1", "::1"}:
            import httpx
            import requests
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            session = requests.Session()
            session.trust_env = False
            credentials = f"{settings.langfuse_public_key}:{settings.langfuse_secret_key}"
            authorization = base64.b64encode(credentials.encode()).decode()
            options = {
                "httpx_client": httpx.Client(timeout=5, trust_env=False),
                "span_exporter": OTLPSpanExporter(
                    endpoint=f"{settings.langfuse_base_url.rstrip('/')}/api/public/otel/v1/traces",
                    headers={"Authorization": f"Basic {authorization}"},
                    session=session,
                    timeout=5,
                ),
            }
        _client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_base_url,
            **options,
        )
    return _client


def _make_handler():
    from langfuse.langchain import CallbackHandler

    class _InlineCallbackHandler(CallbackHandler):
        """run_inline=True:让 LangChain 在调用方协程内联执行回调,而不是丢进独立 task。
        没有它,handler 的 OTel context.attach 挂在别的 task 上,节点代码里没有活动
        span 上下文,tag_intent 的 propagate_attributes 写不进当前 trace(实测踩坑)。"""
        run_inline = True

    return _InlineCallbackHandler()


def get_langfuse():
    """启用时返回已初始化 client(cost 脚本用 client.api 查询);未启用返回 None。"""
    if not langfuse_enabled():
        return None
    return _init_client()


def attach_observability(graph):
    """编译后挂一次 Langfuse 回调,全图自动 trace(README:「编译时挂一次,节点里一行不用动」)。
    未配置时原样返回——不挂、不 import langfuse。"""
    if not langfuse_enabled():
        return graph
    _init_client()
    return graph.with_config({"callbacks": [_make_handler()]})


def tag_intent(intent: str, confidence: float) -> None:
    """把意图写进当前 trace 的 metadata + tag(Cost Control 按意图分堆的钩子)。
    任何异常静默降级——观测失败不许影响业务流。"""
    if not langfuse_enabled():
        return
    try:
        from langfuse import get_client, propagate_attributes
        # 不能只 with...pass 写"当前活动 span"——LangGraph 异步调度下它可能已 ended,
        # OTel 对 ended span 的写入静默丢弃(实测踩坑)。改为在传播上下文内新建一个
        # event 观测:新 span 必然存活,trace 级属性(metadata/tags)随它上提到整条 trace。
        with propagate_attributes(
            metadata={"intent": intent, "intent_confidence": f"{confidence:.2f}"},
            tags=[f"intent:{intent}"],
        ):
            get_client().create_event(name="intent-tagged")
    except Exception:
        logger.warning("langfuse tag_intent 失败(已忽略)", exc_info=True)


def _dump_model(value) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return value
    return {}


def _number(row: dict, *names: str) -> float:
    for name in names:
        value = row.get(name)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _percentile(values: list[float], p: float) -> float:
    """线性插值分位数；只用于后台近期 Trace 摘要，不作评测指标。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * p
    low, high = math.floor(pos), math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def _generation_tokens_by_trace(since: datetime) -> dict[str, int]:
    """自部署 Langfuse v3 的 Trace 列表不返回 token 汇总；批量读取生成观测。"""
    import httpx

    local = urlparse(settings.langfuse_base_url).hostname in {"localhost", "127.0.0.1", "::1"}
    totals: dict[str, int] = {}
    # v3 每页最多 100 条；后台只做近期样本摘要，最多读取 5 页。
    for page in range(1, 6):
        response = httpx.get(
            f"{settings.langfuse_base_url.rstrip('/')}/api/public/observations",
            params={"page": page, "limit": 100, "type": "GENERATION",
                    "fromStartTime": since.isoformat()},
            auth=(settings.langfuse_public_key, settings.langfuse_secret_key),
            timeout=5, trust_env=not local,
        )
        response.raise_for_status()
        body = response.json()
        for row in body.get("data", []):
            trace_id = row.get("traceId")
            if trace_id:
                tokens = _number(row, "totalTokens", "total_tokens")
                if not tokens:
                    tokens = _number(row.get("usage") or {}, "total")
                totals[trace_id] = totals.get(trace_id, 0) + int(tokens)
        if page >= (body.get("meta") or {}).get("totalPages", 1):
            break
    return totals


def _safe_timestamp(value, now: datetime) -> tuple[str | None, bool]:
    """对异常未来时间戳显式标记，避免把 9999 年误当作正常发生时间。"""
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        parsed = parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        if parsed > now + timedelta(minutes=5):
            return None, True
        return parsed.isoformat(), False
    except (ValueError, TypeError, OverflowError):
        return None, bool(value)


def _trace_latency_seconds(row: dict, now: datetime) -> float:
    latency = _number(row, "latency")
    # 正常 v3 Trace API 返回秒；仅旧 26.8 异常时间戳数据表现为放大 1000 倍。
    _, anomalous = _safe_timestamp(row.get("timestamp"), now)
    return latency / 1000 if anomalous else latency


def runtime_snapshot(*, limit: int = 50, window_hours: int = 24) -> dict:
    """读 Langfuse 近期 Trace 的安全摘要。不返回 input/output，避免后台总览扩散用户原文。"""
    base = {
        "enabled": langfuse_enabled(),
        "status": "unconfigured",
        "base_url": settings.langfuse_base_url or None,
        "window_hours": window_hours,
        "metrics": {"requests": 0, "errors": 0, "avg_latency": 0.0,
                    "p95_latency": 0.0, "total_tokens": 0},
        "traces": [],
        "note": "请在 .env 配置 Langfuse 三项参数并启动服务。",
    }
    if not base["enabled"]:
        return base
    try:
        client = _init_client()
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=window_hours)
        response = client.api.trace.list(
            limit=limit, from_timestamp=since, order_by="timestamp.desc",
            fields="core,metrics,scores",
        )
        rows = [_dump_model(item) for item in (getattr(response, "data", None) or [])]
        try:
            generation_tokens = _generation_tokens_by_trace(since) if rows else {}
        except Exception:
            logger.warning("Langfuse 生成用量读取失败，继续显示 Trace 摘要", exc_info=True)
            generation_tokens = {}
        latencies = [_trace_latency_seconds(row, now) for row in rows
                     if _number(row, "latency") >= 0]
        errors = sum(1 for row in rows if (
            _number(row, "errorCount", "error_count") > 0
            or str(row.get("level") or "").upper() == "ERROR"
        ))
        total_tokens = int(sum(generation_tokens.get(str(row.get("id")),
                              _number(row, "totalTokens", "total_tokens", "tokens"))
                               for row in rows))
        traces = []
        anomalous_timestamps = 0
        for row in rows[:20]:
            tags = [str(tag) for tag in (row.get("tags") or [])]
            intent = next((tag.removeprefix("intent:") for tag in tags
                           if tag.startswith("intent:")), None)
            trace_id = str(row.get("id") or "")
            timestamp, anomalous = _safe_timestamp(row.get("timestamp"), now)
            anomalous_timestamps += int(anomalous)
            traces.append({
                "id": trace_id,
                "name": row.get("name") or "Agent 调用",
                "timestamp": timestamp,
                "timestamp_anomaly": anomalous,
                "session_id": row.get("sessionId") or row.get("session_id"),
                "intent": intent,
                "tags": tags,
                "latency": round(_trace_latency_seconds(row, now), 3),
                "tokens": int(generation_tokens.get(trace_id,
                              _number(row, "totalTokens", "total_tokens", "tokens"))),
                "error": (_number(row, "errorCount", "error_count") > 0
                          or str(row.get("level") or "").upper() == "ERROR"),
                "score_count": len(row.get("scores") or []),
                "url": client.get_trace_url(trace_id=trace_id) if trace_id else None,
            })
        return {
            **base,
            "status": "online",
            "metrics": {
                "requests": len(rows),
                "errors": errors,
                "avg_latency": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
                "p95_latency": round(_percentile(latencies, .95), 3),
                "total_tokens": total_tokens,
            },
            "traces": traces,
            "note": ("Langfuse 返回异常未来时间戳；当前近期窗口可能包含窗口外数据，请勿将请求数解读为精确 24 小时总量。"
                     if anomalous_timestamps else
                     None if rows else f"近 {window_hours} 小时暂无 Trace，可先在聊天页发起一次对话。"),
        }
    except Exception as exc:  # 观测故障不得影响业务接口
        logger.warning("Langfuse 运行摘要读取失败", exc_info=True)
        return {**base, "status": "unreachable",
                "note": f"Langfuse 暂不可达：{type(exc).__name__}"}


def score_session_feedback(conversation_id: int, rating: str, question: str = "") -> bool:
    """将反馈写到该会话最近 Trace。查找或写入失败均安全降级。"""
    if not langfuse_enabled():
        return False
    try:
        client = _init_client()
        response = client.api.trace.list(
            limit=1, session_id=str(conversation_id), order_by="timestamp.desc",
            fields="core",
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return False
        trace_id = _dump_model(rows[0]).get("id")
        if not trace_id:
            return False
        client.create_score(
            trace_id=trace_id,
            name="user_feedback",
            value=(rating == "up"),
            data_type="BOOLEAN",
            comment=(question[:200] if question else None),
            metadata={"source": "chat_ui", "conversation_id": conversation_id},
        )
        return True
    except Exception:
        logger.warning("Langfuse 用户反馈 Score 写入失败 conv=%s", conversation_id,
                       exc_info=True)
        return False
