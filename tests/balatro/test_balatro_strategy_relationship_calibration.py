from games.balatro.playbook import default_balatro_playbooks
from games.balatro.state import BalatroState
from games.balatro.strategy import (
    BANNED,
    BRONZE,
    COMMITTED,
    GOLD,
    MATURE,
    SILVER,
    BalatroStrategyTracker,
    StrategyDefinition,
)


class GoldJoker:
    pass


class SilverJoker:
    pass


class BronzeJoker:
    pass


class BannedJoker:
    pass


def _definition():
    return StrategyDefinition(
        strategy_id="weight_contract",
        name="Weight Contract",
        gold_jokers=frozenset({"goldjoker"}),
        silver_jokers=frozenset({"silverjoker"}),
        bronze_jokers=frozenset({"bronzejoker"}),
        banned_jokers=frozenset({"bannedjoker"}),
    )


def _tracker():
    playbook = default_balatro_playbooks().get("RED", "WHITE")
    definition = _definition()
    return BalatroStrategyTracker(
        {definition.strategy_id: definition},
        modifier_provider=lambda _state: playbook.strategy_modifiers(),
    )


def _unconfigured_tracker():
    definition = _definition()
    return BalatroStrategyTracker({definition.strategy_id: definition})


def _state(*jokers):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.jokers = list(jokers)
    return state


def test_red_white_playbook_exposes_effective_relationship_calibration():
    modifiers = default_balatro_playbooks().get("RED", "WHITE").strategy_modifiers()

    assert modifiers["gold_evidence"] == 10.0
    assert modifiers["silver_evidence"] == 3.0
    assert modifiers["bronze_evidence"] == 1.0
    assert modifiers["banned_evidence"] == -12.0
    assert modifiers["commit_threshold"] == 10.0
    assert modifiers["mature_threshold"] == 20.0


def test_red_white_effective_relationship_weights_are_10_3_1_minus_12():
    tracker = _tracker()
    state = _state()

    assert tracker.relationship_score(state, GOLD) == 10.0
    assert tracker.relationship_score(state, SILVER) == 3.0
    assert tracker.relationship_score(state, BRONZE) == 1.0
    assert tracker.relationship_score(state, BANNED) == -12.0


def test_one_gold_commits_three_silvers_do_not_outrank_it():
    tracker = _tracker()

    gold = tracker.assess(_state(GoldJoker()))[0]
    silvers = tracker.assess(_state(SilverJoker(), SilverJoker(), SilverJoker()))[0]

    assert gold.score == 10.0
    assert gold.status == COMMITTED
    assert silvers.score == 9.0
    assert silvers.score < gold.score
    assert silvers.status != COMMITTED


def test_two_gold_cores_are_mature():
    assessment = _tracker().assess(_state(GoldJoker(), GoldJoker()))[0]

    assert assessment.score == 20.0
    assert assessment.status == MATURE


def test_one_banned_conflict_outweighs_one_gold_core():
    assessment = _tracker().assess(_state(GoldJoker(), BannedJoker()))[0]

    assert assessment.score == -2.0


def test_non_red_white_identity_keeps_unconfigured_universal_defaults():
    tracker = _unconfigured_tracker()
    state = _state()
    state.deck_name = "BLUE"

    # Red/White calibration is scoped to that cartridge/state identity. A tracker
    # with no Red/White cartridge keeps the universal fallback geometry.
    assert tracker.relationship_score(state, GOLD) == 8.0
    assert tracker.relationship_score(state, BANNED) == -8.0
