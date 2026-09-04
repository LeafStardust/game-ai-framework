from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.serpent_draw import draw_serpent_post_action_cards
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _serpent_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = "The Serpent"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="SERPENT-COMPOSED")


def test_env_r2_serpent_start_then_post_play_draw_is_exactly_composable():
    started = start_supported_start_inert_boss(_serpent_run())

    assert started.public.phase == "SELECTING_HAND"
    assert len(started.public.hand) == started.public.hand_size
    before_rng = started.rng_snapshot()

    played = started.public.hand.pop()
    started.played_pile.append(played)
    started.public.round_hand_play_counts["PAIR"] = 1
    before_draw_hand = len(started.public.hand)
    before_draw_deck = len(started.draw_pile)

    result = draw_serpent_post_action_cards(started)

    assert len(result.public.hand) == before_draw_hand + 3
    assert len(result.draw_pile) == before_draw_deck - 3
    assert result.rng_snapshot() == before_rng
    assert started.rng_snapshot() == before_rng
