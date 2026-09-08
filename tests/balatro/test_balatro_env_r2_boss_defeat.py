import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_defeat import defeat_supported_boss
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def _boss_run(name: str) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "ROUND_EVAL"
    state.boss_name = name
    state.blind_is_boss = True
    state.blind = Blind(BlindType.BOSS, requirement=100, reward=5)
    return HeadlessRunState(public=state, seed="BOSSDEFEAT")


def test_env_r2_boss_defeat_clears_eye_public_mutable_blind_state():
    run = _boss_run("The Eye")
    run.public.boss_blind_state_observed = True
    run.public.boss_blind_hands = {"PAIR", "FLUSH"}

    result = defeat_supported_boss(run)

    assert result.public.boss_blind_state_observed is False
    assert result.public.boss_blind_hands == set()
    assert result.public.boss_blind_only_hand is None
    assert run.public.boss_blind_hands == {"PAIR", "FLUSH"}


def test_env_r2_boss_defeat_restores_manacle_hand_size_without_drawing():
    run = _boss_run("The Manacle")
    run.public.hand_size = 7
    run.boss_hand_size_sub = 1
    before_hand = list(run.public.hand)
    before_draw = list(run.draw_pile)

    result = defeat_supported_boss(run)

    assert result.public.hand_size == 8
    assert result.boss_hand_size_sub is None
    assert result.public.hand == before_hand
    assert result.draw_pile == before_draw
    assert run.public.hand_size == 7
    assert run.boss_hand_size_sub == 1


def test_env_r2_boss_defeat_water_and_needle_drop_stored_round_only_reversals():
    water = _boss_run("The Water")
    water.boss_discards_sub = 3
    water.public.discards_remaining = 0

    water_result = defeat_supported_boss(water)

    assert water_result.boss_discards_sub is None
    assert water_result.public.discards_remaining == 0

    needle = _boss_run("The Needle")
    needle.boss_hands_sub = 3
    needle.public.hands_remaining = 1

    needle_result = defeat_supported_boss(needle)

    assert needle_result.boss_hands_sub is None
    assert needle_result.public.hands_remaining == 1


def test_env_r2_boss_defeat_clears_static_suit_debuffs():
    run = _boss_run("The Goad")
    for card in run.public.deck:
        card.debuffed = card.suit == "Spades"

    result = defeat_supported_boss(run)

    assert all(not card.debuffed for card in result.require_playing_card_order())
    assert sum(card.debuffed for card in run.require_playing_card_order()) == 13


def test_env_r2_boss_defeat_clears_cerulean_forced_selection_from_permanent_cards():
    run = _boss_run("Cerulean Bell")
    run.public.deck[0].forced_selection = True

    result = defeat_supported_boss(run)

    assert all(not card.forced_selection for card in result.require_playing_card_order())
    assert run.public.deck[0].forced_selection is True


def test_env_r2_amber_defeat_preserves_physical_joker_order_without_rng():
    run = _boss_run("Amber Acorn")
    first = FlatMultJoker(1)
    second = FlatMultJoker(2)
    third = FlatMultJoker(3)
    run.public.jokers = [third, first, second]
    before_rng = run.rng_snapshot()
    before_order = [joker.mult for joker in run.public.jokers]

    result = defeat_supported_boss(run)

    assert [joker.mult for joker in result.public.jokers] == before_order
    assert result.rng_snapshot() == before_rng
    assert result.public.boss_blind_state_observed is False
    assert result.public.boss_blind_hands == set()
    assert result.public.boss_blind_only_hand is None
    assert [joker.mult for joker in run.public.jokers] == before_order


def test_env_r2_verdant_defeat_clears_all_card_debuffs_without_disabling_blind():
    run = _boss_run("Verdant Leaf")
    for card in run.require_playing_card_order():
        card.debuffed = True

    result = defeat_supported_boss(run)

    assert all(not card.debuffed for card in result.require_playing_card_order())
    assert result.public.blind.disabled is False
    assert all(card.debuffed for card in run.require_playing_card_order())


def test_env_r2_crimson_defeat_clears_joker_debuff_and_installs_blank_blind_prepped_state():
    run = _boss_run("Crimson Heart")
    joker = FlatMultJoker(3)
    joker.debuffed = True
    run.public.jokers = [joker]
    setattr(run.public.blind, "prepped", False)
    before_rng = run.rng_snapshot()

    result = defeat_supported_boss(run)

    assert result.public.jokers[0].debuffed is False
    assert getattr(result.public.blind, "prepped", False) is True
    assert result.public.blind.disabled is False
    assert result.rng_snapshot() == before_rng
    assert run.public.jokers[0].debuffed is True
    assert getattr(run.public.blind, "prepped", False) is False


@pytest.mark.parametrize("boss_name", ["The House", "The Wheel", "The Mark", "The Fish"])
def test_env_r2_facing_state_boss_normal_defeat_is_state_only_and_rng_neutral(boss_name):
    run = _boss_run(boss_name)
    run.public.boss_blind_state_observed = True
    run.public.boss_blind_hands = {"PAIR"}
    before_rng = run.rng_snapshot()
    before_order = list(run.require_playing_card_order())

    result = defeat_supported_boss(run)

    # Vanilla normal Blind:defeat does not borrow Blind:disable's explicit
    # House/Wheel/Mark/Fish hand-card flip cleanup. The current public model has
    # no facing field, so the exact normal-defeat consequence at this boundary is
    # only removal of the defeated Blind's public mutable state.
    assert result.public.boss_blind_state_observed is False
    assert result.public.boss_blind_hands == set()
    assert result.public.boss_blind_only_hand is None
    assert result.require_playing_card_order() == before_order
    assert result.rng_snapshot() == before_rng
    assert run.public.boss_blind_state_observed is True
    assert run.public.boss_blind_hands == {"PAIR"}


def test_env_r2_disabled_supported_boss_does_not_reapply_inverse_cleanup():
    run = _boss_run("The Manacle")
    run.public.blind.disabled = True
    run.public.hand_size = 8
    run.boss_hand_size_sub = None

    result = defeat_supported_boss(run)

    assert result.public.hand_size == 8
    assert result.boss_hand_size_sub is None


def test_env_r2_boss_defeat_rejects_unsupported_or_wrong_boundary():
    run = _boss_run("Unsupported Boss")
    with pytest.raises(HeadlessTransitionError, match="not exactly owned"):
        defeat_supported_boss(run)

    run = _boss_run("The Eye")
    run.public.phase = "SELECTING_HAND"
    with pytest.raises(HeadlessTransitionError, match="ROUND_EVAL"):
        defeat_supported_boss(run)
