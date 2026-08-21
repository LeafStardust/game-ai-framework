import pytest

from games.balatro.build_component_roles import BuildComponentRole, BuildComponentRoleClassifier
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.state import BalatroState
from games.balatro.strategy import COMMITTED, GOLD, SILVER, BalatroStrategyTracker
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES


class WalkieTalkieJoker:
    name = "Walkie Talkie"


class EvenStevenJoker:
    name = "Even Steven"


class ThrowbackJoker:
    name = "Throwback"

    def __init__(self, x_mult=1.0):
        self.public_state = {"x_mult": x_mult}


def _state(*jokers, ante=3):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = ante
    state.jokers = list(jokers)
    state.joker_slots = 5
    return state


def _tracker():
    playbook = default_balatro_playbooks().get("RED", "WHITE")
    return BalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        modifier_provider=lambda _state: playbook.strategy_modifiers(),
    )


def _assessment(tracker, state, strategy_id):
    return next(value for value in tracker.assess(state) if value.strategy_id == strategy_id)


def test_walkie_alone_is_silver_and_does_not_commit_ten_four():
    tracker = _tracker()
    state = _state(WalkieTalkieJoker())

    assessment = _assessment(tracker, state, "ten_four")
    relation = tracker.evaluate_item(state, state.jokers[0], kind="JOKER")

    assert assessment.score == pytest.approx(3.0)
    assert assessment.gold_owned == 0
    assert assessment.silver_owned == 1
    assert assessment.status != COMMITTED
    assert relation.tier == SILVER


def test_even_steven_is_direct_silver_ten_four_support():
    tracker = _tracker()
    state = _state(EvenStevenJoker())

    assessment = _assessment(tracker, state, "ten_four")

    assert assessment.score == pytest.approx(3.0)
    assert assessment.gold_owned == 0
    assert assessment.silver_owned == 1


def test_walkie_even_pair_promotes_only_walkie_to_gold():
    tracker = _tracker()
    state = _state(WalkieTalkieJoker(), EvenStevenJoker())

    assessment = _assessment(tracker, state, "ten_four")
    walkie = tracker.evaluate_item(state, state.jokers[0], kind="JOKER")
    even = tracker.evaluate_item(state, state.jokers[1], kind="JOKER")

    assert assessment.score == pytest.approx(13.0)
    assert assessment.gold_owned == 1
    assert assessment.silver_owned == 1
    assert assessment.status == COMMITTED
    assert walkie.tier == GOLD
    assert even.tier == SILVER


def test_primary_and_relevant_strategy_components_are_not_filler():
    tracker = _tracker()
    state = _state(WalkieTalkieJoker(), EvenStevenJoker())

    components = BuildComponentRoleClassifier().classify(
        state,
        strategy_tracker=tracker,
    )
    by_name = {component.name: component for component in components}

    assert by_name["Walkie Talkie"].role == BuildComponentRole.CORE
    assert by_name["Walkie Talkie"].strategy_id == "ten_four"
    assert by_name["Even Steven"].role == BuildComponentRole.SUPPORT
    assert by_name["Even Steven"].strategy_id == "ten_four"


def test_unscaled_throwback_is_silver_then_becomes_gold_after_real_skip_scaling():
    tracker = _tracker()
    inactive = _state(ThrowbackJoker(1.0))
    scaled = _state(ThrowbackJoker(1.25))

    before = _assessment(tracker, inactive, "throwback")
    after = _assessment(tracker, scaled, "throwback")

    assert before.score == pytest.approx(3.0)
    assert before.gold_owned == 0
    assert before.silver_owned == 1
    assert after.score == pytest.approx(10.0)
    assert after.gold_owned == 1
    assert after.silver_owned == 0


def test_build_health_coherence_uses_current_commit_threshold_not_legacy_nine():
    tracker = _tracker()
    state = _state(WalkieTalkieJoker())
    health = RuntimeBuildHealthEvaluator().inputs(state, strategy_tracker=tracker)

    # One Silver is score 3 against the current commit floor 10. With one aligned
    # Joker the coherence formula is 0.6*(3/10) + 0.4*1 = 0.58.
    assert health.coherence_ratio == pytest.approx(0.58)
