import json
from pathlib import Path

from scripts.ch10.build_logistics_classifier_benchmark import main


def test_single_topic_classifier_benchmark_is_balanced_and_disjoint():
    main()
    root = Path("data/ch10/dataset")
    val = [json.loads(line) for line in (root / "logistics_val_v2.jsonl").read_text().splitlines() if line.strip()]
    test = [json.loads(line) for line in (root / "logistics_test_v2.jsonl").read_text().splitlines() if line.strip()]
    train = [json.loads(line) for line in (root / "logistics_train_v2.jsonl").read_text().splitlines() if line.strip()]
    assert len(val) == 51 and len(test) == 170
    assert len({row["labels"][0] for row in val}) == 17
    assert len({row["labels"][0] for row in test}) == 17
    assert not ({row["text"] for row in train} | {row["text"] for row in val}) & {row["text"] for row in test}
    assert all(len(row["labels"]) == 1 for row in val + test)
