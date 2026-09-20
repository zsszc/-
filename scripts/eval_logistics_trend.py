"""Run the current logistics retrieval benchmark and append one comparable trend point."""

from __future__ import annotations

import argparse
import asyncio
import json

from app.core.eval_meta import LOGISTICS_RETRIEVAL_DATASET
from app.db import repository
from scripts.eval_logistics_retrieval import evaluate_strategy, load_cases

DATASET_ID = LOGISTICS_RETRIEVAL_DATASET


def metrics_from_summary(summary: dict, *, sample_count: int) -> dict:
    if summary.get("errors"):
        raise RuntimeError(f"检索失败 {summary['errors']} 条；本轮不写趋势，避免把故障算成零分")
    overall = summary.get("overall") or {}
    names = ("recall_at_5", "mrr_at_5", "ndcg_at_5")
    if sample_count != 30 or any(name not in overall for name in names):
        raise ValueError("物流评测样本数或指标不完整；本轮不写趋势")
    return {"dataset": DATASET_ID, **{name: overall[name] for name in names}}


async def run_once(triggered_by: str) -> dict:
    cases = load_cases()
    summary, _details = await evaluate_strategy("hybrid_rerank", cases, concurrency=3)
    metrics = metrics_from_summary(summary, sample_count=len(cases))
    run_id = await repository.insert_eval_run(triggered_by, len(cases), metrics)
    return {"run_id": run_id, "dataset": DATASET_ID, "dataset_size": len(cases),
            "strategy": "hybrid_rerank", "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triggered-by", default="手动", choices=("手动", "定时"))
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run_once(args.triggered_by)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
