from games.balatro.build.effects import SCORE_CHIPS, SCORE_MULT, SCORE_XMULT
from games.balatro.build.joker_scenarios import (
    HAND_RULE,
    JOKER_COPY,
    PERMANENT_CARD_GROWTH,
    SURVIVAL,
    TAG_GENERATE,
    ScenarioJokerBehaviorAnalyzer,
    scenario_feature,
)
from games.balatro.build.joker_semantics import SemanticEffectDescriptor
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.baseball_card import BaseballCardJoker
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.card_sharp import CardSharpJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.diet_cola import DietColaJoker
from games.balatro.jokers.drivers_license import DriversLicenseJoker
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.hiker import HikerJoker
from games.balatro.jokers.mr_bones import MrBonesJoker


def _describe(joker):
    return ScenarioJokerBehaviorAnalyzer().describe(joker)


class _CountingScenarioAnalyzer(ScenarioJokerBehaviorAnalyzer):
    def __init__(self):
        self.uncached_calls = 0

    def _describe_uncached(self, joker):
        self.uncached_calls += 1
        marker = int(getattr(joker, "cache_test_marker", 0))
        return SemanticEffectDescriptor(
            source=type(joker).__name__,
            kind="JOKER",
            evidence=(f"marker={marker}",),
        )


def test_descriptor_cache_is_shared_and_invalidates_on_joker_state_change():
    _CountingScenarioAnalyzer.reset_descriptor_cache()
    first = _CountingScenarioAnalyzer()
    second = _CountingScenarioAnalyzer()
    joker = CardSharpJoker()

    initial = first.describe(joker)
    repeated = second.describe(joker)
    joker.cache_test_marker = 1
    mutated = second.describe(joker)

    assert initial is repeated
    assert first.uncached_calls == 1
    assert second.uncached_calls == 1
    assert mutated.evidence == ("marker=1",)


def test_owned_joker_neighborhood_exposes_joker_count_scoring():
    descriptor = _describe(AbstractJoker())

    assert SCORE_MULT in descriptor.produces
    assert scenario_feature("joker_neighborhood") in descriptor.requires


def test_owned_uncommon_jokers_expose_baseball_card_scaling():
    descriptor = _describe(BaseballCardJoker())

    assert SCORE_XMULT in descriptor.produces
    assert scenario_feature("joker_neighborhood") in descriptor.requires


def test_exhausted_hands_expose_acrobat_condition():
    descriptor = _describe(AcrobatJoker())

    assert SCORE_XMULT in descriptor.produces
    assert scenario_feature("hands_exhausted") in descriptor.requires


def test_repeated_hand_flag_exposes_card_sharp_condition():
    descriptor = _describe(CardSharpJoker())

    assert SCORE_XMULT in descriptor.produces
    assert scenario_feature("repeated_hand") in descriptor.requires


def test_two_pair_card_shape_exposes_clever_joker():
    descriptor = _describe(CleverJoker())

    assert SCORE_CHIPS in descriptor.produces
    assert scenario_feature("two_pair") in descriptor.requires


def test_enhanced_deck_exposes_drivers_license_threshold():
    descriptor = _describe(DriversLicenseJoker())

    assert SCORE_XMULT in descriptor.produces
    assert scenario_feature("enhanced_deck") in descriptor.requires


def test_short_deck_exposes_erosion_scaling():
    descriptor = _describe(ErosionJoker())

    assert SCORE_MULT in descriptor.produces
    assert scenario_feature("short_deck") in descriptor.requires


def test_copy_joker_signal_is_promoted_to_generic_copy_semantics():
    descriptor = _describe(BlueprintJoker())

    assert JOKER_COPY in descriptor.produces
    assert "signal:copy_joker" not in descriptor.produces


def test_hand_rule_signals_are_promoted_without_joker_name_rules():
    descriptor = _describe(FourFingersJoker())

    assert HAND_RULE in descriptor.produces
    assert not any(feature.startswith("signal:") for feature in descriptor.produces)


def test_run_failure_prevention_is_promoted_to_survival_semantics():
    descriptor = _describe(MrBonesJoker())

    assert SURVIVAL in descriptor.produces
    assert "signal:prevented_loss" not in descriptor.produces


def test_self_sale_tag_creation_is_discovered():
    descriptor = _describe(DietColaJoker())

    assert TAG_GENERATE in descriptor.produces
    assert "signal:double_tag" not in descriptor.produces


def test_permanent_card_growth_is_detected_from_card_mutation():
    descriptor = _describe(HikerJoker())

    assert PERMANENT_CARD_GROWTH in descriptor.produces
    assert descriptor.feature_magnitude(PERMANENT_CARD_GROWTH) >= 5.0
