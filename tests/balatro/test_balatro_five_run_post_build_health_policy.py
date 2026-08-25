from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import (
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)


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
    weak = LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=(object(),)),
        value=LiveBlindPlanValue(0.1, 0.2, 100.0, 3.0, 2.0),
        horizon=1,
        exact=True,
        candidate_count=2,
    )
    strong = LiveBlindPlan(
        action=BalatroAction(PLAY_CARDS, cards=(object(), object())),
        value=LiveBlindPlanValue(0.4, 0.6, 300.0, 2.0, 2.0),
        horizon=1,
        exact=True,
        candidate_count=2,
    )
    policy = LiveHandActionPolicy()
    policy.decide = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError("expired timeout fallback must not re-enter full D1 policy")
    )
    state = SimpleNamespace(
        blind=SimpleNamespace(requirement=600),
        score=0,
        hands_remaining=4,
        discards_remaining=4,
    )
    engine = SimpleNamespace(
        policy=policy,
        _safe_pace_completed_root_plans=(weak, strong),
    )

    result = LiveHandActionDecisionEngine._structural_timeout_fallback(
        engine,
        state,
        search_attempts=("shallow-complete", "deep-timeout"),
    )

    assert result.selected_plan is strong
    assert result.action.name == PLAY_CARDS
    assert result.best_discard is None
    assert result.plans == (weak, strong)
    assert "without any post-deadline projection" in result.rationale[1]


class _EqualScoreOrderPolicy(JokerOrderPolicy):
    def __init__(self):
        self.minimum_improvement = 0.0
        self.last_negative_retention_diagnostics = ()
        self.evaluator = SimpleNamespace()

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
