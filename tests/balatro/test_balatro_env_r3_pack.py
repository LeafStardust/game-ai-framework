import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.pack import PackTransitionEngine, can_skip_pack_exact, skip_pack_exact
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.red_card import RedCardJoker
from games.balatro.state import BalatroState


def _pack_run(*, return_phase: str = "SHOP") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BUFFOON_PACK"
    state.shop_active = False
    red_card = RedCardJoker()
    red_card.mult = 6
    state.jokers = [red_card, FlatMultJoker()]
    return HeadlessRunState(
        public=state,
        seed="SKIP-PACK",
        pack_choices=[{"center": "j_joker"}, {"center": "j_misprint"}],
        pack_return_phase=return_phase,
    )


@pytest.mark.parametrize("return_phase", ["SHOP", "BLIND_SELECT"])
def test_env_r3_skip_pack_applies_red_card_and_returns_to_exact_origin(return_phase):
    run = _pack_run(return_phase=return_phase)
    before_rng = run.rng_snapshot()
    assert can_skip_pack_exact(run)
    result = skip_pack_exact(run)
    assert result.public.phase == return_phase
    assert result.public.shop_active is (return_phase == "SHOP")
    assert result.public.jokers[0].mult == 9
    assert result.pack_choices == []
    assert result.pack_return_phase is None
    assert result.rng_snapshot() == before_rng
    assert run.public.phase == "BUFFOON_PACK"
    assert run.public.jokers[0].mult == 6
    assert len(run.pack_choices) == 2


def test_env_r3_pack_engine_masks_and_executes_exact_skip():
    run = _pack_run()
    action = EnvAction.from_alias("SKIP_PACK")
    engine = PackTransitionEngine()
    assert engine.legal_actions(run) == (action,)
    assert engine.step(run, action).public.phase == "SHOP"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda run: setattr(run.public, "phase", "SHOP"), "open-pack phase"),
        (lambda run: setattr(run, "pack_return_phase", None), "return phase"),
        (lambda run: run.pack_choices.clear(), "offered choices"),
        (lambda run: run.public.hand.append(object()), "hand-to-deck"),
        (lambda run: setattr(run.public, "shop_active", True), "active main shop"),
    ],
)
def test_env_r3_skip_pack_fails_closed_on_inexact_pack_state(mutation, message):
    run = _pack_run()
    mutation(run)
    assert not can_skip_pack_exact(run)
    with pytest.raises(HeadlessTransitionError, match=message):
        skip_pack_exact(run)


def test_env_r3_skip_pack_rejects_non_run_input():
    assert not can_skip_pack_exact(object())
    with pytest.raises(TypeError, match="HeadlessRunState"):
        skip_pack_exact(object())
