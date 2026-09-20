from app.core.taxonomy import (ID2LABEL, LABEL2ID, NUM_CLASSES, TOPIC_CLASSES,
                               TOPIC_NAMES, terminology_table)


def test_seventeen_unique_classes():
    assert NUM_CLASSES == 17
    assert len(set(TOPIC_NAMES)) == 17


def test_four_leads_first():
    assert TOPIC_NAMES[:4] == ("运单查询", "清关资料", "关税税费", "运输时效")


def test_every_class_has_boundary_examples_severity():
    for c in TOPIC_CLASSES:
        assert c.boundary.strip()
        assert len(c.examples) >= 3 or c.name == "其他"
        assert c.severity in ("严", "中", "宽")


def test_label_id_roundtrip():
    for name in TOPIC_NAMES:
        i = LABEL2ID[name]
        assert ID2LABEL[i] == name
    assert LABEL2ID["运单查询"] == 0 and LABEL2ID["其他"] == 16
    # 旧标签只供历史数据读取；ID 回查应始终返回当前物流类目。
    assert ID2LABEL[LABEL2ID["物流"]] == "运单查询"


def test_terminology_table_covers_all():
    table = terminology_table()
    for name in TOPIC_NAMES:
        assert name in table
