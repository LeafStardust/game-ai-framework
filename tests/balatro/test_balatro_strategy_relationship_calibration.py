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


def _tracker():
    playbook = default_balatro_playbooks().get("RED", "WHITE")
    definition = StrategyDefinition(
        strategy_id="weight_contract",
        name="Weight Contract",
        gold_jokers=frozenset({"goldjoker"}),
        silver_jokers=frozenset({"silverjoker"}),
        bronze_jokers=frozenset({"bronzejoker"}),
        banned_jokers=frozenset({"bannedjoker"}),
    )
    return BalatroStrategyTracker(
        {definition.strategy_id: definition},
        modifier_provider=lambda _state: playbook.strategy_modifiers(),
    )


def _state(*jokers):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.jokers = list(jokers)
    return state


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


def test_non_red_white_identity_keeps_cartridge_values_unmodified():
    tracker = _tracker()
    state = _state()
    state.deck_name = "BLUE"

    # The Red/White cartridge happens to expose the legacy values here; the
    # calibration layer must not leak into a different deck/stake identity.
    assert tracker.relationship_score(state, GOLD) == 8.0
    assert tracker.relationship_score(state, BANNED) == -8.0
