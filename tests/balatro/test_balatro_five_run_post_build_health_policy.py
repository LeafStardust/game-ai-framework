from types import SimpleNamespace

from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.live.hand_action_policy import LiveHandActionDecisionEngine
from games.balatro.safe_pace_timeout_patch import install_safe_pace_timeout_patch
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


def _joker(name: str, *, x_mult: float = 1.0):
    return SimpleNamespace(name=name, x_mult=x_mult)


def test_timeout_fallback_delegates_without_fabricating_max_width_discard(monkeypatch):
    calls = []

    def original(self, state, *, search_attempts):
        calls.append((self, state, search_attempts))
        return "ORIGINAL_STRUCTURAL_FALLBACK"

    monkeypatch.setattr(
        LiveHandActionDecisionEngine,
        "_structural_timeout_fallback",
        original,
    )
    monkeypatch.setattr(
        LiveHandActionDecisionEngine,
        "_safe_pace_timeout_installed",
        False,
    )

    install_safe_pace_timeout_patch()

    state = SimpleNamespace(discards_remaining=4)
    engine = SimpleNamespace(
        planner=SimpleNamespace(
            action_generator=SimpleNamespace(
                generate_discard_actions=lambda _state: [
                    SimpleNamespace(cards=(0, 1, 2, 3, 4))
                ]
            )
        )
    )
    result = LiveHandActionDecisionEngine._structural_timeout_fallback(
        engine,
        state,
        search_attempts=("timeout",),
    )

    assert result == "ORIGINAL_STRUCTURAL_FALLBACK"
    assert calls == [(engine, state, ("timeout",))]


def test_blackboard_is_silver_not_gold():
    strategy = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["blackboard"]

    assert strategy.relationship_for(_joker("Blackboard"), kind="JOKER") == "SILVER"


def test_swashbuckler_is_required_and_egg_gift_card_are_gold_support():
    strategy = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["swashbuckler"]

    assert "swashbuckler" in strategy.required_jokers
    assert strategy.relationship_for(_joker("Swashbuckler"), kind="JOKER") == "SILVER"
    assert strategy.relationship_for(_joker("Egg"), kind="JOKER") == "GOLD"
    assert strategy.relationship_for(_joker("Gift Card"), kind="JOKER") == "GOLD"


class _EqualScoreOrderPolicy(JokerOrderPolicy):
    def __init__(self):
        self.minimum_improvement = 0.0
        self.last_negative_retention_diagnostics = ()
        self.evaluator = SimpleNamespace(strategy_tracker=None)

    def _score(self, state, permutation, *, phase):
        del state, permutation, phase
        return 100.0, ()


def test_equal_score_order_right_aligns_ramen_xmult():
    state = SimpleNamespace(
        phase="SELECTING_HAND",
        jokers=[
            _joker("Even Steven"),
            _joker("Ramen", x_mult=1.84),
            _joker("Scholar"),
            _joker("Blue Joker"),
        ],
    )

    decision = _EqualScoreOrderPolicy().recommend(state)

    assert decision is not None
    assert decision.permutation[-1] == 1
    assert decision.ordered_score == decision.current_score == 100.0
    assert any("right-aligns active XMult" in note for note in decision.rationale)
