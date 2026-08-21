from games.balatro.state import BalatroState
from games.balatro.strategy import (
    AVAILABLE,
    BalatroStrategyTracker,
    StrategyDefinition,
)


class GoldOneJoker:
    pass


class GoldTwoJoker:
    pass


class BadJoker:
    pass


class CleanJoker:
    pass


def _state(*jokers):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = 6
    state.jokers = list(jokers)
    return state


def _tracker(include_clean=True):
    conflicted = StrategyDefinition(
        strategy_id="conflicted",
        name="Conflicted",
        gold_jokers=frozenset({"goldonejoker", "goldtwojoker"}),
        banned_jokers=frozenset({"badjoker"}),
    )
    definitions = {"conflicted": conflicted}
    if include_clean:
        definitions["clean"] = StrategyDefinition(
            strategy_id="clean",
            name="Clean",
            silver_jokers=frozenset({"cleanjoker"}),
        )
    return BalatroStrategyTracker(definitions)


def test_positive_but_banned_route_cannot_control_ante_six():
    state = _state(GoldOneJoker(), GoldTwoJoker(), BadJoker(), CleanJoker())
    resolution = _tracker().observe(state)

    conflicted = resolution.assessment("conflicted")
    assert conflicted is not None
    assert conflicted.score == 8.0
    assert conflicted.banned_owned == 1
    assert resolution.dominant_strategy_id == "clean"
    assert resolution.committed_strategy_id == "clean"


def test_only_positive_route_being_banned_falls_back_to_meta_value():
    state = _state(GoldOneJoker(), GoldTwoJoker(), BadJoker())
    resolution = _tracker(include_clean=False).observe(state)

    conflicted = resolution.assessment("conflicted")
    assert conflicted is not None
    assert conflicted.score == 8.0
    assert resolution.dominant_strategy_id is None
    assert resolution.committed_strategy_id is None
    assert resolution.active_status == AVAILABLE
