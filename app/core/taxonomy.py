"""跨境物流权威归并术语表:全系统唯一一份,17 类主题类目。
数据处理、预标、训练、推理、评测、前端全部 import 这里,不许各自抄一份。
类目名与边界说明集中维护;元组顺序即 label id,训练与推理共用。
severity 是容错档位:归错会带偏补知识优先级的类目从严。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class TopicClass:
    name: str
    boundary: str                 # 一句边界说明:什么算这一类,近邻类目靠它划开
    examples: tuple[str, ...]     # 用户的说法示例
    severity: str                 # 容错档位:严 / 中 / 宽


TOPIC_CLASSES: tuple[TopicClass, ...] = (
    TopicClass("运单查询", "查询国际包裹当前状态、节点和轨迹",
               ("到哪了", "查运单", "物流不动", "轨迹更新"), "严"),
    TopicClass("清关资料", "清关所需资料、查验和补料流程",
               ("清关资料", "海关查验", "补文件", "清关卡住"), "严"),
    TopicClass("关税税费", "进口税、关税、税费承担和申报价值",
               ("关税怎么算", "进口税谁付", "税费预付"), "严"),
    TopicClass("运输时效", "线路运输时长和延误时效说明",
               ("多久到", "运输几天", "航班延误"), "严"),
    TopicClass("运输费用", "计费重量、报价和附加费用",
               ("运费怎么算", "体积重", "燃油附加费"), "中"),
    TopicClass("异常处理", "物流异常识别和处理步骤",
               ("物流异常", "运输延误", "状态不对"), "严"),
    TopicClass("派送问题", "派送失败、联系不上和重新派送",
               ("派送失败", "没人收件", "联系不上"), "中"),
    TopicClass("地址修改", "运输中修改收件地址或联系方式",
               ("改地址", "电话写错", "收件信息"), "中"),
    TopicClass("禁限寄", "禁寄物品、线路限制和申报要求",
               ("能寄电池吗", "液体能寄吗", "禁运品"), "严"),
    TopicClass("包裹破损", "包裹破损、少件和签收异常",
               ("外箱破了", "少了东西", "破损理赔"), "严"),
    TopicClass("丢失理赔", "包裹丢失认定和赔偿材料",
               ("包裹丢了", "怎么理赔", "赔偿材料"), "严"),
    TopicClass("退运处理", "清关失败、拒收和退回始发地",
               ("退回去了", "拒收", "退运费用"), "中"),
    TopicClass("承运商服务", "承运商选择、服务范围和轨迹差异",
               ("DHL", "FedEx", "哪家快"), "中"),
    TopicClass("贸易单证", "商业发票、装箱单和贸易文件",
               ("商业发票", "装箱单", "进口资质"), "中"),
    TopicClass("线路选择", "目的国、运输方式和线路方案比较",
               ("发德国走哪条", "经济还是特快", "线路推荐"), "中"),
    TopicClass("账户权限", "登录、账号安全和客户权限",
               ("登录不上", "账号安全", "权限"), "宽"),
    TopicClass("其他", "上面都对不上的问题,先兜底",
               ("闲聊", "转人工", "客服"), "宽"),
)

TOPIC_NAMES: tuple[str, ...] = tuple(c.name for c in TOPIC_CLASSES)
LABEL2ID: dict[str, int] = {name: i for i, name in enumerate(TOPIC_NAMES)}
# 旧数据集仍可被离线切分/读取，但新生成与展示只使用上面的物流术语。
LEGACY_LABEL_ALIASES = {
    "物流": "运单查询", "运费": "运输费用", "订单修改": "地址修改",
    "发票": "贸易单证", "质量问题": "包裹破损", "售后": "异常处理",
    "退换货": "退运处理", "商品信息": "线路选择", "尺码": "线路选择",
    "优惠活动": "运输费用", "价保": "运输费用", "支付": "运输费用",
    "库存补货": "线路选择", "保修维修": "异常处理", "账号": "账户权限",
    "会员积分": "账户权限", "评价": "其他",
}
LABEL2ID.update({legacy: LABEL2ID[current] for legacy, current in LEGACY_LABEL_ALIASES.items()})
ID2LABEL: dict[int, str] = {i: name for i, name in enumerate(TOPIC_NAMES)}
NUM_CLASSES = len(TOPIC_CLASSES)
SEVERITY: dict[str, str] = {c.name: c.severity for c in TOPIC_CLASSES}


def terminology_table() -> str:
    """预标/造数 prompt 用的术语表文本:类目:边界说明(示例)。"""
    return "\n".join(
        f"- {c.name}:{c.boundary}(示例:{'、'.join(c.examples)})" for c in TOPIC_CLASSES
    )
