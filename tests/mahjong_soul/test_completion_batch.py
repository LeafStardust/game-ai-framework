"""Batch diagnostics must reproduce the baseline and match a public target."""
import json
import pytest
from agents.mahjong_soul import completion_batch as batch


def test_existing_output_is_preserved(tmp_path):
    output = tmp_path/'report.json'; output.write_text('original')
    with pytest.raises(ValueError, match='already exists'):
        batch.evaluate(tmp_path, output)
    assert output.read_text() == 'original'


def setup_match(monkeypatch, tmp_path, events, traced):
    replay = tmp_path/'baseline.json'; replay.write_text(json.dumps({'events': events}))
    match = {'profile': 'callers', 'split': 'development', 'seed': 1, 'seat': 0,
             'replay': str(replay), 'targets': [{'hand_index': 0, 'called_tile': '3p',
                                               'combination': ['3p','3p']}]}
    monkeypatch.setattr(batch, 'manifest', lambda *a: {'eligible_calls': 1, 'matches': [match]})
    monkeypatch.setattr(batch, 'capture_calls', lambda *a, **kw: ({'log': []}, traced))
    return tmp_path/'result.json'


def test_changed_baseline_rejected(monkeypatch, tmp_path):
    output = setup_match(monkeypatch, tmp_path, [{'type': 'changed'}], [])
    with pytest.raises(ValueError, match='Baseline replay changed'):
        batch.evaluate(tmp_path, output)
    assert not output.exists()


def test_missing_public_target_rejected(monkeypatch, tmp_path):
    output = setup_match(monkeypatch, tmp_path, [], [])
    with pytest.raises(ValueError, match='exactly one target'):
        batch.evaluate(tmp_path, output)
    assert not output.exists()
