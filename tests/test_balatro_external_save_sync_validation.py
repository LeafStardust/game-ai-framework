from games.balatro.live.external.save_sync_validation import (
    changed_fields,
    state_summary,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def test_state_summary_reports_translated_save_snapshot():
    snapshot = LiveBalatroSnapshot(
        sequence=3,
        phase="SELECTING_HAND",
        state_complete=False,
        payload={
            "save_state": 1,
            "save_sha256": "1234567890abcdef",
            "money": 6,
            "ante_num": 1,
            "round_num": 2,
            "score": 195,
            "round": {
                "chips": 450,
                "hands_left": 2,
                "discards_left": 1,
            },
            "blind": {
                "type": "BIG",
                "status": "CURRENT",
                "name": "Big Blind",
                "score": 450,
            },
            "hand": {
                "limit": 8,
                "cards": [
                    {
                        "value": {"rank": "A", "suit": "S"},
                        "modifier": {},
                    }
                ],
            },
        },
    )

    summary = state_summary(snapshot)

    assert summary["sequence"] == 3
    assert summary["hash"] == "1234567890ab"
    assert summary["phase"] == "SELECTING_HAND"
    assert summary["money"] == 6
    assert summary["score"] == 195
    assert summary["blind"] == "Big Blind"
    assert summary["blind_target"] == 450
    assert summary["hands"] == 2
    assert summary["discards"] == 1
    assert summary["hand"] == ["A Spades"]


def test_changed_fields_ignores_sequence_and_hash_metadata():
    before = {
        "sequence": 1,
        "hash": "old",
        "score": 0,
        "hands": 4,
        "hand": ["A Spades"],
    }
    after = {
        "sequence": 2,
        "hash": "new",
        "score": 220,
        "hands": 3,
        "hand": ["K Hearts"],
    }

    assert changed_fields(before, after) == ["score", "hands", "hand"]
