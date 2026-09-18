import json
from pathlib import Path

from app.core.taxonomy import TOPIC_NAMES
from scripts.ch10.build_logistics_dataset import main


def test_generated_logistics_dataset_is_balanced_and_disjoint():
    main()
    root = Path("data/ch10/dataset")
    train = [json.loads(line) for line in (root / "logistics_train.jsonl").read_text().splitlines() if line.strip()]
    val = [json.loads(line) for line in (root / "logistics_val.jsonl").read_text().splitlines() if line.strip()]
    test = [json.loads(line) for line in (root / "logistics_test.jsonl").read_text().splitlines() if line.strip()]
    assert len(train) >= 120
    assert len(test) >= 50
    assert len(val) >= 17
    assert {row["labels"][0] for row in train} == set(TOPIC_NAMES)
    assert {row["labels"][0] for row in test} == set(TOPIC_NAMES)
    assert {row["labels"][0] for row in val} == set(TOPIC_NAMES)
    texts = [{row["text"] for row in rows} for rows in (train, val, test)]
    assert not ((texts[0] & texts[1]) | (texts[0] & texts[2]) | (texts[1] & texts[2]))
    assert all(set(row.keys()) >= {"text", "labels"} for row in train + val + test)
