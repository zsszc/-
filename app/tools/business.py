"""mock 数据源(纯函数,随机种子固定 → 同键稳定)。
ch08 起工具实现迁至 app/tools/builtin/(注册即定义),本模块只留被 graph 节点
(fetch_order)与 builtin 工具共用的快照函数,不再定义任何 @tool。"""
import random


def order_snapshot(order_id: str) -> dict:
    """订单快照(纯函数,随机种子固定 → 同 order_id 稳定)。query_order 工具与 fetch_order 节点同源。"""
    rng = random.Random(f"order:{order_id}")
    return {
        "order_id": order_id,
        "status": rng.choice(["待付款", "已付款", "已发货", "已签收"]),
        "amount": rng.randint(50, 2000),
        "created_at": f"2026-07-{rng.randint(1, 12):02d} 10:00",
        "product": rng.choice(["智能猫砂盆", "猫粮 5kg", "猫爬架", "自动饮水机"]),
        "tracking_no": f"SF{rng.randint(10**11, 10**12 - 1)}",
    }


def owns_order(user_id: str, order_id: str) -> bool:
    """这一单是不是这个人的。归属判断只有这一处,工具和节点都调它,不各判各的。

    空 user_id 一律不放行:身份是注入进来的,注入没接上就是空串,那种情况下放行等于没做校验。"""
    if not user_id or not order_id:
        return False
    return any(o["order_id"] == order_id for o in list_user_orders(user_id))


# 课程演示单。文档、curl 例子、各章验收脚本里到处写着 1001 和 2002,让每个账号名下都有
# 这两笔,例子拿来即跑。想看归属校验拦人,随便报一个别的号(如 9999)就会被挡下。
DEMO_ORDER_IDS = ("1001", "2002")


def list_user_orders(user_id: str) -> list[dict]:
    """按 user_id 稳定列出该用户的订单(mock,不落库):两笔演示单 + 2-4 笔随机单。
    每笔用 order_snapshot 同源,前端选中后回填 order_id 即可 query_order。"""
    rng = random.Random(f"user_orders:{user_id}")
    ids = list(DEMO_ORDER_IDS)
    for _ in range(rng.randint(2, 4)):
        oid = str(rng.randint(1000, 9999))
        if oid not in ids:
            ids.append(oid)
    out = []
    for oid in ids:
        s = order_snapshot(oid)
        out.append({"order_id": oid, "product": s["product"],
                    "status": s["status"], "amount": s["amount"]})
    return out


DEMO_TRACKING_NOS = ("CNDE20260917001", "CNUS20260917002")


def shipment_snapshot(tracking_no: str) -> dict:
    """跨境运单 mock 快照：同一运单号每次返回稳定结果。"""
    rng = random.Random(f"shipment:{tracking_no}")
    status = rng.choice(["已揽收", "运输中", "清关中", "派送中", "已签收"])
    city = rng.choice(["深圳", "广州", "法兰克福", "洛杉矶", "东京"])
    return {
        "tracking_no": tracking_no,
        "status": status,
        "current_node": city,
        "carrier": rng.choice(["DHL", "FedEx", "UPS", "顺丰国际"]),
        "last_update": "2026-09-17 10:30",
        "estimated_delivery": f"2026-09-{rng.randint(20, 28):02d}",
        "trace": [f"{city}处理中心：{status}", "等待下一运输节点更新"],
    }


def list_user_shipments(user_id: str) -> list[dict]:
    """按用户稳定生成演示运单列表，供前端和 Agent 演示。"""
    if not user_id:
        return []
    return [shipment_snapshot(no) for no in DEMO_TRACKING_NOS]


def owns_shipment(user_id: str, tracking_no: str) -> bool:
    return bool(user_id and tracking_no and any(
        item["tracking_no"] == tracking_no for item in list_user_shipments(user_id)))
