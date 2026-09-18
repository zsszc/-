# 物流分类器训练说明

## 环境

项目运行环境继续使用 `.venv`。分类器训练使用原生 arm64 环境 `.venv-m4-arm`，避免 M4 机器误用 x86_64 Python。

```bash
./.venv-m4-arm/bin/python -c 'import platform, torch; print(platform.machine(), torch.__version__, torch.backends.mps.is_available())'
```

如果 `torch.backends.mps.is_available()` 为 `True`，训练会使用 MPS；否则会退回 CPU。

## 训练

先运行 2 轮烟测：

```bash
HF_HOME=.cache/huggingface ./.venv-m4-arm/bin/python scripts/ch10/train.py \
  --data-dir data/ch10/dataset \
  --output-dir data/ch10/model-logistics-smoke \
  --epochs 2 --batch-size 32 --max-length 96
```

确认流程后再增加轮数：

```bash
HF_HOME=.cache/huggingface ./.venv-m4-arm/bin/python scripts/ch10/train.py \
  --data-dir data/ch10/dataset \
  --output-dir data/ch10/model-logistics \
  --epochs 6 --batch-size 16 --max-length 128
```

## 评测

```bash
PYTHONPATH=. ./.venv-m4-arm/bin/python scripts/ch10/evaluate.py \
  --model-dir data/ch10/model-logistics \
  --test data/ch10/dataset/logistics_test.jsonl \
  --reports-dir data/ch10/reports/logistics
```

物流主题数据是单标签任务，训练脚本会自动切换到 softmax/argmax；旧的多标签数据仍使用 sigmoid/阈值模式。当前单标签模型在 170 条均衡测试集上达到 micro-F1 0.8471、macro-F1 0.8520。
