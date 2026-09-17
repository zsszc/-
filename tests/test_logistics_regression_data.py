import json
from pathlib import Path

from app.core.intent import INTENTS
from app.core.taxonomy import TOPIC_NAMES


CASES = Path(__file__).parents[1] / "data" / "evals" / "logistics_regression.jsonl"
CAPABILITIES = {"rag", "shipment_query", "shipping_fee", "exception_classify", "prohibited_check"}


def test_logistics_regression_dataset_contract():
    rows = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) >= 30
    assert len({row["id"] for row in rows}) == len(rows)
    for row in rows:
        assert {"id", "query", "intent", "topic", "expected_capability"} <= row.keys()
        assert row["intent"] in INTENTS
        assert row["topic"] in TOPIC_NAMES
        assert row["expected_capability"] in CAPABILITIES
    assert len({row["topic"] for row in rows}) >= 12
    capability_counts = {cap: sum(row["expected_capability"] == cap for row in rows) for cap in CAPABILITIES}
    assert all(count >= 3 for count in capability_counts.values())
