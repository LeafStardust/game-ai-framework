from games.balatro.live import joker_sale_fixture


def test_env_r5_joker_sale_fixture_delegates_to_shared_purchase_preserver(monkeypatch):
    captured = {}
    expected = (
        {"event": "observation"},
        {"event": "decision", "data": {"action": {"name": "SELL_JOKER"}}},
        {"event": "action_result"},
    )

    def fake_preserve(source, destination, **kwargs):
        captured.update(
            {
                "source": source,
                "destination": destination,
                **kwargs,
            }
        )
        return expected

    monkeypatch.setattr(
        joker_sale_fixture,
        "preserve_successful_purchase_fixture",
        fake_preserve,
    )

    result = joker_sale_fixture.preserve_successful_joker_sale_fixture(
        "run.jsonl",
        "fixture.jsonl",
        occurrence=2,
        overwrite=True,
    )

    assert result == expected
    assert captured == {
        "source": "run.jsonl",
        "destination": "fixture.jsonl",
        "action_name": joker_sale_fixture.SELL_JOKER,
        "evidence_parser": joker_sale_fixture.successful_joker_sale_evidence_from_run_rows,
        "occurrence": 2,
        "overwrite": True,
    }
