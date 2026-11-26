from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.actions import EnvAction
from games.balatro.env.blind_progression import (
    BlindProgressionState,
    activate_selected_blind_progression,
)
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_SCHEMA
from games.balatro.env.ordinary_round_resolution import (
    resolve_supported_ordinary_round,
)
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.shop_inventory_generation import (
    first_shop_from_retained_progression,
)
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.tactical_transition import apply_planned_tactical_step
from games.balatro.env.transition import HeadlessTransitionError, ShopTransitionEngine
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.runner import RunnerJoker


class _ClearingTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(
            action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]])
        )


def _cleared_ordinary_blind(blind_type=BlindType.SMALL):
    run = pristine_red_white_reset("ORDINARY-ROUND")
    if blind_type is BlindType.BIG:
        run.public.round = 1
        run.public.blind = Blind(BlindType.BIG, requirement=450, reward=4)
        run.blind_progression_state = BlindProgressionState(
            small_status="Defeated",
            big_status="Select",
            boss_status="Upcoming",
            blind_on_deck="Big",
            blind_ante=1,
        )
    run.public.hand_levels["HIGH_CARD"] = 1000
    run = activate_selected_blind_progression(run)
    run = select_blind_exact(run)
    return apply_planned_tactical_step(run, _ClearingTacticalPolicy())


def test_env_ppo_ordinary_round_resolution_composes_progression_then_cashout():
    cleared = _cleared_ordinary_blind()
    before_rng = cleared.rng_snapshot()

    result = resolve_supported_ordinary_round(
        cleared,
        cleared.require_blind_progression_state(),
    )

    assert cleared.public.phase == "ROUND_EVAL"
    assert cleared.public.money == 4
    assert cleared.blind_progression_state.small_status == "Current"
    assert cleared.rng_snapshot() == before_rng
    assert result.progression.small_status == "Defeated"
    assert result.progression.blind_on_deck == "Small"
    assert result.run.blind_progression_state == result.progression
    assert result.run.public.phase == "SHOP"
    assert result.run.public.shop_active is True
    assert result.run.public.money == 10
    assert result.run.public.score == 0
    assert result.run.public.hands_remaining == 4
    assert result.run.public.discards_remaining == 3
    assert len(result.run.draw_pile) == 52
    assert result.run.rng_snapshot() != before_rng
    assert "cashout1" in result.run.rng_snapshot()["nodes"]
    assert result.run.public.shop_jokers == []
    assert result.run.public.shop_consumables == []
    assert result.run.public.shop_boosters == []
    assert result.run.public.shop_vouchers == []
    assert first_shop_from_retained_progression(result.run) is True


def test_env_ppo_ordinary_round_resolution_supports_big_blind_exactly():
    cleared = _cleared_ordinary_blind(BlindType.BIG)

    result = resolve_supported_ordinary_round(
        cleared,
        cleared.require_blind_progression_state(),
    )

    assert cleared.public.round == 2
    assert result.progression.small_status == "Defeated"
    assert result.progression.big_status == "Defeated"
    assert result.progression.blind_on_deck == "Big"
    assert result.run.public.money == 11
    assert result.run.public.phase == "SHOP"
    assert first_shop_from_retained_progression(result.run) is False


def test_env_ppo_ordinary_round_resolution_rejects_parallel_progression_drift():
    cleared = _cleared_ordinary_blind()
    conflicting = BlindProgressionState(
        small_status="Defeated",
        big_status="Upcoming",
        boss_status="Upcoming",
        blind_on_deck="Small",
        blind_ante=1,
    )

    with pytest.raises(ValueError, match="conflicts with retained"):
        resolve_supported_ordinary_round(cleared, conflicting)


def test_env_ppo_ordinary_round_resolution_rejects_nonordinary_blind():
    cleared = _cleared_ordinary_blind()
    cleared.public.blind = None

    with pytest.raises(HeadlessTransitionError, match="Small or Big"):
        resolve_supported_ordinary_round(
            cleared,
            cleared.require_blind_progression_state(),
        )


def test_env_ppo_runner_grows_before_scoring_and_persists_through_next_blind():
    run = pristine_red_white_reset("RUNNER-4")
    joker = RunnerJoker()
    joker.center = "j_runner"
    run.public.jokers = [joker]
    run.public.hand_levels["STRAIGHT"] = 2
    run = select_blind_exact(activate_selected_blind_progression(run))
    indices = (1, 3, 4, 5, 6)
    assert [run.public.hand[i].rank for i in indices] == ["7", "6", "5", "4", "3"]

    cleared = apply_supported_ordinary_play(run, indices)

    assert cleared.public.phase == "ROUND_EVAL"
    assert cleared.public.score == 700
    assert run.public.jokers[0].chips == 0
    assert cleared.public.jokers[0].chips == 15
    shop = resolve_supported_ordinary_round(
        cleared, cleared.require_blind_progression_state()
    ).run
    observation = EnvStateFrame(shop.public).encoded_observation()
    chip_index = PUBLIC_OBSERVATION_SCHEMA.feature_names.index("jokers.0.chips")
    assert observation.values[chip_index] == 15.0

    next_blind = ShopTransitionEngine().step(shop, EnvAction.from_alias("END_SHOP"))
    dealt = select_blind_exact(activate_selected_blind_progression(next_blind))
    assert dealt.public.hand[0].rank == "A"
    result = apply_supported_ordinary_play(dealt, (0,))

    assert result.public.score == 31
    assert result.public.jokers[0].chips == 15


def test_env_ppo_green_keeps_mult_visible_across_rounds():
    run = pristine_red_white_reset("ORDINARY-ROUND")
    joker = GreenJoker()
    joker.center = "j_green_joker"
    joker.mult = 3
    run.public.jokers = [joker]
    run.public.hand_levels["HIGH_CARD"] = 1000
    dealt = select_blind_exact(activate_selected_blind_progression(run))
    cleared = apply_supported_ordinary_play(dealt, (0,))
    shop = resolve_supported_ordinary_round(
        cleared, cleared.require_blind_progression_state()
    ).run

    observation = EnvStateFrame(shop.public).encoded_observation()
    mult_index = PUBLIC_OBSERVATION_SCHEMA.feature_names.index("jokers.0.mult")
    assert observation.values[mult_index] == 4.0
    next_blind = ShopTransitionEngine().step(shop, EnvAction.from_alias("END_SHOP"))
    dealt = select_blind_exact(activate_selected_blind_progression(next_blind))
    assert dealt.public.jokers[0].mult == 4
    assert apply_supported_ordinary_play(dealt, (0,)).public.jokers[0].mult == 5
