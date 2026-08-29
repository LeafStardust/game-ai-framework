from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("A", "Spades", live_id=1),
        BalatroCard("A", "Hearts", live_id=2),
        BalatroCard("K", "Clubs", live_id=3),
        BalatroCard("7", "Diamonds", live_id=4),
        BalatroCard("3", "Spades", live_id=5),
    ]
    state.deck = []
    state.score = 0
    state.hands_remaining = 2
    state.discards_remaining = 0
    state.blind = Blind(BlindType.SMALL, 1_000)
    state.jokers = []
    return state


def test_beam_ranking_does_not_enter_full_play_projection(monkeypatch):
    """Beam admission must stay bounded before the first expectimax node.

    A real late-game tuner run spent roughly forty seconds in ``project_play``
    while ranking the root beam and then reported ``nodes=0``.  Full stochastic
    and Joker projection belongs to candidate evaluation after beam admission, not
    to the pre-search ranking pass.
    """
    evaluator = LiveHandDecisionEvaluator()

    def forbidden_project_play(*args, **kwargs):
        raise AssertionError("beam ranking entered full play projection")

    monkeypatch.setattr(evaluator, "project_play", forbidden_project_play)
    planner = LiveBlindClearPlanner(
        evaluator=evaluator,
        play_width=2,
        discard_width=0,
        horizon=1,
    )

    candidates = planner._candidate_actions(_state(), allow_discards=False)

    assert candidates
    assert len(candidates) <= 2
    assert planner.nodes_evaluated == 0
