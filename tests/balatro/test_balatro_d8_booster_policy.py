from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_BOOSTER, BalatroAction
from games.balatro.live.shop import LiveShopItem
from games.balatro.shop_booster_policy import (
    BUY,
    HOLD,
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
)
from games.balatro.state import BalatroState
from games.balatro.tarots import Death


def _state(*, money: int = 20, ante: int = 1) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.ante = ante
    return state


def _specialized_state(*, money: int = 20, ante: int = 1) -> BalatroState:
    state = _state(money=money, ante=ante)
    state.hand_levels["FLUSH"] = 2
    state.hand_play_counts["FLUSH"] = 8
    return state


def _action(label: str, *, price: int = 4, index: int = 0) -> BalatroAction:
    return BalatroAction(
        BUY_BOOSTER,
        target=LiveShopItem(
            kind="BOOSTER",
            label=label,
            price=price,
            area_index=index,
        ),
    )


@pytest.mark.parametrize(
    ("label", "family", "offers", "selections"),
    (
        ("Standard Pack", "STANDARD", 3, 1),
        ("Arcana Pack", "ARCANA", 3, 1),
        ("Celestial Pack", "CELESTIAL", 3, 1),
        ("Buffoon Pack", "BUFFOON", 2, 1),
        ("Spectral Pack", "SPECTRAL", 2, 1),
    ),
)
def test_d8_models_all_five_pack_families(label, family, offers, selections):
    recommendation = BuildAwareShopBoosterPolicy().recommend(_state(), _action(label))

    assert recommendation.family == family
    assert recommendation.variant == "NORMAL"
    assert recommendation.offer_count == offers
    assert recommendation.selection_count == selections
    assert 0.0 <= recommendation.per_offer_hit_probability <= 1.0
    assert 0.0 <= recommendation.at_least_one_hit_probability <= 1.0
    assert recommendation.decision in {BUY, HOLD}


def test_d8_celestial_value_rises_with_observed_hand_specialization():
    policy = BuildAwareShopBoosterPolicy()
    baseline = _state(money=50)
    specialized = _specialized_state(money=50)

    baseline_rec = policy.recommend(baseline, _action("Celestial Pack"))
    specialized_rec = policy.recommend(specialized, _action("Celestial Pack"))

    assert specialized_rec.build_need_score > baseline_rec.build_need_score
    assert (
        specialized_rec.at_least_one_hit_probability
        > baseline_rec.at_least_one_hit_probability
    )
    assert specialized_rec.option_utility > baseline_rec.option_utility


def test_d8_buffoon_fails_closed_without_a_free_joker_slot():
    state = _state(money=50)
    state.jokers = [object() for _ in range(state.joker_slots)]

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Buffoon Pack"),
    )

    assert recommendation.decision == HOLD
    assert recommendation.per_offer_hit_probability == pytest.approx(0.0)
    assert recommendation.at_least_one_hit_probability == pytest.approx(0.0)


def test_d8_single_hand_normal_celestial_is_held_even_with_healthy_reserve():
    policy = BuildAwareShopBoosterPolicy()

    rich = policy.recommend(_specialized_state(money=20), _action("Celestial Pack"))
    pressured = policy.recommend(_specialized_state(money=5), _action("Celestial Pack"))

    assert rich.decision == HOLD
    assert rich.at_least_one_hit_probability == pytest.approx(0.25)
    assert any("useful=1/12" in note for note in rich.rationale)
    assert pressured.decision == HOLD
    assert pressured.reserve_penalty > rich.reserve_penalty


def test_d8_generic_celestial_pack_is_held_without_hand_direction():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _state(money=50),
        _action("Celestial Pack"),
    )

    assert recommendation.decision == HOLD
    assert any("no marginal hand-development headroom" in note for note in recommendation.rationale)


def test_d8_one_selection_standard_pack_is_held_at_zero_scoped_need():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _state(money=50),
        _action("Standard Pack"),
    )

    assert recommendation.build_need_score == pytest.approx(0.0)
    assert recommendation.decision == HOLD
    assert any("random deck bloat" in note for note in recommendation.rationale)


def test_d8_held_death_does_not_fabricate_standard_pack_card_target_demand():
    state = _state(money=50)
    state.consumables = [Death()]

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Standard Pack"),
    )

    assert recommendation.build_need_score == pytest.approx(0.0)
    assert recommendation.decision == HOLD
    assert any("relevant unmet build features=none" in note for note in recommendation.rationale)


