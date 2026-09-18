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
- 已准备独立原生 arm64 `.venv-m4-arm`，安装 PyTorch、Transformers、Accelerate、Scikit-learn 和 NumPy；原有 x86 `.venv` 保持不动。
- 已完成 2 轮 CPU 烟测，验证集阈值扫描 micro-F1 为 0.8690，独立 57 条测试集 micro-F1 为 0.2087；该结果暴露出合成训练语句与测试语句分布仍有差异，不能直接作为最终模型成绩。
- 模型权重保留在本地忽略目录，未上传 Git；评测报告已保存到 `data/ch10/reports/logistics-smoke/`。
