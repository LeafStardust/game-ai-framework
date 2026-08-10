from pathlib import Path

from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.live.external.save_observer import (
    SaveBalatroObserver,
    snapshot_from_save,
)
from games.balatro.live.external.save_state import BalatroSaveSnapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _save_snapshot(*, sha256="abc", state_id=1):
    data = {
        "STATE": state_id,
        "VERSION": "1.0.1o-FULL",
        "BACK": {
            "name": "Red Deck",
            "key": "b_red",
        },
        "BLIND": {
            "name": "Small Blind",
            "chips": 300,
            "config_blind": "bl_small",
            "boss": False,
        },
        "GAME": {
            "dollars": 4,
            "chips": 220,
            "round": 1,
            "stake": 1,
            "facing_blind": True,
            "blind_on_deck": "Small",
            "won": False,
            "pseudorandom": {
                "seed": "HIDDEN",
            },
            "round_resets": {
                "ante": 1,
            },
            "current_round": {
                "hands_left": 3,
                "discards_left": 2,
            },
            "hands": {
                "Pair": {"level": 2},
            },
        },
        "cardAreas": {
            "hand": {
                "cards": [
                    {
                        "playing_card": 9,
                        "base": {
                            "value": "Ace",
                            "suit": "Clubs",
                        },
                        "save_fields": {
                            "card": "C_A",
                            "center": "c_base",
                        },
                    },
                    {
                        "playing_card": 51,
                        "base": {
                            "value": "Queen",
                            "suit": "Spades",
                        },
                        "save_fields": {
                            "card": "S_Q",
                            "center": "m_steel",
                        },
                        "edition": {"foil": True},
                        "seal": "Red",
                    },
                ],
                "config": {
                    "card_count": 2,
                    "card_limit": 8,
                },
            },
            "deck": {
                "cards": [
                    {
                        "playing_card": 19,
                        "base": {
                            "value": "7",
                            "suit": "Diamonds",
                        },
                        "save_fields": {
                            "card": "D_7",
                            "center": "c_base",
                        },
                    }
                ],
                "config": {
                    "card_count": 1,
                    "card_limit": 52,
                },
            },
            "jokers": {
                "cards": {
                    1: {
                        "sort_id": 640,
                        "label": "Acrobat",
                        "cost": 6,
                        "sell_cost": 3,
                        "debuff": False,
                        "save_fields": {
                            "center": "j_acrobat",
                        },
                        "ability": {
                            "name": "Acrobat",
                            "set": "Joker",
                        },
                    }
                },
                "config": {"card_count": 1, "card_limit": 5},
            },
            "consumeables": {
                "cards": {},
                "config": {"card_count": 0, "card_limit": 2},
            },
            "shop_jokers": {
                "cards": {
                    1: {
                        "sort_id": 641,
                        "label": "Rough Gem",
                        "cost": 7,
                        "save_fields": {
                            "center": "j_rough_gem",
                        },
                        "ability": {
                            "name": "Rough Gem",
                            "set": "Joker",
                        },
                    }
                },
                "config": {"card_count": 1, "card_limit": 2},
            },
            "shop_booster": {
                "cards": {
                    1: {
                        "sort_id": 642,
                        "label": "Celestial Pack",
                        "cost": 4,
                        "save_fields": {
                            "center": "p_celestial_normal_4",
                        },
                        "ability": {
                            "name": "Celestial Pack",
                            "set": "Booster",
                        },
                    }
                },
                "config": {"card_count": 1, "card_limit": 2},
            },
            "shop_vouchers": {
                "cards": {
                    1: {
                        "sort_id": 643,
                        "label": "Crystal Ball",
                        "cost": 10,
                        "save_fields": {
                            "center": "v_crystal_ball",
                        },
                        "ability": {
                            "name": "Crystal Ball",
                            "set": "Voucher",
                        },
                    }
                },
                "config": {"card_count": 1, "card_limit": 1},
            },
        },
    }
    return BalatroSaveSnapshot(
        path=Path("save.jkr"),
        modified_ns=123,
        size=100,
        sha256=sha256,
        data=data,
    )


