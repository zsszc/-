"""Evaluate the logistics Agent dataset offline or against a running API."""

import argparse
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data/evals/logistics_agent_eval.jsonl"
DEFAULT_REPORT = ROOT / "data/evals/logistics_agent_eval_report_live_v3.json"
EVAL_VERSION = 3
EXPECTED_COUNTS = {
    "policy_process": 100,
    "cross_document": 70,
    "tool_operation": 60,
    "out_of_scope": 50,
    "boundary_clarification": 20,
}
TOOL_ALIASES = {"ticket_draft": {"ticket_draft", "create_ticket"}}
REFUSAL_MARKERS = ("无法", "不能", "不确定", "没有相关", "超出", "建议转人工", "人工客服")
CLARIFY_MARKERS = ("请提供", "需要补充", "还缺少", "缺少", "运单号", "重量", "目的地", "申报价值")
EVIDENCE_MARKERS = ("知识库", "依据", "参考", "来源", "[1]", "[2]", "政策")


def load_cases(path: Path = DEFAULT_DATASET) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    required = {"id", "category", "query", "gold_topic", "expected_tools", "must_abstain", "requires_citations", "note"}
    if len(rows) != 300:
        raise ValueError(f"评估集应为 300 条，实际为 {len(rows)} 条")
    if Counter(row.get("category") for row in rows) != Counter(EXPECTED_COUNTS):
        raise ValueError(f"评估集分类分布不符合预期: {dict(Counter(row.get('category') for row in rows))}")
    if len({row.get("query") for row in rows}) != len(rows):
        raise ValueError("评估集存在重复 query")
    for row in rows:
        missing = required - row.keys()
        if missing:
            raise ValueError(f"{row.get('id', '<unknown>')} 缺少字段: {sorted(missing)}")
    return rows


def _actual_tool_names(response: dict[str, Any]) -> set[str]:
    return {item.get("name", "") for item in response.get("tool_calls", [])}


def _has_expected_tool(expected: str, actual: set[str]) -> bool:
    return bool(actual & TOOL_ALIASES.get(expected, {expected}))


def select_cases(cases: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """按类别轮询抽样，避免 --limit 只取到文件开头的政策题。"""
    if not limit or limit >= len(cases):
        return cases
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["category"]].append(case)
    selected = []
    categories = list(grouped)
    index = 0
    while len(selected) < limit:
        category = categories[index % len(categories)]
        if grouped[category]:
            selected.append(grouped[category].pop(0))
        index += 1
    return selected


def score_case(case: dict[str, Any], response: dict[str, Any]) -> tuple[bool, str]:
    answer = str(response.get("answer") or "")
    actual = _actual_tool_names(response)
    category = case["category"]
    if category == "tool_operation":
        expected = case.get("expected_tools", [])
        return (any(_has_expected_tool(tool, actual) for tool in expected), f"actual_tools={sorted(actual)}")
    if category == "cross_document" and "query_shipment" in case.get("expected_tools", []) and not actual:
        clarified = any(marker in answer for marker in CLARIFY_MARKERS)
        return (clarified, f"missing_tracking_clarification={clarified}")
    if category == "out_of_scope":
        suggested = json.dumps(response.get("suggested_actions", []), ensure_ascii=False)
        refused = any(marker in answer for marker in REFUSAL_MARKERS + ("转人工",))
        return (not actual and (refused or "转人工" in suggested), f"actual_tools={sorted(actual)}")
    if category == "boundary_clarification":
        interrupted = bool(response.get("interrupt"))
        clarified = any(marker in answer for marker in CLARIFY_MARKERS)
        return (not actual and (clarified or interrupted), f"clarified={clarified}, interrupted={interrupted}")
    evidence = any(marker in answer for marker in EVIDENCE_MARKERS)
    # 工具返回的结构化结果本身就是本轮证据;不要求工具型回答强行伪造 FAQ 编号。
    successful_tool_result = any(item.get("ok") for item in response.get("tool_results", []))
    evidence = evidence or successful_tool_result
    if case.get("requires_citations"):
        evidence = evidence or any(
            any(marker in str(item.get("content", "")) for marker in EVIDENCE_MARKERS)
            for item in response.get("tool_results", [])
        )
    return (bool(answer.strip()) and (evidence if case.get("requires_citations") else True), f"evidence={evidence}")


