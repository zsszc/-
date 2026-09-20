from scripts.cost_by_intent import _should_generate_read_note


def test_read_note_requires_five_requests() -> None:
    assert not _should_generate_read_note([])
    assert not _should_generate_read_note([{"count": 1}, {"count": 3}])
    assert _should_generate_read_note([{"count": 2}, {"count": 3}])
