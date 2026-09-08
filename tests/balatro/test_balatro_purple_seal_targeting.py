from types import SimpleNamespace

from games.balatro.build.consumable_targeting import ContextualConsumableTargetEvaluator
from games.balatro.card import BalatroCard
from games.balatro.spectrals import create_spectral
from games.balatro.state import BalatroState


class _ProfileStub:
    def profile(self, _state):
        return object()


class _AceBuildCardEvaluator:
    def evaluate(
        self,
        _state,
        *,
        rank=None,
        suit=None,
        enhancement=None,
        seal=None,
        edition=None,
        profile=None,
    ):
        del suit, enhancement, edition, profile
        # Model an Aces strategy: an Ace is a core scoring card. Purple Seal itself
        # still has some positive build value, but not enough to justify converting
        # a card the strategy wants to retain instead of discard fodder.
        value = 10.0 if rank == "A" else 0.0
        if seal == "Purple":
            value += 1.0
        return SimpleNamespace(total_gain=value)


def _evaluator():
    return ContextualConsumableTargetEvaluator(
        profiler=_ProfileStub(),
        card_evaluator=_AceBuildCardEvaluator(),
    )


def test_medium_prefers_discard_fodder_over_core_ace_in_ace_build():
    state = BalatroState()
    state.hand = [
        BalatroCard("A", "Spades"),
        BalatroCard("2", "Clubs"),
    ]

    ranked = _evaluator().rank_targets(state, create_spectral("Medium"))

    assert ranked
    assert ranked[0].target_indices == (1,)
    assert ranked[0].cards[0].rank == "2"
    ace = next(item for item in ranked if item.target_indices == (0,))
    assert ranked[0].total_gain > ace.total_gain
    assert any("discard opportunity cost" in note for note in ace.rationale)


def test_medium_avoids_intrinsically_valuable_discard_target_when_plain_fodder_exists():
    state = BalatroState()
    state.hand = [
        BalatroCard("4", "Hearts", enhancement="Steel"),
        BalatroCard("3", "Diamonds"),
    ]

    ranked = _evaluator().rank_targets(state, create_spectral("Medium"))

    assert ranked[0].target_indices == (1,)
    assert ranked[0].cards[0].enhancement is None
