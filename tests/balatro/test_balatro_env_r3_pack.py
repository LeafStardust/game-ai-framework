import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.pack import PackTransitionEngine, can_skip_pack_exact, skip_pack_exact
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.juggler import JugglerJoker
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
    red_card.live_id = 10
    flat = FlatMultJoker()
    flat.live_id = 20
    state.jokers = [red_card, flat]
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


def _buffoon_choice_run(joker=None) -> HeadlessRunState:
    run = _pack_run()
    run.pack_choices = [joker or FlatMultJoker(), FlatMultJoker()]
    run.pack_choices_remaining = 1
    return run


def test_env_r3_final_buffoon_choice_adds_exact_inventory_only_joker():
    run = _buffoon_choice_run()
    before_rng = run.rng_snapshot()
    action = EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": 0})
    engine = PackTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert len(result.public.jokers) == 3
    assert type(result.public.jokers[-1]) is FlatMultJoker
    assert result.public.phase == "SHOP"
    assert result.pack_choices == []
    assert result.pack_choices_remaining == 0
    assert result.rng_snapshot() == before_rng
    assert len(run.public.jokers) == 2
    result.require_joker_order_state()


def test_env_r3_buffoon_choice_masks_resource_mutation_and_nonfinal_choice():
    run = _buffoon_choice_run(JugglerJoker())
    action = EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": 0})
    engine = PackTransitionEngine()
    assert action not in engine.legal_actions(run)

    run = _buffoon_choice_run()
    run.pack_choices_remaining = 2
    assert all(item.alias != "CHOOSE_PACK_OPTION" for item in engine.legal_actions(run))


def test_env_r3_buffoon_choice_rejects_non_buffoon_pack():
    run = _buffoon_choice_run()
    run.public.phase = "TAROT_PACK"
    assert all(
        item.alias != "CHOOSE_PACK_OPTION"
        for item in PackTransitionEngine().legal_actions(run)
    )


def test_env_r3_buffoon_choice_requires_authoritative_existing_joker_order():
    run = _buffoon_choice_run()
    del run.public.jokers[0].live_id
    del run.public.jokers[1].live_id
    run.joker_order_state = None

    assert all(
        action.alias != "CHOOSE_PACK_OPTION"
        for action in PackTransitionEngine().legal_actions(run)
    )
