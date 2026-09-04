import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.amber_acorn import apply_amber_acorn_order_effect
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.state import BalatroState


def _run(count=5):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.boss_name = "Amber Acorn"
    state.blind = Blind(BlindType.BOSS, 100000)
    types = [FlatMultJoker, JollyJoker, SlyJoker, ZanyJoker, WilyJoker]
    state.jokers = []
    for live_id, joker_type in enumerate(types[:count], start=1):
        joker = joker_type()
        joker.live_id = live_id
        state.jokers.append(joker)
    return HeadlessRunState(public=state, seed="AMBER-TEST")


def _ids(run):
    return [joker.live_id for joker in run.public.jokers]


def test_env_r2_amber_order_effect_installs_exact_hidden_physical_order_and_rng():
    run = _run()

    result = apply_amber_acorn_order_effect(run)

    assert _ids(result) == [4, 5, 2, 1, 3]
    assert result.rng.nodes["aajk"] == 0.991074513307
    assert _ids(run) == [1, 2, 3, 4, 5]
    assert "aajk" not in run.rng.nodes


def test_env_r2_amber_order_effect_one_joker_changes_no_rng_order():
    run = _run(1)
    before = run.rng_snapshot()

    result = apply_amber_acorn_order_effect(run)

    assert _ids(result) == [1]
    assert result.rng_snapshot() == before


def test_env_r2_amber_order_effect_fails_closed_without_multi_joker_creation_ids():
    run = _run(2)
    for joker in run.public.jokers:
        joker.live_id = None

    with pytest.raises(HeadlessTransitionError, match="creation order is unavailable"):
        apply_amber_acorn_order_effect(run)


def test_env_r2_amber_order_effect_rejects_wrong_or_disabled_blind():
    run = _run(2)
    run.public.boss_name = "Verdant Leaf"
    with pytest.raises(HeadlessTransitionError, match="requires Amber Acorn"):
        apply_amber_acorn_order_effect(run)

    run = _run(2)
    run.public.blind.disabled = True
    with pytest.raises(HeadlessTransitionError, match="active blind state"):
        apply_amber_acorn_order_effect(run)
