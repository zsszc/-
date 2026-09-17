# Spec 006：跨境禁限寄预检

## 状态

已批准，进入实现阶段。

## 目标

为寄件前的物品咨询提供结构化预检结果，帮助用户区分“明确禁寄”和“需要承运商/目的国提前确认”。

## 接口

`POST /api/logistics/prohibited-item-check`

请求：`item_name`，长度 1-200 字符。

响应：`decision`、`reason`、`declaration_hint`。

`decision` 仅允许：`prohibited`、`requires_review`、`可咨询寄运`。

## 约束

- 复用内置工具，不接入外部海关判断服务。
- 明确禁寄与需确认，不把“可能受限”误报成绝对禁寄。
- 不保存物品名称，不替用户完成申报。

## 验收标准

- 易燃物返回 `prohibited`。
- 电池/液体等返回 `requires_review`。
- 普通衣物返回 `可咨询寄运`。
- 空输入和超长输入返回 422。
- 相关测试通过，Spec 回填实现记录。

## 实现记录

- 已实现 `check_prohibited_item` 工具和 `POST /api/logistics/prohibited-item-check` 接口。
- 已覆盖明确禁寄、需提前确认和普通物品三类样例，接口测试通过。
