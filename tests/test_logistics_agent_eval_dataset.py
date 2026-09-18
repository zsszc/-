import json
from collections import Counter
from pathlib import Path

from scripts.build_logistics_agent_eval import main


def test_agent_eval_dataset_has_stratified_300_cases():
    main()
    path = Path("data/evals/logistics_agent_eval.jsonl")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 300
    assert Counter(row["category"] for row in rows) == Counter({
        "policy_process": 100, "cross_document": 70, "tool_operation": 60,
        "out_of_scope": 50, "boundary_clarification": 20,
    })
    assert len({row["query"] for row in rows}) == 300
    assert sum(row["must_abstain"] for row in rows) == 50
    assert all({"id", "category", "query", "gold_topic", "expected_tools", "must_abstain", "requires_citations", "note"} <= row.keys() for row in rows)
