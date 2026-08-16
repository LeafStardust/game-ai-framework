from games.balatro.build.effects import (
    SCORE_CHIPS,
    SCORE_MULT,
    SCORE_XMULT,
    consumable_category_feature,
)
from games.balatro.build.joker_lifecycle import (
    STATEFUL_ACTIVATION,
    STATEFUL_DECAY,
    STATEFUL_SCALING,
    LifecycleJokerBehaviorAnalyzer,
)
from games.balatro.build.joker_semantics import HAND_SIZE_RESOURCE
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.jokers.ancient_joker import AncientJoker
from games.balatro.jokers.campfire import CampfireJoker
from games.balatro.jokers.constellation import ConstellationJoker
from games.balatro.jokers.flash_card import FlashCardJoker
from games.balatro.jokers.fortune_teller import FortuneTellerJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.jokers.throwback import ThrowbackJoker
from games.balatro.jokers.turtle_bean import TurtleBeanJoker
from games.balatro.state import BalatroState


def test_constellation_discovers_planet_driven_persistent_scaling():
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(ConstellationJoker())

    assert SCORE_XMULT in descriptor.produces
    assert STATEFUL_SCALING in descriptor.produces
    assert consumable_category_feature("PLANET") in descriptor.scales_with
    assert "lifecycle:PLANET_USED:scaling" in descriptor.evidence


def test_fortune_teller_discovers_tarot_driven_persistent_scaling():
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(FortuneTellerJoker())

    assert SCORE_MULT in descriptor.produces
    assert STATEFUL_SCALING in descriptor.produces
    assert consumable_category_feature("TAROT") in descriptor.scales_with


def test_green_joker_discovers_repeated_hand_score_growth():
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(GreenJoker())

    assert SCORE_MULT in descriptor.produces
    assert STATEFUL_SCALING in descriptor.produces
    assert "lifecycle:HAND_SCORED:scaling" in descriptor.evidence


def test_runner_discovers_same_hand_repeated_scoring_growth():
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(RunnerJoker())

    assert SCORE_CHIPS in descriptor.produces
    assert STATEFUL_SCALING in descriptor.produces
    assert "lifecycle:SCORE:STRAIGHT:scaling" in descriptor.evidence


def test_campfire_discovers_card_sale_scaling():
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(CampfireJoker())

    assert SCORE_XMULT in descriptor.produces
    assert STATEFUL_SCALING in descriptor.produces
    assert "lifecycle:CARD_SOLD:scaling" in descriptor.evidence


def test_shop_reroll_and_blind_skip_scalers_are_observed():
    analyzer = LifecycleJokerBehaviorAnalyzer()

    flash = analyzer.describe(FlashCardJoker())
    throwback = analyzer.describe(ThrowbackJoker())

    assert SCORE_MULT in flash.produces
    assert STATEFUL_SCALING in flash.produces
    assert SCORE_XMULT in throwback.produces
    assert STATEFUL_SCALING in throwback.produces


def test_round_start_can_activate_later_scoring_effect():
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(AncientJoker())

    assert SCORE_XMULT in descriptor.produces
    assert STATEFUL_ACTIVATION in descriptor.produces
    assert "lifecycle:ROUND_STARTED:activation" in descriptor.evidence


def test_turtle_bean_decay_is_explicit_negative_lifecycle_semantic():
    descriptor = LifecycleJokerBehaviorAnalyzer().describe(TurtleBeanJoker())

    assert HAND_SIZE_RESOURCE in descriptor.produces
    assert STATEFUL_DECAY in descriptor.penalizes
    assert "lifecycle:ROUND_STARTED:decay" in descriptor.evidence


def test_default_build_value_includes_stateful_scaling_semantics():
    value = JokerBuildValueEvaluator().evaluate(BalatroState(), ConstellationJoker())

    assert value.contextual.intrinsic_gain > 0.0
    assert any(
        contribution.feature == STATEFUL_SCALING and contribution.amount > 0.0
        for contribution in value.contextual.contributions
    )
