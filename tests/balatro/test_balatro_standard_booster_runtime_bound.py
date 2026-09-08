from games.balatro.build import ContextualPlayingCardSynergyEvaluator
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.standard_booster_expectation_policy import (
    StandardBoosterExpectationEvaluator,
)
from games.balatro.state import BalatroState


class _CountingPlayingCardSynergyEvaluator:
    def __init__(self) -> None:
        self.inner = ContextualPlayingCardSynergyEvaluator()
        self.profiler = self.inner.profiler
        self.calls = 0

    def evaluate(self, *args, **kwargs):
        self.calls += 1
        return self.inner.evaluate(*args, **kwargs)


def test_standard_unopened_expectation_bounds_contextual_graph_calls():
    state = BalatroState()
    state.phase = "SHOP"
    state.joker_generation_edition_rate = 1.0

    counting = _CountingPlayingCardSynergyEvaluator()
    pack_policy = BalatroPackPolicy(
        skip_bias=0.0,
        playing_card_build=counting,
    )
    evaluator = StandardBoosterExpectationEvaluator(pack_policy=pack_policy)

    expected, positive_probability, _ = evaluator.evaluate(state)

    assert expected >= 0.0
    assert 0.0 <= positive_probability <= 1.0
    # Exact factorization: 13 ranks + 4 suits + 8 enhancements + 3 editions
    # + 4 seals + 8*4 enhancement/seal overlap corrections = 64 B6 calls.
    assert counting.calls == 64