def test_d8_mega_standard_pack_keeps_two_choice_option_value_at_zero_need():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _state(money=50),
        _action("Mega Standard Pack"),
    )

    assert recommendation.build_need_score == pytest.approx(0.0)
    assert recommendation.selection_count == 2
    assert not any("random deck bloat" in note for note in recommendation.rationale)


def test_d8_deck_growth_scorer_can_override_zero_need_standard_veto():
    state = _state(money=50)
    state.jokers = [SimpleNamespace(name="Blue Joker")]

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Standard Pack"),
    )

    assert recommendation.decision == BUY
    assert any("deck-growth composition" in note for note in recommendation.rationale)


def test_d8_celestial_is_held_after_relevant_hand_reaches_current_target_level():
    state = _state(money=50)
    state.hand_levels["FLUSH"] = 3
    state.hand_play_counts["FLUSH"] = 8

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Celestial Pack"),
    )

    assert recommendation.decision == HOLD
    assert any("effective Celestial headroom=0" in note for note in recommendation.rationale)


def test_d8_off_path_planet_investment_consumes_repeated_celestial_budget():
    state = _specialized_state(money=50)
    state.hand_levels["FOUR_OF_A_KIND"] = 2

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Celestial Pack"),
    )

    assert recommendation.decision == HOLD
    assert any("Planet investment=2/2; remaining=0" in note for note in recommendation.rationale)


def test_d8_more_realized_play_reopens_headroom_but_not_false_pack_odds():
    state = _state(money=50)
    state.hand_levels["FLUSH"] = 2
    state.hand_levels["FOUR_OF_A_KIND"] = 2
    state.hand_play_counts["FLUSH"] = 14

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Celestial Pack"),
    )

    assert recommendation.decision == HOLD
    assert recommendation.at_least_one_hit_probability == pytest.approx(0.25)
    assert any("effective Celestial headroom=1" in note for note in recommendation.rationale)


def test_d8_two_relevant_hands_can_clear_exact_celestial_hit_threshold():
    state = _state(money=50)
    state.hand_play_counts["FLUSH"] = 8
    state.hand_play_counts["PAIR"] = 8

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Celestial Pack"),
    )

    assert recommendation.decision == BUY
    assert recommendation.at_least_one_hit_probability == pytest.approx(5 / 11)
    assert any("useful=2/12" in note for note in recommendation.rationale)


def test_d8_one_hand_jumbo_celestial_is_not_logged_as_near_certain():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _specialized_state(money=50),
        _action("Jumbo Celestial Pack", price=6),
    )

    assert recommendation.decision == HOLD
    assert recommendation.at_least_one_hit_probability == pytest.approx(5 / 12)


def test_d8_mega_pack_has_more_option_value_than_normal_at_equal_price():
    policy = BuildAwareShopBoosterPolicy()
    state = _specialized_state(money=50)

    normal = policy.recommend(state, _action("Celestial Pack"))
    mega = policy.recommend(state, _action("Mega Celestial Pack"))

    assert mega.offer_count == 5
    assert mega.selection_count == 2
    assert mega.at_least_one_hit_probability > normal.at_least_one_hit_probability
    assert mega.option_utility > normal.option_utility


def test_d8_arcana_and_spectral_are_valued_but_fail_closed_until_d9_d10():
    policy = BuildAwareShopBoosterPolicy()
    state = _state(money=50)

    arcana = policy.recommend(state, _action("Arcana Pack"))
    spectral = policy.recommend(state, _action("Spectral Pack"))

    assert arcana.option_utility > 0.0
    assert spectral.option_utility > 0.0
    assert arcana.decision == HOLD
    assert spectral.decision == HOLD
    assert any("D9/D10" in note for note in arcana.rationale)
    assert any("D9/D10" in note for note in spectral.rationale)


def test_d8_threshold_mapping_is_layer_owned_and_rejects_unknown_keys():
    thresholds = BoosterAcquisitionThresholds.from_mapping(
        {"minimum_buy_advantage": 1.25}
    )
    assert thresholds.minimum_buy_advantage == pytest.approx(1.25)

    with pytest.raises(ValueError, match="unknown D8 booster threshold"):
        BoosterAcquisitionThresholds.from_mapping({"joker_threshold": 1.0})
