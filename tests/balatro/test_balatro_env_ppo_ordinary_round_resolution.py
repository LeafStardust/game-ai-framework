from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_progression import (
    BlindProgressionState,
    activate_selected_blind_progression,
)
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.ordinary_round_resolution import (
    resolve_supported_ordinary_round,
)
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.tactical_transition import apply_planned_tactical_step
from games.balatro.env.transition import HeadlessTransitionError


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
