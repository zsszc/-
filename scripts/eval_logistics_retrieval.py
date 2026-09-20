"""Evaluate the current logistics knowledge base with traditional retrieval metrics."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core import retrieval

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data/evals/logistics_retrieval_eval.jsonl"
DEFAULT_REPORT = ROOT / "data/evals/logistics_retrieval_eval_report.json"
STRATEGIES = ("vector", "bm25", "hybrid", "hybrid_rerank")
K_VALUES = (1, 3, 5)
TOP_K = max(K_VALUES)


def load_cases(path: Path = DEFAULT_DATASET) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 30:
        raise ValueError(f"检索评测集应为 30 条，实际为 {len(rows)} 条")
    if len({row.get("id") for row in rows}) != len(rows):
        raise ValueError("检索评测集存在重复 id")
    if len({row.get("query") for row in rows}) != len(rows):
        raise ValueError("检索评测集存在重复 query")
    kinds = defaultdict(int)
    sections: set[str] = set()
    for row in rows:
        if not {"id", "query", "expected_sections", "kind"} <= row.keys():
            raise ValueError(f"{row.get('id', '<unknown>')} 字段不完整")
        if row["kind"] not in {"single", "multi"}:
            raise ValueError(f"{row['id']} kind 只能是 single/multi")
        if not row["expected_sections"]:
            raise ValueError(f"{row['id']} 没有相关小节标注")
        if row["kind"] == "single" and len(row["expected_sections"]) != 1:
            raise ValueError(f"{row['id']} single 样本必须只标一个相关小节")
        if row["kind"] == "multi" and len(row["expected_sections"]) < 2:
            raise ValueError(f"{row['id']} multi 样本至少标两个相关小节")
        kinds[row["kind"]] += 1
        sections.update(row["expected_sections"])
    if dict(kinds) != {"single": 19, "multi": 11}:
        raise ValueError(f"样本类型分布应为 single=19/multi=11，实际为 {dict(kinds)}")
    if len(sections) != 19:
        raise ValueError(f"ground truth 应覆盖 19 个知识小节，实际为 {len(sections)}")
    return rows


def relevance_at_ranks(hits: list[dict], expected_sections: list[str], top_k: int = TOP_K) -> list[int]:
    """返回每个名次的二元相关性；同一相关小节重复出现只在首次命中时计分。"""
    expected = set(expected_sections)
    matched: set[str] = set()
    relevance: list[int] = []
    for hit in hits[:top_k]:
        section = str(hit.get("section_path") or "")
        relevant = section in expected and section not in matched
        relevance.append(int(relevant))
        if relevant:
            matched.add(section)
    relevance.extend([0] * (top_k - len(relevance)))
    return relevance


def metrics_for_case(hits: list[dict], expected_sections: list[str]) -> dict[str, float]:
    rel = relevance_at_ranks(hits, expected_sections)
    total_relevant = len(set(expected_sections))
    out: dict[str, float] = {}
    for k in K_VALUES:
        found = sum(rel[:k])
        out[f"hit_rate_at_{k}"] = float(found > 0)
        out[f"precision_at_{k}"] = found / k
        out[f"recall_at_{k}"] = found / total_relevant
    first = next((index + 1 for index, value in enumerate(rel[:TOP_K]) if value), 0)
    out["mrr_at_5"] = 1.0 / first if first else 0.0
    dcg = sum(value / math.log2(index + 2) for index, value in enumerate(rel[:TOP_K]))
    ideal_count = min(total_relevant, TOP_K)
    idcg = sum(1.0 / math.log2(index + 2) for index in range(ideal_count))
    out["ndcg_at_5"] = dcg / idcg if idcg else 0.0
    return out


def aggregate(items: list[dict[str, float]]) -> dict[str, float]:
    if not items:
        return {}
    return {
        key: round(sum(item[key] for item in items) / len(items), 4)
        for key in items[0]
    }


async def evaluate_strategy(
    strategy: str, cases: list[dict[str, Any]], concurrency: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(case: dict[str, Any]) -> dict[str, Any]:
        try:
            async with semaphore:
                hits = await retrieval.search_knowledge(
                    case["query"], strategy=strategy, top_k=TOP_K,
                )
            metrics = metrics_for_case(hits, case["expected_sections"])
            return {
                "id": case["id"], "kind": case["kind"], "query": case["query"],
                "expected_sections": case["expected_sections"], "metrics": metrics,
                "hits": [
                    {"rank": rank, "section_path": hit.get("section_path"),
                     "question": hit.get("question")}
                    for rank, hit in enumerate(hits[:TOP_K], 1)
                ],
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001 - 每条错误进入报告，整轮仍可审计
            return {
                "id": case["id"], "kind": case["kind"], "query": case["query"],
                "expected_sections": case["expected_sections"],
                "metrics": metrics_for_case([], case["expected_sections"]),
                "hits": [], "error": f"{type(exc).__name__}: {exc}",
            }

    details = await asyncio.gather(*(one(case) for case in cases))
    overall = aggregate([item["metrics"] for item in details])
    by_kind = {
        kind: aggregate([item["metrics"] for item in details if item["kind"] == kind])
        for kind in ("single", "multi")
    }
    return {
        "overall": overall,
        "by_kind": by_kind,
        "errors": sum(bool(item["error"]) for item in details),
    }, details


async def run(args: argparse.Namespace) -> dict[str, Any]:
    cases = load_cases(args.dataset)
    strategy_reports: dict[str, Any] = {}
    result_details: dict[str, Any] = {}
    for strategy in args.strategies:
        summary, details = await evaluate_strategy(strategy, cases, args.concurrency)
        strategy_reports[strategy] = summary
        result_details[strategy] = details
    return {
        "meta": {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "dataset": str(args.dataset.relative_to(ROOT)),
            "samples": len(cases),
            "single_samples": sum(case["kind"] == "single" for case in cases),
            "multi_samples": sum(case["kind"] == "multi" for case in cases),
            "relevant_sections": len({s for case in cases for s in case["expected_sections"]}),
            "top_k": TOP_K,
        },
        "strategies": strategy_reports,
        "results": result_details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    if args.concurrency < 1:
        parser.error("--concurrency 必须大于 0")
    report = asyncio.run(run(args))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"meta": report["meta"], "strategies": report["strategies"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
