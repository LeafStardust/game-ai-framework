from types import SimpleNamespace

from games.balatro.live.boss_score_transform import boss_hand_scores_zero
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


def test_translator_ignores_stale_eye_and_mouth_state_on_other_bosses():
    translator = DefaultBalatroStateTranslator()
    state = BalatroState()
    translator._translate_blind(
        state,
        {
            "type": "BOSS",
            "name": "The Wheel",
            "score": 40000,
            "hands": ["Pair", "Two Pair"],
            "only_hand": "High Card",
        },
    )
    assert state.boss_name == "The Wheel"
    assert state.boss_blind_hands == set()
    assert state.boss_blind_only_hand is None
    assert not state.boss_blind_state_observed


def test_translator_accepts_only_each_boss_owned_mutable_field():
    translator = DefaultBalatroStateTranslator()

    mouth = BalatroState()
    translator._translate_blind(
        mouth,
        {"type": "BOSS", "name": "The Mouth", "score": 10000, "only_hand": "Flush", "hands": ["Pair"]},
    )
    assert mouth.boss_blind_only_hand == "FLUSH"
    assert mouth.boss_blind_hands == set()
    assert mouth.boss_blind_state_observed

    eye = BalatroState()
    translator._translate_blind(
        eye,
        {"type": "BOSS", "name": "The Eye", "score": 10000, "hands": ["Pair", "Two Pair"], "only_hand": "Flush"},
    )
    assert eye.boss_blind_hands == {"PAIR", "TWO_PAIR"}
    assert eye.boss_blind_only_hand is None
    assert eye.boss_blind_state_observed


def test_mouth_and_eye_zero_score_contracts_are_boss_gated():
    mouth = BalatroState()
    mouth.boss_name = "The Mouth"
    mouth.boss_blind_only_hand = "FLUSH"
    assert boss_hand_scores_zero(mouth, SimpleNamespace(value="PAIR"))
    assert not boss_hand_scores_zero(mouth, SimpleNamespace(value="FLUSH"))

    eye = BalatroState()
    eye.boss_name = "The Eye"
    eye.boss_blind_hands = {"PAIR"}
    assert boss_hand_scores_zero(eye, SimpleNamespace(value="PAIR"))
    assert not boss_hand_scores_zero(eye, SimpleNamespace(value="FLUSH"))

    wheel = BalatroState()
    wheel.boss_name = "The Wheel"
    wheel.boss_blind_only_hand = "HIGH_CARD"
    wheel.boss_blind_hands = {"PAIR"}
    assert not boss_hand_scores_zero(wheel, SimpleNamespace(value="PAIR"))
