import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_facing import (
    _initial_draw_creation_indices,
    clear_facing_boss_hand,
    prepare_supported_wheel_start,
    start_supported_wheel,
)
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.tactical_transition import apply_supported_tactical_discard
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.state import BalatroState


def _run(seed: str = "WHEEL") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = "The Wheel"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.discards_used = 0
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_wheel_consumes_one_keyed_rng_check_per_physically_drawn_card():
    seed = "WHEEL"
    run = _run(seed)
    before_rng = run.rng_snapshot()

    result = start_supported_wheel(run)

    expected = BalatroRNG(seed)
    expected_results = [expected.random("wheel") < (1.0 / 7.0) for _ in range(8)]

    assert run.rng_snapshot() == before_rng
    assert len(result.public.hand) == 8
    assert all(card.facing_observed for card in result.public.hand)
    assert result.rng.nodes["wheel"] == expected.nodes["wheel"]
    assert sum(card.face_down for card in result.public.hand) == sum(expected_results)


def test_env_r2_wheel_assigns_rng_results_in_physical_draw_order_before_hand_sort():
    seed = "WHEEL-PHYSICAL"
    run = _run(seed)
    prepared = prepare_supported_wheel_start(run)
    physical_indices = _initial_draw_creation_indices(prepared)

    expected_rng = BalatroRNG(seed)
    expected_by_creation_index = {
        creation_index: expected_rng.random("wheel") < (1.0 / 7.0)
        for creation_index in physical_indices
    }

    result = start_supported_wheel(run)
    order = result.require_playing_card_order()
    actual_by_creation_index = {
        index: card.face_down
        for index, card in enumerate(order)
        if id(card) in {id(hand_card) for hand_card in result.public.hand}
    }

    assert actual_by_creation_index == expected_by_creation_index


def test_env_r2_wheel_policy_observation_masks_only_rng_selected_hidden_cards():
    result = start_supported_wheel(_run("WHEEL-MASK"))
    observation = EnvStateFrame(state=result.public).observation()

    for internal, public in zip(result.public.hand, observation.hand, strict=True):
        assert public.face_down is internal.face_down
        if internal.face_down:
            assert public.rank == "?"
            assert public.suit == "?"
            assert public.live_id is None
        else:
            assert public.rank == internal.rank
            assert public.suit == internal.suit


def test_env_r2_wheel_replay_is_seed_deterministic_and_seed_sensitive():
    first = start_supported_wheel(_run("WHEEL-REPLAY"))
    second = start_supported_wheel(_run("WHEEL-REPLAY"))
    other = start_supported_wheel(_run("WHEEL-OTHER"))

    def signature(run):
        return [
            (card.rank, card.suit, card.face_down)
            for card in run.public.hand
        ]

    assert signature(first) == signature(second)
    assert first.rng_snapshot() == second.rng_snapshot()
    assert (
        signature(first) != signature(other)
        or first.rng_snapshot() != other.rng_snapshot()
    )


def test_env_r2_wheel_probability_modifier_joker_fails_closed():
    run = _run()
    run.public.jokers = [OopsAll6sJoker()]
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="unsupported identity"):
        start_supported_wheel(run)

    assert run.rng_snapshot() == before_rng
    assert run.public.phase == "BLIND_SELECT"


def test_env_r2_wheel_cleanup_flips_hidden_cards_up_without_rng():
    run = start_supported_wheel(_run("WHEEL-CLEAN"))
    before_rng = run.rng_snapshot()

    result = clear_facing_boss_hand(run)

    assert all(not card.face_down for card in result.public.hand)
    assert all(card.facing_observed for card in result.public.hand)
    assert result.rng_snapshot() == before_rng


def test_env_r4_wheel_discard_polls_each_physical_replacement_before_sort():
    run = start_supported_wheel(_run("WHEEL-DISCARD"))
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()
    order = run.require_playing_card_order()
    creation_index = {id(card): index for index, card in enumerate(order)}
    replacement_indices = [
        creation_index[id(run.draw_pile[-1])],
        creation_index[id(run.draw_pile[-2])],
    ]
    retained_facing = {
        creation_index[id(card)]: card.face_down
        for offset, card in enumerate(run.public.hand)
        if offset not in {0, 2}
    }
    expected_rng = BalatroRNG.from_snapshot(before_rng)
    expected_facing = [
        expected_rng.random("wheel") < (1.0 / 7.0)
        for _ in replacement_indices
    ]

    result = apply_supported_tactical_discard(run, (0, 2))
    result_order = result.require_playing_card_order()

    assert serialize_headless_run_state(run) == before
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert result.rng_snapshot() == expected_rng.snapshot()
    assert [
        result_order[index].face_down for index in replacement_indices
    ] == expected_facing
    assert all(result_order[index].facing_observed for index in replacement_indices)
    assert {
        index: result_order[index].face_down for index in retained_facing
    } == retained_facing


