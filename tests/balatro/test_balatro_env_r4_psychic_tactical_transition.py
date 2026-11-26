import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.tactical_transition import apply_supported_tactical_discard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.splash import SplashJoker
from games.balatro.jokers.supernova import SupernovaJoker
from games.balatro.state import BalatroState


def _psychic_run(*, seed="R4-PSYCHIC-DISCARD"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.round = 2
    state.blind = Blind(BlindType.BOSS, requirement=600, reward=5)
    state.boss_name = "The Psychic"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_start_inert_boss(
        HeadlessRunState(public=state, seed=seed)
    )


def test_env_r4_psychic_discard_is_ordinary_and_refills_full_hand():
    run = _psychic_run()
    before_rng = run.rng_snapshot()

    result = apply_supported_tactical_discard(run, (0, 2))

    assert len(run.public.hand) == run.public.hand_size == 8
    assert run.public.discards_remaining == 3
    assert run.public.discards_used == 0
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert result.public.score == 0
    assert result.public.hands_remaining == 4
    assert result.rng_snapshot() == before_rng


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("boss_hands_sub", 1),
        ("boss_discards_sub", 1),
        ("boss_hand_size_sub", 1),
    ],
)
def test_env_r4_psychic_discard_rejects_private_resource_adjustments_atomically(
    field,
    value,
):
    run = _psychic_run(seed=f"R4-PSYCHIC-DISCARD-{field}")
    setattr(run, field, value)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="ordinary Red Deck resource"):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_psychic_discard_rejects_inactive_or_modified_blind():
    disabled = _psychic_run(seed="R4-PSYCHIC-DISCARD-DISABLED")
    disabled.public.blind.disabled = True
    with pytest.raises(HeadlessTransitionError, match="active Boss"):
        apply_supported_tactical_discard(disabled, (0,))

    modified = _psychic_run(seed="R4-PSYCHIC-DISCARD-MODIFIED")
    modified.public.blind.modifiers = {"extra": True}
    with pytest.raises(HeadlessTransitionError, match="additional blind modifiers"):
        apply_supported_tactical_discard(modified, (0,))

    tagged = _psychic_run(seed="R4-PSYCHIC-DISCARD-TAGGED")
    tagged.public.blind.tag_key = "tag_double"
    with pytest.raises(HeadlessTransitionError, match="additional blind modifiers"):
        apply_supported_tactical_discard(tagged, (0,))


def test_env_r4_psychic_discard_rejects_wrong_hand_size_and_jokers():
    wrong_size = _psychic_run(seed="R4-PSYCHIC-DISCARD-SIZE")
    wrong_size.public.hand_size = 9
    with pytest.raises(HeadlessTransitionError, match="ordinary Red Deck resource"):
        apply_supported_tactical_discard(wrong_size, (0,))

    joker = _psychic_run(seed="R4-PSYCHIC-DISCARD-JOKER")
    joker.public.jokers = [object()]
    with pytest.raises(HeadlessTransitionError, match="Joker discard callbacks"):
        apply_supported_tactical_discard(joker, (0,))


def test_env_r4_splash_respects_psychic_played_card_count():
    from games.balatro.env.play_transition import apply_supported_ordinary_play

    run = _psychic_run()
    joker = SplashJoker()
    joker.center = "j_splash"
    run.public.jokers = [joker]

    short = apply_supported_ordinary_play(run, (0, 1, 3, 4))
    full = apply_supported_ordinary_play(run, (0, 1, 2, 3, 4))

    assert short.public.score == 0
    assert full.public.score == 120
    assert short.public.last_played_hand == full.public.last_played_hand == "PAIR"


def test_env_r4_supernova_counts_a_prior_boss_debuffed_play():
    from games.balatro.env.play_transition import apply_supported_ordinary_play

    run = _psychic_run()
    run.public.hand_play_counts["HIGH_CARD"] = 3
    joker = SupernovaJoker()
    joker.center = "j_supernova"
    run.public.jokers = [joker]

    blocked = apply_supported_ordinary_play(run, (0, 1, 2, 3))
    assert blocked.public.score == 0
    assert blocked.public.last_played_hand == "HIGH_CARD"
    assert blocked.public.hand_play_counts["HIGH_CARD"] == 4

    accepted = apply_supported_ordinary_play(blocked, (0, 1, 2, 3, 5))

    assert accepted.public.last_played_hand == "HIGH_CARD"
    assert accepted.public.hand_play_counts["HIGH_CARD"] == 5
    assert accepted.public.round_hand_play_counts["HIGH_CARD"] == 2
    assert accepted.public.score == 90
