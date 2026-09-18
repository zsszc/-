import json
from collections import Counter
from pathlib import Path

from scripts.ch10.build_logistics_dataset_v2 import main


def test_logistics_dataset_v2_has_natural_and_hard_negative_sources():
    main()
    rows = [json.loads(line) for line in Path("data/ch10/dataset/logistics_train_v2.jsonl").read_text().splitlines() if line.strip()]
    assert len(rows) == 300
    assert len({row["text"] for row in rows}) == 300
    assert Counter(row["source"] for row in rows) == Counter({"natural_hard_negative": 272, "regression_variant": 28})
    assert len({row["labels"][0] for row in rows}) == 17