def test_snapshot_from_save_normalizes_live_state():
    snapshot = snapshot_from_save(_save_snapshot(), sequence=4)

    assert snapshot.sequence == 4
    assert snapshot.phase == "SELECTING_HAND"
    assert snapshot.state_complete is False
    assert snapshot.payload["money"] == 4
    assert snapshot.payload["ante_num"] == 1
    assert snapshot.payload["round_num"] == 1
    assert snapshot.payload["deck"] == "RED"
    assert snapshot.payload["stake"] == "WHITE"
    assert snapshot.payload["score"] == 220
    assert snapshot.payload["round"] == {
        "chips": 300,
        "hands_left": 3,
        "discards_left": 2,
    }
    assert snapshot.payload["hand"]["count"] == 2
    assert snapshot.payload["hand"]["limit"] == 8
    assert snapshot.payload["jokers"]["cards"] == [
        {
            "live_id": 640,
            "center": "j_acrobat",
            "label": "Acrobat",
            "ability_name": "Acrobat",
            "ability_set": "Joker",
            "debuff": False,
            "cost": 6,
            "sell_cost": 3,
        }
    ]
    assert snapshot.payload["shop_jokers"]["cards"][0]["label"] == "Rough Gem"
    assert snapshot.payload["shop_jokers"]["cards"][0]["cost"] == 7
    assert snapshot.payload["shop_boosters"]["cards"][0]["label"] == "Celestial Pack"
    assert snapshot.payload["shop_vouchers"]["cards"][0]["label"] == "Crystal Ball"
    assert "raw_save" not in snapshot.payload
    assert "pseudorandom" not in snapshot.payload


def test_save_snapshot_translates_into_framework_state():
    snapshot = snapshot_from_save(_save_snapshot())

    state = DefaultBalatroStateTranslator().translate(snapshot)

    assert state.money == 4
    assert state.ante == 1
    assert state.round == 1
    assert state.score == 220
    assert state.blind_score == 300
    assert state.hands_remaining == 3
    assert state.discards_remaining == 2
    assert state.deck_name == "RED"
    assert state.stake_name == "WHITE"
    assert state.hand_size == 8
    assert state.phase == "SELECTING_HAND"
    assert state.hand_levels["PAIR"] == 2
    assert [(card.rank, card.suit) for card in state.hand] == [
        ("A", "Clubs"),
        ("Q", "Spades"),
    ]
    assert state.hand[1].enhancement == "Steel"
    assert state.hand[1].edition == "Foil"
    assert state.hand[1].seal == "Red"
    assert [(card.rank, card.suit) for card in state.deck] == [
        ("7", "Diamonds"),
    ]
    assert len(state.jokers) == 1
    assert isinstance(state.jokers[0], AcrobatJoker)
    assert state.jokers[0].live_id == 640
    assert state.jokers[0].center == "j_acrobat"
    assert state.blind is not None
    assert state.blind.requirement == 300


def test_save_observer_sequence_changes_only_when_save_changes():
    snapshots = iter([
        _save_snapshot(sha256="first"),
        _save_snapshot(sha256="first"),
        _save_snapshot(sha256="second"),
    ])

    class Reader:
        def read(self, **kwargs):
            return next(snapshots)

    observer = SaveBalatroObserver(Reader())

    assert observer.observe().sequence == 1
    assert observer.observe().sequence == 1
    assert observer.observe().sequence == 2


def test_save_phase_mapping_covers_validated_live_states():
    assert snapshot_from_save(_save_snapshot(state_id=1)).phase == "SELECTING_HAND"
    assert snapshot_from_save(_save_snapshot(state_id=5)).phase == "SHOP"
    assert snapshot_from_save(_save_snapshot(state_id=7)).phase == "BLIND_SELECT"
    assert snapshot_from_save(_save_snapshot(state_id=8)).phase == "ROUND_EVAL"
    assert snapshot_from_save(_save_snapshot(state_id=99)).phase == "SAVE_STATE_99"
