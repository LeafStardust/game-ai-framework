from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.live.hand_action_policy import (
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


def _joker(name: str, *, x_mult: float = 1.0):
    return SimpleNamespace(name=name, x_mult=x_mult)


def test_timeout_fallback_never_fabricates_a_discard_without_completed_search():
    play = BalatroAction(PLAY_CARDS, cards=(object(),))
    planner = SimpleNamespace(
        play_width=3,
        _require_state=lambda _state: None,
        _child_play_candidates=lambda _state, _width: [play],
    )
    engine = SimpleNamespace(
        planner=planner,
        policy=LiveHandActionPolicy(),
        _safe_pace_completed_root_plans=(),
    )
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=600),
        score=0,
        hands_remaining=4,
        discards_remaining=4,
    )

    result = LiveHandActionDecisionEngine._structural_timeout_fallback(
        engine,
        state,
        search_attempts=("timeout",),
    )

    assert result.action.name == PLAY_CARDS
    assert result.best_discard is None


def test_timeout_reuses_completed_root_search_before_structural_fallback():
    completed = (SimpleNamespace(action=SimpleNamespace(name="PLAY_CARDS")),)
    calls = []
    sentinel = SimpleNamespace(rationale=("completed search policy decision",))

    class _Policy:
        def decide(self, state, plans, **kwargs):
            calls.append((state, tuple(plans), kwargs))
            return sentinel

    state = SimpleNamespace()
    engine = SimpleNamespace(
        policy=_Policy(),
        _safe_pace_completed_root_plans=completed,
    )

    result = LiveHandActionDecisionEngine._structural_timeout_fallback(
        engine,
        state,
        search_attempts=("shallow-complete", "deep-timeout"),
    )

    assert result is sentinel
    assert calls == [
        (
            state,
            completed,
            {
                "search_attempts": ("shallow-complete", "deep-timeout"),
                "setup_discard_consensus": False,
            },
        )
    ]


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
