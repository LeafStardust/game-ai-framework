from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro import burnt_bond_execution_policy as burnt_policy
from games.balatro.live import strategy_hand_policy as strategy_module
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


class _HandEvaluator:
    def __init__(self, hand_type: str) -> None:
        self.hand_type = hand_type

    def evaluate(self, cards, *, rules=None):
        return SimpleNamespace(value=self.hand_type)


def _state(**overrides):
    values = {
        "discards_used": 0,
        "discards_remaining": 2,
        "hands_remaining": 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_burnt_target_first_discard_has_target_and_generic_fit(monkeypatch):
    monkeypatch.setattr(
        burnt_policy,
        "_burnt_development",
        lambda state: SimpleNamespace(target="PAIR"),
    )
    action = BalatroAction(
        DISCARD_CARDS,
        cards=[SimpleNamespace(rank="8"), SimpleNamespace(rank="8")],
    )

    value, rationale = burnt_policy._burnt_strategy_fit(
        _state(),
        action,
        hand_evaluator=_HandEvaluator("PAIR"),
    )

    assert value == 2.5
    assert any("matches target" in note for note in rationale)


def test_burnt_generic_first_discard_keeps_only_generic_fit(monkeypatch):
    monkeypatch.setattr(
        burnt_policy,
        "_burnt_development",
        lambda state: SimpleNamespace(target="PAIR"),
    )
    action = BalatroAction(
        DISCARD_CARDS,
        cards=[SimpleNamespace(rank="8")],
    )

    value, rationale = burnt_policy._burnt_strategy_fit(
        _state(),
        action,
        hand_evaluator=_HandEvaluator("HIGH_CARD"),
    )

    assert value == 0.5
    assert any("discarded poker hand=HIGH_CARD" in note for note in rationale)


def test_burnt_evidence_is_owned_by_strategy_policy(monkeypatch):
    policy = StrategyAwareLiveHandActionPolicy()
    monkeypatch.setattr(
        policy,
        "_strategy_fit_without_castle",
        lambda state, action: (2.0, ("base strategy evidence",)),
    )
    monkeypatch.setattr(
        strategy_module,
        "_castle_strategy_fit",
        lambda state, action: (0.0, ()),
    )
    monkeypatch.setattr(
        strategy_module,
        "_burnt_strategy_fit",
        lambda state, action, **kwargs: (0.5, ("native Burnt evidence",)),
    )
    action = BalatroAction(DISCARD_CARDS, cards=[SimpleNamespace(rank="8")])

    value, rationale = policy._strategy_fit(_state(), action)

    assert value == 2.5
    assert rationale == ("base strategy evidence", "native Burnt evidence")


def test_burnt_evidence_rejects_play_and_critical_round_resources(monkeypatch):
    monkeypatch.setattr(
        burnt_policy,
        "_burnt_development",
        lambda state: SimpleNamespace(target="PAIR"),
    )
    play = BalatroAction(PLAY_CARDS, cards=[SimpleNamespace(rank="8")])
    discard = BalatroAction(DISCARD_CARDS, cards=[SimpleNamespace(rank="8")])

    assert burnt_policy._burnt_strategy_fit(
        _state(), play, hand_evaluator=_HandEvaluator("HIGH_CARD")
    ) == (0.0, ())
    assert burnt_policy._burnt_strategy_fit(
        _state(discards_remaining=1),
        discard,
        hand_evaluator=_HandEvaluator("HIGH_CARD"),
    ) == (0.0, ())
    assert burnt_policy._burnt_strategy_fit(
        _state(hands_remaining=1),
        discard,
        hand_evaluator=_HandEvaluator("HIGH_CARD"),
    ) == (0.0, ())
