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


def test_d8_celestial_specialization_uses_exact_public_planet_probability():
    policy = BuildAwareShopBoosterPolicy()
    baseline = _state(money=50)
    specialized = _specialized_state(money=50)

    baseline_rec = policy.recommend(baseline, _action("Celestial Pack"))
    specialized_rec = policy.recommend(specialized, _action("Celestial Pack"))

    assert specialized_rec.build_need_score > baseline_rec.build_need_score
    # The no-direction baseline is stopped by the authoritative headroom veto after
    # cheap parent-D8 accounting, so its inherited generic family probability is not
    # comparable to the specialized path's exact finite Planet-pool probability.
    # With one relevant hand among nine ordinary eligible Planets and three offers,
    # drawing without replacement gives exactly 3/9 = 1/3.
    assert specialized_rec.at_least_one_hit_probability == pytest.approx(1 / 3)
    assert any("useful=1/9" in note for note in specialized_rec.rationale)
    assert specialized_rec.option_utility >= 0.0


def test_d8_buffoon_fails_closed_without_public_joker_pool():
    state = _state(money=50)
    state.jokers = [object() for _ in range(state.joker_slots)]

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Buffoon Pack"),
    )

    assert recommendation.decision == HOLD
    assert recommendation.offer_count == 2
    assert recommendation.selection_count == 1
    assert recommendation.per_offer_hit_probability == pytest.approx(0.0)
    assert recommendation.at_least_one_hit_probability == pytest.approx(0.0)
    assert any("public Joker expectation incomplete" in note for note in recommendation.rationale)


def test_d8_single_hand_normal_celestial_is_held_even_with_healthy_reserve():
    policy = BuildAwareShopBoosterPolicy()

    rich = policy.recommend(_specialized_state(money=20), _action("Celestial Pack"))
    pressured = policy.recommend(_specialized_state(money=5), _action("Celestial Pack"))

    assert rich.decision == HOLD
    # Early public Planet pool contains the nine ordinary Planet cards. Drawing
    # three without replacement with one relevant hand gives exactly 3/9 = 1/3.
    assert rich.at_least_one_hit_probability == pytest.approx(1 / 3)
    assert any("useful=1/9" in note for note in rich.rationale)
    assert pressured.decision == HOLD
    assert pressured.reserve_penalty > rich.reserve_penalty


def test_d8_generic_celestial_pack_is_held_without_hand_direction():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _state(money=50),
        _action("Celestial Pack"),
    )

    assert recommendation.decision == HOLD
    assert any("no marginal hand-development headroom" in note for note in recommendation.rationale)


def test_d8_standard_pack_uses_exact_generator_even_at_zero_scoped_need():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _state(money=50),
        _action("Standard Pack"),
    )

    assert recommendation.build_need_score == pytest.approx(0.0)
    assert recommendation.option_utility > 0.0
    assert any("exact base-game" in note for note in recommendation.rationale)
    assert any("best-of-3/5 improvement is deliberately omitted" in note for note in recommendation.rationale)


def test_d8_held_death_does_not_fabricate_standard_pack_card_target_demand():
    baseline_state = _state(money=50)
    held_death_state = _state(money=50)
    held_death_state.consumables = [Death()]

    baseline = BuildAwareShopBoosterPolicy().recommend(
        baseline_state,
        _action("Standard Pack"),
    )
    with_death = BuildAwareShopBoosterPolicy().recommend(
        held_death_state,
        _action("Standard Pack"),
    )

    assert with_death.build_need_score == pytest.approx(0.0)
    assert with_death.option_utility == pytest.approx(baseline.option_utility)
    assert with_death.decision == baseline.decision


def test_d8_mega_standard_pack_keeps_public_layout_metadata():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _state(money=50),
        _action("Mega Standard Pack"),
    )

    assert recommendation.build_need_score == pytest.approx(0.0)
    assert recommendation.offer_count == 5
    assert recommendation.selection_count == 2
    assert recommendation.option_utility > 0.0


def test_d8_standard_exact_generator_integrates_deck_growth_value():
    baseline_state = _state(money=50)
    growth_state = _state(money=50)
    growth_state.jokers = [SimpleNamespace(name="Blue Joker")]

    baseline = BuildAwareShopBoosterPolicy().recommend(
        baseline_state,
        _action("Standard Pack"),
    )
    growth = BuildAwareShopBoosterPolicy().recommend(
        growth_state,
        _action("Standard Pack"),
    )

    assert growth.option_utility > baseline.option_utility
    assert any("deck" in note.lower() and "growth" in note.lower() for note in growth.rationale)


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


def test_d8_more_realized_play_reopens_headroom_with_exact_planet_pool_odds():
    state = _state(money=50)
    state.hand_levels["FLUSH"] = 2
    state.hand_levels["FOUR_OF_A_KIND"] = 2
    state.hand_play_counts["FLUSH"] = 14

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Celestial Pack"),
    )

    assert recommendation.decision == HOLD
    assert recommendation.at_least_one_hit_probability == pytest.approx(1 / 3)
    assert any("effective Celestial headroom=1" in note for note in recommendation.rationale)


def test_d8_two_relevant_hands_use_exact_without_replacement_celestial_odds():
    state = _state(money=50)
    state.hand_play_counts["FLUSH"] = 8
    state.hand_play_counts["PAIR"] = 8

    recommendation = BuildAwareShopBoosterPolicy().recommend(
        state,
        _action("Celestial Pack"),
    )

    # Two useful Planets among nine ordinary eligible Planets, drawing three
    # without replacement: 1 - C(7, 3) / C(9, 3) = 7/12.
    assert recommendation.at_least_one_hit_probability == pytest.approx(7 / 12)
    assert any("useful=2/9" in note for note in recommendation.rationale)


def test_d8_one_hand_jumbo_celestial_uses_exact_without_replacement_odds():
    recommendation = BuildAwareShopBoosterPolicy().recommend(
        _specialized_state(money=50),
        _action("Jumbo Celestial Pack", price=6),
    )

    assert recommendation.at_least_one_hit_probability == pytest.approx(5 / 9)


def test_d8_mega_pack_has_more_option_value_than_normal_at_equal_price():
    policy = BuildAwareShopBoosterPolicy()
    state = _specialized_state(money=50)

    normal = policy.recommend(state, _action("Celestial Pack"))
    mega = policy.recommend(state, _action("Mega Celestial Pack"))

    assert mega.offer_count == 5
    assert mega.selection_count == 2
    assert mega.at_least_one_hit_probability > normal.at_least_one_hit_probability
    assert mega.option_utility > normal.option_utility


def test_d8_arcana_and_spectral_fail_closed_without_public_generation_pools():
    policy = BuildAwareShopBoosterPolicy()
    state = _state(money=50)

    arcana = policy.recommend(state, _action("Arcana Pack"))
    spectral = policy.recommend(state, _action("Mega Spectral Pack"))

    assert arcana.decision == HOLD
    assert spectral.decision == HOLD
    assert any("generation pools were not observed" in note for note in arcana.rationale)
    assert any("generation pools were not observed" in note for note in spectral.rationale)


def test_d8_threshold_mapping_is_layer_owned_and_rejects_unknown_keys():
    thresholds = BoosterAcquisitionThresholds.from_mapping(
        {"minimum_buy_advantage": 1.25}
    )
    assert thresholds.minimum_buy_advantage == pytest.approx(1.25)

    with pytest.raises(ValueError, match="unknown D8 booster threshold"):
        BoosterAcquisitionThresholds.from_mapping({"joker_threshold": 1.0})
