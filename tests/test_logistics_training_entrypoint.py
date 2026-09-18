from pathlib import Path


def test_training_entrypoint_documents_logistics_data_switch():
    source = Path("scripts/ch10/train.py").read_text(encoding="utf-8")
    assert "--data-dir" in source
    assert "--output-dir" in source
    assert "logistics_train.jsonl" in source
    assert "logistics_val.jsonl" in source
    assert "--epochs" in source
    assert "--batch-size" in source
    assert "--train-file" in source
    assert "--val-file" in source


def test_evaluation_entrypoint_supports_logistics_artifacts():
    source = Path("scripts/ch10/evaluate.py").read_text(encoding="utf-8")
    assert "--model-dir" in source
    assert "--test" in source
    assert "--reports-dir" in source
