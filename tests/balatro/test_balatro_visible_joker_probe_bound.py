from types import SimpleNamespace

from games.balatro.build import JokerBuildValueEvaluator
from games.balatro.hand import PokerHand


def _state(*, jokers: int, slots: int, counts=None):
    return SimpleNamespace(
        jokers=[object() for _ in range(jokers)],
        joker_slots=slots,
        hand_play_counts=dict(counts or {}),
    )


def test_free_slot_visible_joker_value_uses_at_most_three_scoring_probes():
    evaluator = JokerBuildValueEvaluator()

    probes = tuple(evaluator._scoring_probes(_state(jokers=2, slots=5)))

    assert len(probes) == 3


def test_full_roster_replacement_value_uses_one_scoring_probe():
    evaluator = JokerBuildValueEvaluator()

    probes = tuple(evaluator._scoring_probes(_state(jokers=5, slots=5)))

    assert len(probes) == 1


def test_bounded_probe_prefers_publicly_observed_hand_history():
    evaluator = JokerBuildValueEvaluator()

    probes = tuple(
        evaluator._scoring_probes(
            _state(
                jokers=5,
                slots=5,
                counts={"FLUSH": 9, "PAIR": 2},
            )
        )
    )

    assert len(probes) == 1
    assert probes[0][0] is PokerHand.FLUSH
