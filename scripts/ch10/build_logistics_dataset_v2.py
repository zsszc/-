"""构建更接近客服口语、包含相邻主题样本的物流分类训练集 v2。"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core.taxonomy import TOPIC_NAMES

REGRESSION = ROOT / "data/evals/logistics_regression.jsonl"
OUT = ROOT / "data/ch10/dataset/logistics_train_v2.jsonl"
REPORT = ROOT / "data/ch10/reports/logistics_dataset_v2_report.json"

SEEDS = {
    "运单查询": ("帮我查一下国际件到哪了", "这票货现在到哪个节点", "运单轨迹怎么一直没看到", "我想知道包裹当前在哪里"),
    "清关资料": ("德国清关要补哪些文件", "海关查验需要准备什么", "我的货卡在清关资料这一步了", "清关通知里的补料怎么弄"),
    "关税税费": ("进口税到底谁来付", "目的国税费怎么估算", "申报价值会影响关税吗", "收到包裹还要另外交税吗"),
    "运输时效": ("从中国寄过去通常几天到", "这条线路的承诺时效是多少", "国际干线大概还要飞多久", "怎么判断会不会超过时效"),
    "运输费用": ("这个包裹运费怎么算出来的", "燃油附加费为什么也要收", "体积重比实际重量大怎么办", "能不能给我一个大概报价"),
    "异常处理": ("物流三天没动是不是异常了", "状态一直不更新该怎么办", "这票货看起来像运输延误", "遇到物流异常我先做什么"),
    "派送问题": ("快递员联系不上我怎么办", "派送失败后还会再送吗", "我不在家可以改派送时间吗", "末端派送一直失败怎么处理"),
    "地址修改": ("收件电话填错了能改吗", "货已经发出还能改地址吗", "我要修改收件人信息", "地址写错会不会导致退回"),
    "禁限寄": ("充电电池可以走国际快递吗", "液体寄国外有什么限制", "哪些东西属于明确禁寄", "粉末类物品需要怎么申报"),
    "包裹破损": ("收到时外箱已经压坏了", "里面少了一件应该怎么拍照", "签收后发现商品碎了能赔吗", "包裹破损要留哪些证据"),
    "丢失理赔": ("国际件确认丢了以后怎么赔", "包裹一直找不到可以申请理赔吗", "丢件需要提供什么价值证明", "承运商认定丢失后多久赔付"),
    "退运处理": ("清关失败被退回怎么办", "拒收以后退运费用怎么算", "货退回始发地还要重新申报吗", "退运流程一般要几天"),
    "承运商服务": ("DHL和UPS的服务差异是什么", "哪家承运商的轨迹更新更快", "这条线路可以换承运商吗", "承运商选择会影响清关吗"),
    "贸易单证": ("商业发票怎么填写", "装箱单和发票有什么区别", "寄件需要提供进口资质吗", "贸易单证缺失会有什么影响"),
    "线路选择": ("去德国走经济还是特快", "不同运输方式怎么选", "有没有更稳妥的欧洲线路", "我比较在意价格应该选哪条线路"),
    "账户权限": ("客服账号能看到哪些运单", "我登录后为什么没有查询权限", "怎么给同事开管理员权限", "账号安全信息在哪里修改"),
    "其他": ("我想找人工客服帮忙", "这个问题不在页面说明里", "可以先帮我记录一下吗", "我不知道应该选择哪个服务"),
}
OPENERS = ("", "麻烦你帮我看看，", "客服你好，", "我现在遇到这个情况：")
TAILS = ("，能说得具体一点吗？", "，我需要下一步的处理建议。", "，如果缺资料请直接列出来。", "，不要只给一个结论。")


def load_regression() -> list[dict]:
    return [json.loads(line) for line in REGRESSION.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    rows = []
    for label, seeds in SEEDS.items():
        for seed_index, seed in enumerate(seeds):
            for variant, (opener, tail) in enumerate(zip(OPENERS, TAILS)):
                text = f"{opener}{seed}{tail}"
                rows.append({"id": f"v2-{len(rows)+1:03d}", "text": text,
                             "labels": [label], "source": "natural_hard_negative"})
    for index, item in enumerate(load_regression()[:28]):
        rows.append({"id": f"v2-reg-{index+1:03d}",
                     "text": f"我作为客户现在的实际问题是：{item['query']}，请按物流客服流程处理。",
                     "labels": [item["topic"]], "source": "regression_variant"})
    if len(rows) != 300:
        raise ValueError(f"v2 数据量应为 300，实际 {len(rows)}")
    if len({row["text"] for row in rows}) != len(rows):
        raise ValueError("v2 存在重复文本")
    if {row["labels"][0] for row in rows} != set(TOPIC_NAMES):
        raise ValueError("v2 未覆盖全部主题")
    OUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps({"total": len(rows), "topic_counts": dict(Counter(row["labels"][0] for row in rows)),
                                  "source_counts": dict(Counter(row["source"] for row in rows)),
                                  "template_variants": len(OPENERS)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"v2 训练集生成完成: total={len(rows)}, topics={len(TOPIC_NAMES)}")


if __name__ == "__main__":
    main()
