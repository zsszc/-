"""生成均衡、单主题的物流分类验证/测试基准。"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core.taxonomy import TOPIC_CLASSES, TOPIC_NAMES
from scripts.ch10.build_logistics_dataset_v2 import SEEDS

OUT = ROOT / "data/ch10/dataset"
REPORT = ROOT / "data/ch10/reports/logistics_classifier_benchmark_report.json"


def main() -> None:
    val, test = [], []
    for index, topic in enumerate(TOPIC_CLASSES):
        seeds = SEEDS[topic.name]
        val_templates = (
            f"我只想咨询一个问题：{seeds[0]}。",
            f"客服您好，我目前只遇到{seeds[1]}这个问题。",
            f"请单独说明{seeds[2]}应该怎么处理。",
        )
        test_templates = (
            f"想确认一下，{seeds[0]}。",
            f"这票国际件的情况是：{seeds[1]}。",
            f"麻烦解释下{seeds[2]}。",
            f"我最关心的是{seeds[3]}。",
            f"如果只看这个问题，{seeds[0]}怎么办？",
            f"客户问：{seeds[1]}，客服应该怎么答？",
            f"请判断单一主题：{seeds[2]}。",
            f"不用展开其他问题，我想知道{seeds[3]}。",
            f"这不是报价问题，我要咨询的是{seeds[0]}。",
            f"请给出关于{seeds[1]}的标准答复。",
        )
        for suffix, text in enumerate(val_templates):
            val.append({"id": f"cls-val-{index:02d}-{suffix}", "text": text,
                        "labels": [topic.name], "source": "single_topic_validation"})
        for suffix, text in enumerate(test_templates):
            test.append({"id": f"cls-test-{index:02d}-{suffix}", "text": text,
                         "labels": [topic.name], "source": "single_topic_test"})
    train_path = OUT / "logistics_train_v2.jsonl"
    train_texts = {json.loads(line)["text"] for line in train_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    all_rows = val + test
    if len(val) != 51 or len(test) != 170:
        raise ValueError("分类基准数量不符合预期")
    if len({row["text"] for row in all_rows}) != len(all_rows) or train_texts & {row["text"] for row in all_rows}:
        raise ValueError("分类基准存在重复文本")
    if any(row["labels"][0] not in TOPIC_NAMES for row in all_rows):
        raise ValueError("分类基准存在非法主题")
    for name, rows in (("logistics_val_v2.jsonl", val), ("logistics_test_v2.jsonl", test)):
        (OUT / name).write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    report = {"val_size": len(val), "test_size": len(test),
              "val_topic_counts": dict(Counter(row["labels"][0] for row in val)),
              "test_topic_counts": dict(Counter(row["labels"][0] for row in test)),
              "cross_topic_cases_kept_in": "data/evals/logistics_agent_eval.jsonl"}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"单主题分类基准生成完成: val={len(val)}, test={len(test)}, topics={len(TOPIC_NAMES)}")


if __name__ == "__main__":
    main()
