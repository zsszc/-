"""生成按任务类型分层的 300 条物流 Agent 综合评估集。"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core.taxonomy import TOPIC_NAMES

OUT = ROOT / "data/evals/logistics_agent_eval.jsonl"
REPORT = ROOT / "data/evals/logistics_agent_eval_report.json"

POLICY = [
    ("德国清关需要准备哪些资料", "清关资料"), ("包裹破损怎么申请理赔", "包裹破损"),
    ("锂电池可以寄到美国吗", "禁限寄"), ("国际件一般多久能到", "运输时效"),
    ("体积重和实际重量怎么计费", "运输费用"), ("派送失败后怎么重新安排", "派送问题"),
    ("收件电话写错了能修改吗", "地址修改"), ("进口税一般由谁承担", "关税税费"),
    ("商业发票应该填写哪些内容", "贸易单证"), ("包裹清关失败会怎么处理", "退运处理"),
    ("DHL 和 UPS 有什么服务区别", "承运商服务"), ("怎么选择经济还是特快线路", "线路选择"),
    ("国际包裹丢失如何索赔", "丢失理赔"), ("运单查询需要提供什么", "运单查询"),
    ("物流状态长时间不更新怎么办", "异常处理"), ("登录后能查看哪些运单", "账户权限"),
    ("客服电话什么时候可以转人工", "其他"), ("清关补料一般有哪些步骤", "清关资料"),
    ("目的国禁限寄规则在哪里确认", "禁限寄"), ("偏远地区附加费怎么计算", "运输费用"),
]
CROSS = [
    ("从深圳寄德国，2kg标准运费加上申报价值1000元的税费大约多少", "运输费用", ["estimate_shipping_fee"]),
    ("包裹在德国清关且已经超过SLA，应该准备什么资料并怎么升级", "清关资料", ["query_shipment", "assess_shipment_sla"]),
    ("包裹破损又少件，理赔需要哪些照片和签收材料", "包裹破损", ["classify_logistics_exception", "ticket_draft"]),
    ("锂电池走特快到美国，费用和禁寄风险分别是什么", "禁限寄", ["check_prohibited_item", "estimate_shipping_fee"]),
    ("运单显示派送失败，能否改地址以及是否会产生费用", "地址修改", ["query_shipment", "estimate_shipping_fee"]),
    ("清关失败被退运，退运费用由谁承担，下一步如何申请", "退运处理", ["query_shipment", "classify_logistics_exception"]),
    ("DHL和UPS哪个更适合有SLA要求的德国线路", "承运商服务", ["assess_shipment_sla", "estimate_shipping_fee"]),
    ("目的国税费和燃油附加费是否都包含在报价里", "关税税费", ["estimate_shipping_fee"]),
    ("丢失理赔时，运单状态和商品价值证明是否都要提供", "丢失理赔", ["query_shipment", "ticket_draft"]),
    ("国际件三天没有更新，应该先查件还是直接提交异常工单", "异常处理", ["query_shipment", "classify_logistics_exception"]),
    ("商业发票缺失导致清关卡住，补料和工单怎么准备", "贸易单证", ["classify_logistics_exception", "ticket_draft"]),
    ("想把经济线路改成特快，预计时效和价格怎么变化", "线路选择", ["estimate_shipping_fee"]),
    ("派送失败且收件电话错误，改联系方式后还需要人工介入吗", "派送问题", ["classify_logistics_exception", "ticket_draft"]),
    ("签收后发现外箱破损，理赔时效和证据要求是什么", "包裹破损", ["ticket_draft"]),
]
TOOLS = [
    ("查询运单 CNDE20260917001 到哪了", "运单查询", ["query_shipment"]),
    ("判断 CNUS20260917002 是否接近SLA", "运输时效", ["query_shipment", "assess_shipment_sla"]),
    ("估算深圳到德国2kg标准运费", "运输费用", ["estimate_shipping_fee"]),
    ("估算中国到美国0.8kg特快运费", "运输费用", ["estimate_shipping_fee"]),
    ("锂电池可以寄到美国吗", "禁限寄", ["check_prohibited_item"]),
    ("汽油能不能走国际快递", "禁限寄", ["check_prohibited_item"]),
    ("包裹三天没更新，帮我归类异常", "异常处理", ["classify_logistics_exception"]),
    ("德国清关要求补资料，帮我生成工单草稿", "清关资料", ["classify_logistics_exception", "ticket_draft"]),
    ("包裹破损需要人工处理，创建工单草稿", "包裹破损", ["ticket_draft"]),
    ("查询这票货的当前节点和承运商", "运单查询", ["query_shipment"]),
    ("判断国际件是否会超过标准时效", "运输时效", ["assess_shipment_sla"]),
    ("粉末类物品能否寄运", "禁限寄", ["check_prohibited_item"]),
]
OUT_OF_SCOPE = [
    ("明天深圳飞法兰克福的航班是否会取消", "其他", "不掌握实时航班信息"),
    ("DHL今天德国线路的内部爆仓阈值是多少", "承运商服务", "未收录承运商内部规则"),
    ("我的包裹在海关会被收多少欧元税", "关税税费", "缺少实时税则和完整商品信息"),
    ("UPS今年最新的内部附加费表是什么", "运输费用", "需要实时价目表"),
    ("德国海关今天是否临时增加查验比例", "清关资料", "需要实时海关公告"),
    ("我的包裹具体会由哪位快递员几点送达", "派送问题", "不掌握末端实时排班"),
    ("某个没有提供名称的仓库能否代收包裹", "其他", "缺少仓库身份和协议"),
    ("巴西最新进口许可证要求是什么", "贸易单证", "超出当前国家和政策范围"),
    ("这票货现在在机场哪个摄像头画面里", "运单查询", "无法访问实时监控"),
    ("帮我预测下个月欧洲汇率和运费走势", "运输费用", "不提供金融和市场预测"),
]
BOUNDARY = [
    ("帮我查一下我的包裹", "运单查询", ["缺少运单号"]),
    ("帮我算一下国际运费", "运输费用", ["缺少始发地、目的地和重量"]),
    ("这个东西能不能寄", "禁限寄", ["缺少物品名称和目的地"]),
    ("税费大概多少钱", "关税税费", ["缺少目的地和申报价值"]),
]


def add(rows: list[dict], category: str, query: str, topic: str, tools=None,
        must_abstain=False, requires_citations=True, note="") -> None:
    rows.append({"id": f"agent-{len(rows)+1:03d}", "category": category, "query": query,
                 "gold_topic": topic, "expected_tools": tools or [], "must_abstain": must_abstain,
                 "requires_citations": requires_citations, "note": note})


def build() -> list[dict]:
    rows: list[dict] = []
    for query, topic in POLICY:
        for suffix in ("请按步骤说明。", "客服回答时要给出资料清单。", "如果条件不足请明确说明。", "请引用相关知识依据。", "我想知道下一步怎么做。"):
            add(rows, "policy_process", f"{query}，{suffix}", topic)
    for query, topic, tools in CROSS:
        for suffix in ("请综合判断，不要只回答其中一半。", "请列出依据和下一步。", "如果不能确定请说明缺口。", "请给客服一个可执行方案。", "请区分政策和实时状态。"):
            add(rows, "cross_document", f"{query}。{suffix}", topic, tools)
    for query, topic, tools in TOOLS:
        for suffix in ("请直接调用合适工具。", "返回结果后请用客服能看懂的话解释。", "不要凭空猜测具体状态。", "如果缺参数先追问。", "请保留必要的结构化结果。"):
            add(rows, "tool_operation", f"{query}，{suffix}", topic, tools)
    for query, topic, reason in OUT_OF_SCOPE:
        for suffix in ("请不要编造答案。", "如果知识库没有依据请拒答并转人工。", "请说明为什么无法确认。", "只能给出安全的下一步建议。", "不要把估算说成事实。"):
            add(rows, "out_of_scope", f"{query}。{suffix}", topic, must_abstain=True,
                requires_citations=False, note=reason)
    for query, topic, missing in BOUNDARY:
        for suffix in ("请先补齐必要信息。", "不要直接给出不可靠结论。", "请告诉我还需要什么。", "客服应该先澄清哪些字段？", "缺少信息时走什么流程？"):
            add(rows, "boundary_clarification", f"{query}。{suffix}", topic, note="；".join(missing))
    return rows


def main() -> None:
    rows = build()
    counts = Counter(row["category"] for row in rows)
    if len(rows) != 300 or counts != Counter({"policy_process": 100, "cross_document": 70,
                                               "tool_operation": 60, "out_of_scope": 50,
                                               "boundary_clarification": 20}):
        raise ValueError(f"评估集分层数量不符合预期: {counts}")
    if len({row["query"] for row in rows}) != len(rows):
        raise ValueError("评估集存在重复问题")
    if any(row["gold_topic"] not in TOPIC_NAMES for row in rows):
        raise ValueError("评估集存在非法主题")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    report = {"total": len(rows), "category_counts": dict(counts),
              "must_abstain": sum(row["must_abstain"] for row in rows),
              "citation_cases": sum(row["requires_citations"] for row in rows),
              "topic_counts": dict(Counter(row["gold_topic"] for row in rows))}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Agent评估集生成完成: total={len(rows)}, categories={dict(counts)}")


if __name__ == "__main__":
    main()