def test_env_r4_wheel_discard_masks_only_new_hidden_replacements():
    result = apply_supported_tactical_discard(
        start_supported_wheel(_run("WHEEL-DISCARD-MASK")),
        (0, 2, 4),
    )
    observation = EnvStateFrame(state=result.public).observation()

    for internal, public in zip(result.public.hand, observation.hand, strict=True):
        assert public.face_down is internal.face_down
        if internal.face_down:
            assert public.rank == "?"
            assert public.suit == "?"
            assert public.live_id is None
        else:
            assert public.rank == internal.rank
            assert public.suit == internal.suit


def test_env_r4_wheel_discard_replay_is_seed_deterministic_and_seed_sensitive():
    def signature(seed):
        result = apply_supported_tactical_discard(
            start_supported_wheel(_run(seed)),
            (0, 2, 4, 6),
        )
        return (
            tuple(
                (card.rank, card.suit, card.face_down)
                for card in result.public.hand
            ),
            result.rng_snapshot(),
        )

    assert signature("WHEEL-DISCARD-REPLAY") == signature(
        "WHEEL-DISCARD-REPLAY"
    )
    assert signature("WHEEL-DISCARD-REPLAY") != signature(
        "WHEEL-DISCARD-OTHER"
    )


def test_env_r4_wheel_discard_rejects_zone_drift_atomically():
    run = start_supported_wheel(_run("WHEEL-DISCARD-DRIFT"))
    run.draw_pile.pop()
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="draw zones"):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before
    assert run.rng_snapshot() == before_rng


def test_env_r4_wheel_discard_rejects_resource_drift_atomically():
    run = start_supported_wheel(_run("WHEEL-DISCARD-RESOURCE-DRIFT"))
    run.public.hand_size += 1
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()

    with pytest.raises(
        HeadlessTransitionError,
        match="ordinary Red Deck resource state",
    ):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before
    assert run.rng_snapshot() == before_rng


def test_env_r4_wheel_play_reveals_played_cards_and_polls_replacements():
    run = start_supported_wheel(_run("WHEEL-PLAY"))
    before = serialize_headless_run_state(run)
    order = run.require_playing_card_order()
    creation_index = {id(card): index for index, card in enumerate(order)}
    replacement_indices = [
        creation_index[id(run.draw_pile[-1])],
        creation_index[id(run.draw_pile[-2])],
    ]
    retained_facing = {
        creation_index[id(card)]: card.face_down
        for offset, card in enumerate(run.public.hand)
        if offset not in {0, 1}
    }
    expected_rng = BalatroRNG.from_snapshot(run.rng_snapshot())
    expected_facing = [
        expected_rng.random("wheel") < (1.0 / 7.0)
        for _ in replacement_indices
    ]

    result = apply_supported_ordinary_play(run, (0, 1))
    result_order = result.require_playing_card_order()

    assert serialize_headless_run_state(run) == before
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == result.public.hand_size == 8
    assert all(not card.face_down for card in result.public.discard_pile[-2:])
    assert [
        result_order[index].face_down for index in replacement_indices
    ] == expected_facing
    assert result.rng_snapshot() == expected_rng.snapshot()
    assert {
        index: result_order[index].face_down for index in retained_facing
    } == retained_facing


def test_env_r4_wheel_play_accepts_authoritative_hidden_discard_history():
    run = start_supported_wheel(_run("WHEEL-HIDDEN-DISCARD-PLAY"))
    run.public.hand[0].face_down = True
    run.public.hand[0].facing_observed = True
    discarded = apply_supported_tactical_discard(run, (0,))

    assert discarded.public.discard_pile[-1].face_down is True
    assert discarded.public.discard_pile[-1].facing_observed is True

    result = apply_supported_ordinary_play(discarded, (0,))

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.discard_pile[0].face_down is True
    assert result.public.discard_pile[0].facing_observed is True


@pytest.mark.parametrize("zone", ["deck", "discard_pile"])
def test_env_r4_wheel_play_rejects_unowned_hidden_zone_state_atomically(zone):
    run = start_supported_wheel(_run(f"WHEEL-HIDDEN-ZONE-{zone}"))
    if zone == "discard_pile":
        run = apply_supported_tactical_discard(run, (0,))
    card = getattr(run.public, zone)[0]
    card.face_down = True
    card.facing_observed = zone == "deck"
    before = serialize_headless_run_state(run)

    with pytest.raises(
        HeadlessTransitionError,
        match="outside the current hand/discard zones",
    ):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
