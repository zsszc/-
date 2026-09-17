# Spec 007：物流场景回归评测集

## 状态

已批准，进入实现阶段。

## 目标

建立与本项目业务一致的最小回归集，验证领域标签、工具路由和知识覆盖不会在后续二开中退化。

## 数据契约

每行 JSONL 必须包含：`id`、`query`、`intent`、`topic`、`expected_capability`。

- `intent` 使用聊天流程的 9 类意图。
- `topic` 使用后台 17 类物流主题。
- `expected_capability` 仅允许：`rag`、`shipment_query`、`shipping_fee`、`exception_classify`、`prohibited_check`。

## 范围约束

- 本轮只做数据契约和静态回归校验，不调用大模型、不产生费用。
- 样例使用虚构运单号和通用描述，不包含真实个人信息。
- 后续可在此基础上增加离线检索命中率和工具选择准确率评测。

## 验收标准

- 至少覆盖 6 类业务能力。
- 所有 intent/topic/capability 均属于权威枚举。
- ID 唯一，JSONL 每行可独立解析。
- 自动化校验通过，并在本记录中回填结果。

## 实现记录

- 待实现
