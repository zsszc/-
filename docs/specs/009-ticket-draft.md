# Spec 009：物流异常工单草稿

## 状态

已批准，进入实现阶段。

## 目标

将异常预检结果进一步整理为人工工单草稿，减少客服重复录入，同时保留人工确认边界。

## 接口

`POST /api/logistics/ticket-draft`

请求字段：`description`（1-2000 字符）、可选 `tracking_no`（最多 100 字符）。

响应字段：`ticket_type`、`title`、`description`、`category`、`severity`、`required_materials`、`requires_confirmation`。

## 规则

- 复用 `classify_logistics_exception`，不复制异常分类规则。
- 标题必须包含异常分类；正文保留用户原始描述，并在有运单号时附上运单号。
- `requires_confirmation` 永远为 `true`，本接口不得写入工单数据库。
- 不调用大模型，不上传描述到第三方服务。

## 验收标准

- 清关异常能生成包含分类和材料清单的草稿。
- 有运单号时草稿正文包含该运单号。
- 空描述、超长描述、超长运单号返回 422。
- 接口和工具测试通过，Spec 回填实现记录。

## 实现记录

- 已实现 `app/api/ticket_draft.py`，复用异常分类工具生成草稿，不写入工单表。
- 已覆盖清关草稿、运单号带入和输入校验；相关测试通过。