async def evaluate_live(cases: list[dict[str, Any]], base_url: str, concurrency: int = 3) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(case: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            payload = {"user_id": "eval-logistics-agent", "message": case["query"]}
            try:
                async with httpx.AsyncClient(base_url=base_url, timeout=90, trust_env=False) as client:
                    response = await client.post("/api/agent", json=payload)
                    response.raise_for_status()
                    body = response.json()
                passed, reason = score_case(case, body)
                return {"id": case["id"], "category": case["category"], "passed": passed, "reason": reason, "response": body}
            except Exception as exc:  # noqa: BLE001 - report per-case service failures
                return {"id": case["id"], "category": case["category"], "passed": False, "reason": f"request_failed: {type(exc).__name__}: {exc}"}

    return await asyncio.gather(*(one(case) for case in cases))


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["category"]].append(result)
    by_category = {
        category: {"total": len(items), "passed": sum(item["passed"] for item in items), "pass_rate": round(sum(item["passed"] for item in items) / len(items), 4)}
        for category, items in sorted(grouped.items())
    }
    return {"total": len(results), "passed": sum(item["passed"] for item in results), "pass_rate": round(sum(item["passed"] for item in results) / len(results), 4) if results else 0, "by_category": by_category}


def _checkpoint(path: Path, cases: list[dict[str, Any]], results: dict[str, dict],
                base_url: str) -> dict[str, Any]:
    ordered = [results[case["id"]] for case in cases if case["id"] in results]
    report = {
        "eval_version": EVAL_VERSION, "dataset": str(DEFAULT_DATASET.relative_to(ROOT)),
        "base_url": base_url, "target_total": len(cases),
        "completed": len(ordered), "remaining": len(cases) - len(ordered),
        "summary": summarize(ordered), "results": ordered,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return report


async def evaluate_with_checkpoints(
    cases: list[dict[str, Any]], base_url: str, report_path: Path, *,
    concurrency: int, batch_size: int, resume: bool = False,
    retry_failed: bool = False,
) -> dict[str, Any]:
    results: dict[str, dict] = {}
    if resume and report_path.exists():
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        if previous.get("eval_version") != EVAL_VERSION or previous.get("base_url") != base_url:
            raise ValueError("评测版本或目标地址与断点报告不一致，拒绝混跑")
        results = {row["id"]: row for row in previous.get("results", [])}
    pending = [case for case in cases if case["id"] not in results or
               (retry_failed and str(results[case["id"]].get("reason", "")).startswith("request_failed:"))]
    report = _checkpoint(report_path, cases, results, base_url)
    for start in range(0, len(pending), batch_size):
        batch = pending[start:start + batch_size]
        for row in await evaluate_live(batch, base_url, concurrency):
            results[row["id"]] = row
        report = _checkpoint(report_path, cases, results, base_url)
        print(f"进度 {report['completed']}/{report['target_total']}，"
              f"通过 {report['summary']['passed']}，"
              f"请求失败 {sum(str(r.get('reason', '')).startswith('request_failed:') for r in report['results'])}",
              flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--offline", action="store_true", help="只校验评估集，不调用模型")
    parser.add_argument("--live", action="store_true", help="调用正在运行的 /api/agent")
    parser.add_argument("--limit", type=int, default=0, help="在线模式最多调用多少条，0 表示全部")
    parser.add_argument("--base-url", default=os.getenv("MEWHELP_EVAL_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--concurrency", type=int, default=1, help="在线请求并发数，默认串行以降低上游限流风险")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--resume", action="store_true", help="从同版本、同目标地址的本地报告续跑")
    parser.add_argument("--retry-failed", action="store_true", help="续跑时仅重试请求错误，不重试行为评分失败")
    args = parser.parse_args()
    if args.offline == args.live:
        parser.error("请二选一传入 --offline 或 --live")
    cases = load_cases(args.dataset)
    if args.offline:
        print(json.dumps({"status": "PASS", "total": len(cases), "categories": EXPECTED_COUNTS}, ensure_ascii=False, indent=2))
        return
    if args.limit < 0:
        parser.error("--limit 不能为负数")
    if args.concurrency < 1:
        parser.error("--concurrency 必须大于 0")
    if args.batch_size < 1:
        parser.error("--batch-size 必须大于 0")
    selected = select_cases(cases, args.limit)
    report = asyncio.run(evaluate_with_checkpoints(
        selected, args.base_url, args.report, concurrency=args.concurrency,
        batch_size=args.batch_size, resume=args.resume, retry_failed=args.retry_failed))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
