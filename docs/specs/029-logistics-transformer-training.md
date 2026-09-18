# Spec 029：物流主题 Transformer 训练入口

## 状态

已批准，进入实现阶段。

## 目标

让现有分类器训练脚本可以直接切换到新增的物流训练、验证和测试数据，为后续在具备 PyTorch/Transformers 与模型缓存的环境中正式微调做准备。

## 范围

- 为 `scripts/ch10/train.py` 增加数据目录和模型输出目录参数。
- 为 `scripts/ch10/evaluate.py` 增加模型目录、测试集和报告目录参数。
- 默认行为保持兼容，仍使用原有 `data/ch10/dataset` 和 `data/ch10/model`。
- 物流训练命令使用 `logistics_train.jsonl`、`logistics_val.jsonl`，输出到独立模型目录。
- 不在当前无 PyTorch/Transformers 环境中伪造训练指标。

## 验收标准

- 训练脚本支持 `--data-dir` 和 `--output-dir`。
- 物流数据字段可被现有编码逻辑读取，17 个 canonical 标签可映射到分类头。
- 默认旧训练命令的路径和行为不被破坏。
- 数据生成与训练入口的静态检查通过，并明确记录当前运行环境限制。

## 实现记录

- 已为训练脚本增加 `--data-dir` 和 `--output-dir`，并自动识别 `logistics_train.jsonl` / `logistics_val.jsonl`；默认旧数据路径保持兼容。
- 数据生成、训练/评测入口静态检查通过；当前环境缺少 `torch` 和 `transformers`，因此未伪造正式 Transformer 训练指标，待具备训练依赖后执行微调。
