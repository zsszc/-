"""Langfuse 观测：可选挂载、运行摘要和反馈 Score 都必须可降级。"""
from types import SimpleNamespace
import httpx
import langfuse
from datetime import datetime, timezone

from app.core import observability


def test_local_langfuse_bypasses_environment_proxy(monkeypatch):
    captured = {}
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "pk-test")
    monkeypatch.setattr("app.config.settings.langfuse_secret_key", "sk-test")
    monkeypatch.setattr("app.config.settings.langfuse_base_url", "http://127.0.0.1:3000")
    monkeypatch.setattr(observability, "_client", None)
    monkeypatch.setattr(langfuse, "Langfuse", lambda **kwargs: captured.update(kwargs) or object())

    observability._init_client()
    assert isinstance(captured["httpx_client"], httpx.Client)
    assert captured["httpx_client"]._trust_env is False
    assert captured["span_exporter"]._session.trust_env is False
    assert captured["span_exporter"]._endpoint.endswith("/api/public/otel/v1/traces")
    captured["httpx_client"].close()


def test_remote_langfuse_keeps_default_transport(monkeypatch):
    captured = {}
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "pk-test")
    monkeypatch.setattr("app.config.settings.langfuse_secret_key", "sk-test")
    monkeypatch.setattr("app.config.settings.langfuse_base_url", "https://example.test")
    monkeypatch.setattr(observability, "_client", None)
    monkeypatch.setattr(langfuse, "Langfuse", lambda **kwargs: captured.update(kwargs) or object())
    observability._init_client()
    assert "httpx_client" not in captured
    assert "span_exporter" not in captured


def test_generation_token_batch_uses_local_transport_without_proxy(monkeypatch):
    monkeypatch.setattr("app.config.settings.langfuse_base_url", "http://localhost:3000")
    seen = {}

    def fake_get(url, **kwargs):
        seen.update({"url": url, **kwargs})
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"data": [
                {"traceId": "a", "totalTokens": 120},
                {"traceId": "a", "usage": {"total": 30}},
                {"traceId": "b", "totalTokens": 80},
            ]},
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    totals = observability._generation_tokens_by_trace(datetime.now(timezone.utc))
    assert totals == {"a": 150, "b": 80}
    assert seen["trust_env"] is False
    assert seen["params"]["type"] == "GENERATION"


def test_future_langfuse_timestamp_is_flagged_not_displayed():
    now = datetime(2026, 9, 19, tzinfo=timezone.utc)
    timestamp, anomalous = observability._safe_timestamp("9999-12-31T23:59:59Z", now)
    assert timestamp is None
    assert anomalous is True
    assert observability._trace_latency_seconds(
        {"timestamp": "9999-12-31T23:59:59Z", "latency": 7877}, now) == 7.877
    assert observability._trace_latency_seconds(
        {"timestamp": "2026-09-18T10:00:00Z", "latency": 8.965}, now) == 8.965


def test_disabled_when_keys_missing(monkeypatch):
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "")
    monkeypatch.setattr("app.config.settings.langfuse_secret_key", "sk")
    monkeypatch.setattr("app.config.settings.langfuse_base_url", "http://x")
    assert observability.langfuse_enabled() is False


def test_attach_returns_graph_unchanged_when_disabled(monkeypatch):
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "")
    sentinel = object()
    assert observability.attach_observability(sentinel) is sentinel


def test_tag_intent_noop_when_disabled(monkeypatch):
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "")
    observability.tag_intent("商品咨询", 0.9)   # 不许抛异常、不许要求 langfuse 已装好服务


def test_get_langfuse_none_when_disabled(monkeypatch):
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "")
    assert observability.get_langfuse() is None


def test_attach_wraps_with_callbacks_when_enabled(monkeypatch):
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "pk")
    monkeypatch.setattr("app.config.settings.langfuse_secret_key", "sk")
    monkeypatch.setattr("app.config.settings.langfuse_base_url", "http://localhost:3000")

    calls = {}

    class FakeGraph:
        def with_config(self, cfg):
            calls["cfg"] = cfg
            return "wrapped"

    monkeypatch.setattr(observability, "_init_client", lambda: object())
    monkeypatch.setattr(observability, "_make_handler", lambda: "HANDLER")
    assert observability.attach_observability(FakeGraph()) == "wrapped"
    assert calls["cfg"] == {"callbacks": ["HANDLER"]}


def test_runtime_snapshot_unconfigured(monkeypatch):
    monkeypatch.setattr("app.config.settings.langfuse_public_key", "")
    snap = observability.runtime_snapshot()
    assert snap["status"] == "unconfigured"
    assert snap["metrics"]["requests"] == 0


def test_runtime_snapshot_summarizes_without_exposing_io(monkeypatch):
    monkeypatch.setattr(observability, "langfuse_enabled", lambda: True)
    traces = [
        {"id": "a", "timestamp": "2026-09-18T10:00:00Z", "name": "LangGraph",
         "sessionId": "7", "tags": ["intent:清关咨询"], "latency": 1.0,
         "errorCount": 0, "input": "私密问题", "output": "私密回答"},
        {"id": "b", "timestamp": "2026-09-18T10:01:00Z", "name": "LangGraph",
         "sessionId": "8", "tags": [], "latency": 3.0,
         "errorCount": 1},
    ]
    fake = SimpleNamespace(
        api=SimpleNamespace(trace=SimpleNamespace(
            list=lambda **kwargs: SimpleNamespace(data=traces))),
        get_trace_url=lambda **kwargs: "http://lf/trace/" + kwargs["trace_id"],
    )
    monkeypatch.setattr(observability, "_init_client", lambda: fake)
    monkeypatch.setattr(observability, "_generation_tokens_by_trace", lambda since: {"a": 120, "b": 80})

    snap = observability.runtime_snapshot()
    assert snap["status"] == "online"
    assert snap["metrics"] == {"requests": 2, "errors": 1, "avg_latency": 2.0,
                               "p95_latency": 2.9, "total_tokens": 200}
    assert snap["traces"][0]["intent"] == "清关咨询"
    assert snap["traces"][0]["tokens"] == 120
    assert "input" not in snap["traces"][0] and "output" not in snap["traces"][0]


def test_score_feedback_targets_latest_session_trace(monkeypatch):
    monkeypatch.setattr(observability, "langfuse_enabled", lambda: True)
    scores = []
    fake = SimpleNamespace(
        api=SimpleNamespace(trace=SimpleNamespace(
            list=lambda **kwargs: SimpleNamespace(data=[{"id": "trace-1"}]))),
        create_score=lambda **kwargs: scores.append(kwargs),
    )
    monkeypatch.setattr(observability, "_init_client", lambda: fake)
    assert observability.score_session_feedback(9, "down", "没解决") is True
    assert scores[0]["trace_id"] == "trace-1"
    assert scores[0]["value"] is False and scores[0]["data_type"] == "BOOLEAN"


def test_score_feedback_failure_is_safe(monkeypatch):
    monkeypatch.setattr(observability, "langfuse_enabled", lambda: True)
    monkeypatch.setattr(observability, "_init_client", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    assert observability.score_session_feedback(9, "up") is False
