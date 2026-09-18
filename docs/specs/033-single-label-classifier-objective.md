# Spec 033：物流单标签分类目标修正

## 状态

已批准，进入实现阶段。

## 目标

修正物流主题分类器沿用多标签训练目标的问题。物流分类数据每条只有一个主题，应使用 softmax/argmax；原有多标签数据继续保留 BCE/sigmoid 兼容模式。

## 范围

- 自动识别训练集是否为单标签数据。
- 单标签使用 `single_label_classification`、整数标签和 argmax 预测。
- 多标签继续使用原有向量标签、sigmoid 和阈值扫描。
- 评测报告标记分类模式，避免混淆阈值和 argmax 结果。

## 验收标准

- 物流单标签数据不再走多标签 BCE 目标。
- 旧多标签数据入口保持兼容。
- 单标签训练/评测结果包含 `classification_mode=single_label`。
- 相关静态测试和一次单标签训练评估通过。

## 实现记录

- 已自动识别单标签物流数据并切换到 `single_label_classification` + argmax；旧多标签数据仍保持兼容。
- 单标签模型验证集 micro-F1 0.9020，独立测试集 micro-F1 0.8471；评测报告已保存到 `data/ch10/reports/logistics-singlelabel/`。
