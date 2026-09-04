from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import prepare_supported_verdant_leaf_start
from games.balatro.env.transition import HeadlessRunState
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.state import BalatroState


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 8
    state.round = 23
    state.blind = Blind(BlindType.BOSS, 100000)
    state.boss_name = "Verdant Leaf"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.jokers = [ChicotJoker()]
    return HeadlessRunState(public=state, seed="CHICOT-VERDANT")


def test_env_r2_chicot_disables_verdant_after_start_debuff_and_clears_all_cards():
    run = _run()
    before_rng = run.rng_snapshot()

    result = prepare_supported_verdant_leaf_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.blind.disabled is True
    assert all(not card.debuffed for card in result.require_playing_card_order())
    # Chicot/Verdant pre-deal cleanup itself consumes no RNG; round-start deal
    # has not occurred yet at this preparation boundary.
    assert result.rng_snapshot() == before_rng

    # Input isolation: the source state remains an unstarted, non-debuffed Boss.
    assert run.public.phase == "BLIND_SELECT"
    assert not getattr(run.public.blind, "disabled", False)
    assert all(not card.debuffed for card in run.require_playing_card_order())


def test_env_r2_chicot_verdant_cleanup_happens_after_verdant_start_debuff():
    run = _run()

    result = prepare_supported_verdant_leaf_start(run)

    # If Chicot were applied before Blind:set_blind/Verdant debuffing, the
    # start helper would reject the disabled Boss or leave cards debuffed. The
    # final clean disabled state pins the vanilla order: set_blind debuff first,
    # queued Chicot Blind:disable second.
    assert result.public.blind.disabled is True
    assert not any(card.debuffed for card in result.require_playing_card_order())
