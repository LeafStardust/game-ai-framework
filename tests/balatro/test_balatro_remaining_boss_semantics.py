from __future__ import annotations

from types import SimpleNamespace

from games.balatro.card import BalatroCard
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.live.crimson_heart import CrimsonHeartScoreOutcomeModel
from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
)
from games.balatro.live.verdant_leaf import VerdantLeafSalePolicy
from games.balatro.state import BalatroState


def _verdant_state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.boss_name = "Verdant Leaf"
    state.hand = [BalatroCard("A", "Spades", debuffed=True)]
    return state


class _VerdantPlanner:
    def plan(self, state):
        debuffed = any(bool(getattr(card, "debuffed", False)) for card in state.hand)
        probability = 0.20 if debuffed else 0.80
        return SimpleNamespace(value=SimpleNamespace(clear_probability=probability))


def test_verdant_leaf_sells_only_legal_joker_to_lift_card_debuff() -> None:
    state = _verdant_state()

    eternal = FlatMultJoker(20)
    eternal.eternal = True
    eternal.area_index = 0
    eternal.label = "Eternal scorer"

    fodder = FlatMultJoker(0)
    fodder.area_index = 1
    fodder.label = "Fodder"

    state.jokers = [eternal, fodder]

    decision = VerdantLeafSalePolicy(planner=_VerdantPlanner()).recommend(state)

    assert decision is not None
    assert decision.joker_index == 1
    assert decision.joker == "Fodder"
    assert any("0.200000->0.800000" in note for note in decision.rationale)


def test_verdant_leaf_does_not_sell_when_chicot_disables_boss() -> None:
    state = _verdant_state()
    chicot = ChicotJoker()
    chicot.area_index = 0
    state.jokers = [chicot]

    assert VerdantLeafSalePolicy(planner=_VerdantPlanner()).recommend(state) is None


def test_crimson_heart_next_debuff_excludes_previous_disabled_joker() -> None:
    state = BalatroState()
    state.boss_name = "Crimson Heart"

    previous = FlatMultJoker(4)
    previous.debuffed = True
    left = FlatMultJoker(8)
    right = FlatMultJoker(12)
    state.jokers = [previous, left, right]

    transition = ScoreProjectionTransition(
        distribution=ScoreOutcomeDistribution(
            outcomes=(ScoreOutcome(100, 1.0, state_after_scoring=state),),
        ),
        state_after_scoring=state,
    )

    branched = CrimsonHeartScoreOutcomeModel()._branch_next_disabled_joker(
        transition
    )

    assert len(branched.distribution.outcomes) == 2
    assert all(
        outcome.probability == 0.5
        for outcome in branched.distribution.outcomes
    )
    for outcome in branched.distribution.outcomes:
        flags = [bool(getattr(joker, "debuffed", False)) for joker in outcome.state_after_scoring.jokers]
        assert flags[0] is False
        assert sum(flags) == 1
    assert (
        CrimsonHeartScoreOutcomeModel.RANDOM_SOURCE
        in branched.distribution.random_sources
    )


def test_crimson_heart_chicot_bypasses_next_debuff_branch() -> None:
    state = BalatroState()
    state.boss_name = "Crimson Heart"
    state.jokers = [ChicotJoker(), FlatMultJoker(20)]

    transition = ScoreProjectionTransition(
        distribution=ScoreOutcomeDistribution(
            outcomes=(ScoreOutcome(100, 1.0, state_after_scoring=state),),
        ),
        state_after_scoring=state,
    )

    projected = CrimsonHeartScoreOutcomeModel()._branch_next_disabled_joker(
        transition
    )

    assert len(projected.distribution.outcomes) == 1
    assert projected.distribution.random_sources == ()
    assert not any(
        bool(getattr(joker, "debuffed", False))
        for joker in projected.distribution.outcomes[0].state_after_scoring.jokers
    )
