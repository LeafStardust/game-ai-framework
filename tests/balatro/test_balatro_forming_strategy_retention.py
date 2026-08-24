from dataclasses import replace
from types import SimpleNamespace

import games.balatro
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.pinned_strategy_retention_policy import apply_pinned_strategy_retention


class BurntJoker:
    area_index = 0


class SpaceJoker:
    area_index = 0


class RandomJoker:
    area_index = 0


def _decision(index=0):
    return SimpleNamespace(
        action=REPLACE,
        selected=SimpleNamespace(replace_index=index),
        rationale=(),
    )


def test_forming_known_strategy_is_not_protected_by_pinned_retention():
    # Regression characterization: PINNED retention intentionally does not protect
    # a FORMING engine. A separate forming-retention authority must own this case.
    state = SimpleNamespace(jokers=[BurntJoker()], joker_slots=1)
    decision = _decision()
    result = apply_pinned_strategy_retention(state, RandomJoker(), decision)
    assert result.action == REPLACE
