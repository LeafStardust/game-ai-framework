from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_build_policy import BuildAwareLiveHandActionPolicy
from games.balatro.state import BalatroState


class _FlatHandEvaluator:
    """Keep tactical score evidence equal so tests isolate strategic ordering."""

    def project_play(self, state, action):
        del state, action
        return SimpleNamespace(expected_hand_score=100.0)

    def evaluate(self, state, action):
        del state, action
        return 0.0


def _state(ante: int, joker) -> BalatroState:
    state = BalatroState()
    state.ante = ante
    state.jokers = [joker]
    state.blind = SimpleNamespace(requirement=400)
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 3
    return state


def _face_play() -> BalatroAction:
    return BalatroAction(
        PLAY_CARDS,
        cards=[
            BalatroCard("K", "Spades"),
            BalatroCard("7", "Hearts"),
        ],
    )


def _no_face_play() -> BalatroAction:
    return BalatroAction(
        PLAY_CARDS,
        cards=[
            BalatroCard("9", "Spades"),
            BalatroCard("7", "Hearts"),
        ],
    )


def _discard(card: BalatroCard) -> BalatroAction:
    return BalatroAction(DISCARD_CARDS, cards=[card])


def _plan(
    action: BalatroAction,
    *,
    clear_probability: float = 0.80,
    expected_progress: float = 100.0,
) -> LiveBlindPlan:
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear_probability,
            expected_progress=expected_progress,
            expected_score=100.0,
            expected_hands_remaining=3.0,
            expected_discards_remaining=3.0,
        ),
        horizon=1,
        exact=True,
        candidate_count=2,
    )


def _noncredible_play() -> LiveBlindPlan:
    """Satisfy the D1 policy invariant without entering clear-path selection."""
    return _plan(_face_play(), clear_probability=0.10)


def _policy() -> BuildAwareLiveHandActionPolicy:
    return BuildAwareLiveHandActionPolicy(evaluator=_FlatHandEvaluator())


def test_equal_safety_clear_paths_preserve_steel_card():
    state = _state(3, RideTheBusJoker())
    steel = BalatroCard("2", "Spades", enhancement="Steel")
    plain = BalatroCard("2", "Hearts")
    state.hand = [
        steel,
        plain,
        BalatroCard("5", "Clubs"),
        BalatroCard("8", "Diamonds"),
    ]
    discard_steel = _plan(_discard(steel))
    discard_plain = _plan(_discard(plain))

    decision = _policy().decide(
        state,
        [_noncredible_play(), discard_steel, discard_plain],
    )

    assert decision.action is discard_plain.action
    assert any("steel=1" in note for note in decision.rationale)


def test_equal_safety_clear_paths_preserve_blue_seal():
    state = _state(3, RideTheBusJoker())
    blue = BalatroCard("3", "Spades", seal="Blue")
    plain = BalatroCard("3", "Hearts")
    state.hand = [
        blue,
        plain,
        BalatroCard("6", "Clubs"),
        BalatroCard("9", "Diamonds"),
    ]
    discard_blue = _plan(_discard(blue))
    discard_plain = _plan(_discard(plain))

    decision = _policy().decide(
        state,
        [_noncredible_play(), discard_blue, discard_plain],
    )

    assert decision.action is discard_plain.action
    assert any("blue_seal=1" in note for note in decision.rationale)


def test_equal_safety_clear_paths_preserve_semantic_baron_king_source():
    state = _state(3, BaronJoker())
    king = BalatroCard("K", "Hearts")
    queen = BalatroCard("Q", "Hearts")
    state.hand = [
        king,
        queen,
        BalatroCard("2", "Spades"),
        BalatroCard("5", "Diamonds"),
        BalatroCard("8", "Clubs"),
    ]
    discard_king = _plan(_discard(king))
    discard_queen = _plan(_discard(queen))

    decision = _policy().decide(
        state,
        [_noncredible_play(), discard_king, discard_queen],
    )

    assert decision.action is discard_queen.action
    assert any("build_gain=" in note for note in decision.rationale)
