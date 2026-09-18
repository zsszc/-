"""比较旧领域样例与物流领域增量样例的轻量主题分类效果。

这是本地数据工程验收，不代表 Transformer 微调；目的是先回答「物流数据是否改善领域分类」。
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core.taxonomy import LEGACY_LABEL_ALIASES, TOPIC_CLASSES

OLD_TRAIN = ROOT / "data/ch10/dataset/train.jsonl"
LOGISTICS = ROOT / "data/evals/logistics_regression.jsonl"
REPORT = ROOT / "data/ch10/reports/logistics_classifier_comparison.json"


def grams(text: str) -> set[str]:
    compact = "".join(ch for ch in text.lower().strip() if not ch.isspace())
    return {compact[i:i + 2] for i in range(max(1, len(compact) - 1))}


def fit(samples: list[tuple[str, str]]) -> list[tuple[set[str], str]]:
    return [(grams(text), label) for text, label in samples]


def predict(model: list[tuple[set[str], str]], text: str) -> str:
    query = grams(text)
    best_score, best_label = -1.0, "其他"
    for sample, label in model:
        score = len(query & sample) / math.sqrt(max(1, len(query) * len(sample)))
        if score > best_score:
            best_score, best_label = score, label
    return best_label


def load_old() -> list[tuple[str, str]]:
    out = []
    for line in OLD_TRAIN.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        label = LEGACY_LABEL_ALIASES.get(item["labels"][0], item["labels"][0])
        out.append((item["text"], label))
    return out


def main() -> None:
    cases = [json.loads(line) for line in LOGISTICS.read_text(encoding="utf-8").splitlines() if line.strip()]
    old = load_old()
    domain_train, holdout = cases[:20], cases[20:]
    logistics_examples = [(example, topic.name) for topic in TOPIC_CLASSES for example in topic.examples]
    baseline = fit(old)
    augmented = fit(old + logistics_examples + [(x["query"], x["topic"]) for x in domain_train])
    rows = []
    for case in holdout:
        before = predict(baseline, case["query"])
        after = predict(augmented, case["query"])
        rows.append({"id": case["id"], "query": case["query"], "gold": case["topic"],
                     "before": before, "after": after})
    before_acc = sum(row["before"] == row["gold"] for row in rows) / len(rows)
    after_acc = sum(row["after"] == row["gold"] for row in rows) / len(rows)
    report = {"method": "character-bigram-exemplar", "baseline_samples": len(old),
              "augmented_samples": len(old) + len(logistics_examples) + len(domain_train),
              "holdout_size": len(rows), "baseline_accuracy": round(before_acc, 4),
              "augmented_accuracy": round(after_acc, 4), "improvement": round(after_acc - before_acc, 4),
              "rows": rows}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"baseline accuracy={before_acc:.4f}; augmented accuracy={after_acc:.4f}; report={REPORT}")


if __name__ == "__main__":
    main()
