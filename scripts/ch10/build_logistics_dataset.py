"""生成可复现的物流主题分类训练/测试集。"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core.taxonomy import TOPIC_CLASSES, TOPIC_NAMES

REGRESSION = ROOT / "data/evals/logistics_regression.jsonl"
OUT = ROOT / "data/ch10/dataset"
REPORT = ROOT / "data/ch10/reports/logistics_dataset_report.json"


def load_regression() -> list[dict]:
    return [json.loads(line) for line in REGRESSION.read_text(encoding="utf-8").splitlines() if line.strip()]


def make_sample(text: str, label: str, sample_id: str, source: str) -> dict:
    return {"id": sample_id, "text": text, "labels": [label], "source": source}


def build() -> tuple[list[dict], list[dict], list[dict]]:
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for index, topic in enumerate(TOPIC_CLASSES):
        for variant, example in enumerate(topic.examples):
            train.append(make_sample(f"{example}，跨境物流客服应该怎么处理？", topic.name,
                                     f"syn-train-{index:02d}-{variant:02d}", "taxonomy_variant"))
            train.append(make_sample(f"请问{example}，需要准备什么资料？", topic.name,
                                     f"syn-train-{index:02d}-{variant:02d}-b", "taxonomy_variant"))
        test.append(make_sample(f"我想咨询{topic.boundary}，能给我一个处理建议吗？", topic.name,
                                f"syn-test-{index:02d}-a", "taxonomy_holdout"))
        test.append(make_sample(f"关于{topic.examples[0]}，这类跨境问题应该找谁确认？", topic.name,
                                f"syn-test-{index:02d}-b", "taxonomy_holdout"))
        test.append(make_sample(f"遇到{topic.examples[-1]}，我想知道下一步怎么做。", topic.name,
                                f"syn-test-{index:02d}-c", "taxonomy_holdout"))
        val.append(make_sample(f"如果是{topic.examples[1]}，通常要如何跟进？", topic.name,
                               f"syn-val-{index:02d}", "taxonomy_validation"))
    regression = load_regression()
    for index, item in enumerate(regression):
        target = train if index < 24 else test
        target.append(make_sample(item["query"], item["topic"], f"reg-{index:03d}", "logistics_regression"))
    return train, val, test


def validate(train: list[dict], val: list[dict], test: list[dict]) -> dict:
    train_texts = {item["text"] for item in train}
    val_texts = {item["text"] for item in val}
    test_texts = {item["text"] for item in test}
    labels = set(TOPIC_NAMES)
    all_items = train + val + test
    invalid = [item for item in all_items if not set(item["labels"]) <= labels]
    report = {
        "train_size": len(train), "val_size": len(val), "test_size": len(test),
        "train_topic_counts": dict(sorted(Counter(item["labels"][0] for item in train).items())),
        "test_topic_counts": dict(sorted(Counter(item["labels"][0] for item in test).items())),
        "val_topic_counts": dict(sorted(Counter(item["labels"][0] for item in val).items())),
        "train_topics": len({item["labels"][0] for item in train}),
        "test_topics": len({item["labels"][0] for item in test}),
        "val_topics": len({item["labels"][0] for item in val}),
        "duplicate_texts": len((train_texts & val_texts) | (train_texts & test_texts) | (val_texts & test_texts)),
        "invalid_labels": invalid,
    }
    if any(report[key] != len(TOPIC_NAMES) for key in ("train_topics", "val_topics", "test_topics")):
        raise ValueError("训练集、验证集或测试集未覆盖全部物流主题")
    if report["duplicate_texts"] or invalid:
        raise ValueError(f"数据质量检查失败: {report}")
    return report


def main() -> None:
    train, val, test = build()
    report = validate(train, val, test)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("logistics_train.jsonl", train), ("logistics_val.jsonl", val), ("logistics_test.jsonl", test)):
        (OUT / name).write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"物流分类数据生成完成: train={len(train)}, test={len(test)}, topics={len(TOPIC_NAMES)}")


if __name__ == "__main__":
    main()
