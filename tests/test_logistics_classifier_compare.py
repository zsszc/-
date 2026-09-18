import json
from pathlib import Path

from scripts.ch10.compare_logistics_classifier import main


def test_logistics_classifier_before_after_report():
    main()
    report = json.loads(Path("data/ch10/reports/logistics_classifier_comparison.json").read_text(encoding="utf-8"))
    assert report["baseline_samples"] > 0
    assert report["holdout_size"] == 10
    assert report["augmented_accuracy"] >= report["baseline_accuracy"]
    assert len(report["rows"]) == report["holdout_size"]
