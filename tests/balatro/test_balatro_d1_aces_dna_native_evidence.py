from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live import strategy_hand_policy
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _play_action():
    return BalatroAction(
        PLAY_CARDS,
        cards=[SimpleNamespace(rank="A", suit="Spades")],
    )


def test_dna_aces_evidence_is_owned_by_strategy_policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    monkeypatch.setattr(
        policy,
        "_strategy_fit_without_castle",
        lambda state, action: (2.0, ("base strategy evidence",)),
    )
    monkeypatch.setattr(
        strategy_hand_policy,
        "_castle_strategy_fit",
        lambda state, action: (0.0, ()),
    )
    monkeypatch.setattr(
        strategy_hand_policy,
        "_burnt_strategy_fit",
        lambda state, action, *, hand_evaluator: (0.0, ()),
    )
    monkeypatch.setattr(
        strategy_hand_policy,
        "_dna_aces_fit",
        lambda owner, state, action: (3.0, ("DNA native evidence",)),
    )

    value, rationale = policy._strategy_fit(SimpleNamespace(), _play_action())

    assert value == 5.0
    assert "base strategy evidence" in rationale
    assert "DNA native evidence" in rationale
    assert any(
        "DNA/Aces candidate evidence=+3.000" in note
        and "canonical D1 survival ordering remains authoritative" in note
        for note in rationale
    )


def test_zero_dna_aces_evidence_does_not_add_wrapper_rationale(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    monkeypatch.setattr(
        policy,
        "_strategy_fit_without_castle",
        lambda state, action: (2.0, ("base strategy evidence",)),
    )
    monkeypatch.setattr(
        strategy_hand_policy,
        "_castle_strategy_fit",
        lambda state, action: (0.0, ()),
    )
    monkeypatch.setattr(
        strategy_hand_policy,
        "_burnt_strategy_fit",
        lambda state, action, *, hand_evaluator: (0.0, ()),
    )
    monkeypatch.setattr(
        strategy_hand_policy,
        "_dna_aces_fit",
        lambda owner, state, action: (0.0, ()),
    )

    value, rationale = policy._strategy_fit(SimpleNamespace(), _play_action())

    assert value == 2.0
    assert rationale == ("base strategy evidence",)
