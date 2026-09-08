from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _state():
    return SimpleNamespace(
        jokers=[SimpleNamespace(name="Castle", public_state={"suit": "Hearts"})],
    )


def test_castle_discard_evidence_is_owned_by_strategy_policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    monkeypatch.setattr(
        policy,
        "_strategy_fit_without_castle",
        lambda state, action: (2.0, ("base strategy evidence",)),
    )
    action = BalatroAction(
        DISCARD_CARDS,
        cards=[
            SimpleNamespace(suit="Hearts"),
            SimpleNamespace(suit="Hearts"),
            SimpleNamespace(suit="Clubs"),
        ],
    )

    value, rationale = policy._strategy_fit(_state(), action)

    assert value == 3.5
    assert "base strategy evidence" in rationale
    assert any("Castle discard evidence: 2" in note for note in rationale)


def test_castle_evidence_does_not_affect_play_actions(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    monkeypatch.setattr(
        policy,
        "_strategy_fit_without_castle",
        lambda state, action: (2.0, ("base strategy evidence",)),
    )
    action = BalatroAction(
        PLAY_CARDS,
        cards=[SimpleNamespace(suit="Hearts")],
    )

    value, rationale = policy._strategy_fit(_state(), action)

    assert value == 2.0
    assert rationale == ("base strategy evidence",)
