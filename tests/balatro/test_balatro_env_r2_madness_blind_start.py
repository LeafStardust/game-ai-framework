import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import prepare_supported_nonboss_blind_start
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.round_lifecycle import apply_supported_setting_blind_effects
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.madness import MadnessJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.state import BalatroState


def _run(jokers, *, blind=BlindType.SMALL, seed=4):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.blind = Blind(blind, 300)
    state.money = 7
    state.jokers = jokers
    # Physical and creation order deliberately differ.
    for index, joker in enumerate(reversed(jokers)):
        joker.live_id = index
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_madness_targets_the_physical_joker_order_with_retained_rng():
    madness = MadnessJoker()
    first, last = FlatMultJoker(), JollyJoker()
    run = _run([madness, first, last])
    expected = BalatroRNG(4)
    assert expected.pseudorandom_element_index(2, "madness") == 0

    result = apply_supported_setting_blind_effects(run)

    assert [type(joker) for joker in result.public.jokers] == [MadnessJoker, JollyJoker]
    assert result.public.jokers[0].x_mult == 1.5
    assert result.rng_snapshot() == expected.snapshot()
    assert result.public.money == run.public.money == 7
    assert run.public.jokers == [madness, first, last]
    assert madness.x_mult == 1
    assert run.rng.nodes == {}


def test_env_r2_madness_ignores_the_earlier_queued_target_during_blind_start():
    run = _run([MadnessJoker(), FlatMultJoker(), MadnessJoker(), JollyJoker()], seed=41)
    expected = BalatroRNG(41)
    assert expected.pseudorandom_element_index(3, "madness") == 0
    assert expected.pseudorandom_element_index(2, "madness") == 1

    result = apply_supported_setting_blind_effects(run)

    assert [joker.x_mult for joker in result.public.jokers] == [1.5, 1.5]
    assert result.rng_snapshot() == expected.snapshot()
    assert len(run.public.jokers) == 4


@pytest.mark.parametrize(("blind", "debuffed", "x_mult"), [
    (BlindType.SMALL, False, 1.5),
    (BlindType.BIG, False, 1.5),
    (BlindType.BOSS, False, 1.0),
    (BlindType.SMALL, True, 1.0),
])
def test_env_r2_madness_grows_without_a_draw_if_its_only_neighbor_is_eternal(
    blind, debuffed, x_mult
):
    madness = MadnessJoker()
    madness.debuffed = debuffed
    eternal = FlatMultJoker()
    eternal.eternal = True
    run = _run([madness, eternal], blind=blind)

    result = apply_supported_setting_blind_effects(run)

    assert result.public.jokers[0].x_mult == x_mult
    assert len(result.public.jokers) == 2
    assert result.rng_snapshot() == run.rng_snapshot()


def test_env_r2_madness_unowned_resource_removal_is_atomic():
    madness = MadnessJoker()
    run = _run([madness, StuntmanJoker()])
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="destruction inverse"):
        apply_supported_setting_blind_effects(run)

    assert madness.x_mult == 1
    assert len(run.public.jokers) == 2
    assert run.rng_snapshot() == before


def test_env_r2_madness_removing_juggler_deals_at_old_capacity_once():
    run = _run([MadnessJoker(), JugglerJoker()])
    run.public.hand_size = 9
    baseline = _run([JugglerJoker()])
    baseline.public.hand_size = 9
    expected = deal_supported_round_start(prepare_supported_nonboss_blind_start(baseline))

    prepared = prepare_supported_nonboss_blind_start(run)
    result = deal_supported_round_start(prepared)

    assert prepared.opening_draw_capacity == 9
    assert result.opening_draw_capacity is None
    assert result.public.hand_size == 8
    assert len(result.public.hand) == 9
    assert result.public.hand == expected.public.hand
    assert result.public.deck == expected.public.deck
    assert [type(joker) for joker in result.public.jokers] == [MadnessJoker]
    assert result.public.money == run.public.money
    assert len(run.public.hand) == 0 and run.public.hand_size == 9


def test_env_r2_madness_opening_capacity_round_trips_before_the_deal():
    run = _run([])
    run.public.phase = "DRAW_TO_HAND"
    run.opening_draw_capacity = 9
    restored = HeadlessRunState.restore(run.serialize())

    assert restored.opening_draw_capacity == 9
    assert len(deal_supported_round_start(restored).public.hand) == 9


@pytest.mark.parametrize(("bonus", "current"), [(0, 3), (-4, 0)])
def test_env_r2_madness_removing_drunkard_reduces_both_discard_allowances(bonus, current):
    run = _run([MadnessJoker(), DrunkardJoker()])
    run.public.round_reset_discards = 4
    run.round_bonus_discards = bonus

    result = deal_supported_round_start(prepare_supported_nonboss_blind_start(run))

    assert result.public.round_reset_discards == 3
    assert result.public.discards_remaining == current
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.public.money == run.public.money
