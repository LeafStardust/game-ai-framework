from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.state import BalatroState


def _state_with_history(hand: str | None = None) -> BalatroState:
    state = BalatroState()
    state.hand_play_counts = {} if hand is None else {hand: 8}
    return state


def test_joker_scoring_probe_follows_observed_primary_hand() -> None:
    evaluator = JokerBuildValueEvaluator()
    joker = JollyJoker()

    neutral = evaluator._direct_scoring_gain(_state_with_history(), joker)
    pair_run = evaluator._direct_scoring_gain(_state_with_history("PAIR"), joker)
    flush_run = evaluator._direct_scoring_gain(_state_with_history("FLUSH"), joker)

    assert pair_run > neutral
    assert neutral > flush_run


def test_no_hand_history_preserves_neutral_probe_fallback() -> None:
    evaluator = JokerBuildValueEvaluator()
    state = _state_with_history()

    assert evaluator._probe_weights(state) is None
