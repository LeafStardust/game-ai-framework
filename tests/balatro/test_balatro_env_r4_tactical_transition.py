import pytest

from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.tactical_transition import apply_supported_tactical_discard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _dealt_run(*, seed="R4-DISCARD"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.discards_remaining = 3
    state.discards_used = 0
    run = HeadlessRunState(public=state, seed=seed)
    return deal_supported_round_start(run)


def _card_signature(card):
    return (
        card.rank,
        card.suit,
        card.enhancement,
        card.edition,
        card.seal,
        card.permanent_bonus,
    )


def _state_signature(run):
    return (
        tuple(_card_signature(card) for card in run.public.hand),
        tuple(_card_signature(card) for card in run.public.deck),
        tuple(_card_signature(card) for card in run.public.discard_pile),
        tuple(_card_signature(card) for card in run.draw_pile),
        tuple(_card_signature(card) for card in run.discard_pile),
        run.public.discards_remaining,
        run.public.discards_used,
        run.rng_snapshot(),
    )


def test_env_r4_baseline_discard_moves_in_visible_order_updates_counters_and_refills():
    run = _dealt_run()
    selected = [_card_signature(run.public.hand[index]) for index in (1, 3)]
    rng_before = run.rng_snapshot()

    result = apply_supported_tactical_discard(run, (3, 1))

    assert [_card_signature(card) for card in result.public.discard_pile[-2:]] == selected
    assert [_card_signature(card) for card in result.discard_pile[-2:]] == selected
    assert len(result.public.hand) == result.public.hand_size == 8
    assert len(result.public.deck) == 42
    assert len(result.draw_pile) == 42
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert result.public.phase == "SELECTING_HAND"
    assert result.rng_snapshot() == rng_before

    # Transition ownership is copy-on-write.
    assert len(run.public.hand) == 8
    assert len(run.public.deck) == 44
    assert run.public.discard_pile == []
    assert run.discard_pile == []
    assert run.public.discards_remaining == 3
    assert run.public.discards_used == 0


def test_env_r4_baseline_discard_is_replay_deterministic_for_same_seed():
    left = apply_supported_tactical_discard(_dealt_run(seed="REPLAY"), (0, 2, 4))
    right = apply_supported_tactical_discard(_dealt_run(seed="REPLAY"), (4, 0, 2))

    assert _state_signature(left) == _state_signature(right)


@pytest.mark.parametrize(
    "indices, message",
    [
        ((), "1 to 5"),
        ((0, 0), "distinct"),
        ((-1,), "outside"),
        ((8,), "outside"),
        ((True,), "exact integers"),
    ],
)
def test_env_r4_baseline_discard_rejects_invalid_visible_indices(indices, message):
    run = _dealt_run()
    before = _state_signature(run)

    with pytest.raises(HeadlessTransitionError, match=message):
        apply_supported_tactical_discard(run, indices)

    assert _state_signature(run) == before


def test_env_r4_baseline_discard_fails_closed_on_purple_seal_generation():
    run = _dealt_run()
    run.public.hand[0].seal = "Purple"
    before = _state_signature(run)

    with pytest.raises(HeadlessTransitionError, match="Purple Seal"):
        apply_supported_tactical_discard(run, (0,))

    assert _state_signature(run) == before


def test_env_r4_baseline_discard_fails_closed_on_boss_or_joker_callbacks():
    boss_run = _dealt_run()
    boss_run.public.boss_name = "The Water"
    with pytest.raises(HeadlessTransitionError, match="boss discard callbacks"):
        apply_supported_tactical_discard(boss_run, (0,))

    joker_run = _dealt_run()
    # The first slice intentionally rejects the whole Joker callback surface,
    # including otherwise inert identities, until exact discard dispatch owns it.
    joker_run.public.jokers = [object()]
    with pytest.raises(HeadlessTransitionError, match="Joker discard callbacks"):
        apply_supported_tactical_discard(joker_run, (0,))


def test_env_r4_baseline_discard_requires_authoritative_private_draw_zone():
    run = _dealt_run()
    run.draw_pile.pop()

    with pytest.raises(HeadlessTransitionError, match="private/public draw zones"):
        apply_supported_tactical_discard(run, (0,))
