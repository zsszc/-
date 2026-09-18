from pathlib import Path


def test_training_entrypoint_documents_logistics_data_switch():
    source = Path("scripts/ch10/train.py").read_text(encoding="utf-8")
    assert "--data-dir" in source
    assert "--output-dir" in source
    assert "logistics_train.jsonl" in source
    assert "logistics_val.jsonl" in source
