"""Canonical concrete backend for deterministic Red/White PPO episodes."""

from __future__ import annotations

from typing import Any

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.actions import EnvAction
from games.balatro.env.blind_progression import (
    BlindProgressionState,
    activate_selected_blind_progression,
)
from games.balatro.env.ordinary_round_resolution import (
    resolve_supported_ordinary_round,
)
from games.balatro.env.ppo_contract import PPO_REWARD_CONTRACT
from games.balatro.env.ppo_training_profile import (
    PPO_TRAINING_PROFILE,
    initialize_pristine_ppo_boss_authority,
    initialize_pristine_ppo_generation_authority,
)
from games.balatro.env.select_blind import can_select_blind_exact, select_blind_exact
from games.balatro.env.serialization import (
    restore_headless_run_state,
    serialize_headless_run_state,
)
from games.balatro.env.skip_blind import can_skip_blind_exact, skip_blind_exact
from games.balatro.env.shop_inventory_generation import (
    generate_progression_normal_shop_inventory,
)
from games.balatro.env.state import BackendStep, EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.tactical_transition import apply_planned_tactical_step
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.state import BalatroState


PPO_HEADLESS_BACKEND_SCHEMA = "balatro-red-white-ppo-headless-backend-v2"
_MAX_TACTICAL_ACTIONS = 4096


def sparse_terminal_reward(status: RunStatus) -> float:
    """Frozen PPO reward owner: zero running, -1 loss, +1 Ante-8 win."""
    if not isinstance(status, RunStatus):
        raise TypeError("reward status must be RunStatus")
    if status is RunStatus.RUNNING:
        return 0.0
    if status is RunStatus.LOSS:
        return -1.0
    if status is RunStatus.ANTE_8_WIN:
        return 1.0
    raise HeadlessTransitionError("unsupported terminal reward status")


def pristine_red_white_reset(seed: str | int) -> HeadlessRunState:
    """Build the exact fresh Red Deck / White Stake first-blind boundary."""
    if isinstance(seed, bool) or not isinstance(seed, (str, int)):
        raise TypeError("headless game seed must be a string or exact integer")
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.owned_deck = state.deck.copy()
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.round = 0
    state.money = 4
    state.blind = create_small_blind(300)
    state.blind.reward = 3
    state.vouchers_observed = True
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    run = HeadlessRunState(
        public=state,
        seed=seed,
        blind_progression_state=BlindProgressionState(
            small_status="Select",
            big_status="Upcoming",
            boss_status="Upcoming",
            blind_on_deck="Small",
            blind_ante=1,
        ),
    )
    run = initialize_pristine_ppo_generation_authority(run)
    return initialize_pristine_ppo_boss_authority(run)


class PPOHeadlessBackend:
    """Exact backend slice through first and later ordinary shops.

    The injected tactical owner is called through the existing production-shaped
    ``decide(state)`` bridge. If that policy clears the first ordinary Blind, this
    slice completes exact progression and cash-out and publishes source-ordered
    main cards, Voucher, and Boosters. Retained progression owns first-versus-
    later shop generation and the supported Small-shop to Big-Blind exit.
    """

    def __init__(self, tactical_decision_engine: object):
        if not callable(getattr(tactical_decision_engine, "decide", None)):
            raise TypeError("tactical_decision_engine must provide decide(state)")
        self._tactical_decision_engine = tactical_decision_engine
        self._run: HeadlessRunState | None = None
        self._frame: EnvStateFrame | None = None
        self._tactical_actions = 0

    @property
    def run(self) -> HeadlessRunState:
        if self._run is None:
            raise RuntimeError("backend has not been reset")
        return self._run

    def _boundary_frame(
        self,
        run: HeadlessRunState,
        tactical_actions: int,
    ) -> EnvStateFrame:
        state = run.public
        info = {
            "backend_schema": PPO_HEADLESS_BACKEND_SCHEMA,
            "reward_contract": PPO_REWARD_CONTRACT,
            "game_seed": str(run.seed),
            "tactical_actions": tactical_actions,
        }
        if state.phase == "GAME_OVER":
            if (
                state.blind is None
                or state.hands_remaining != 0
                or state.score >= state.blind.requirement
            ):
                raise HeadlessTransitionError(
                    "GAME_OVER boundary is not an exact exhausted-hand loss"
                )
            return EnvStateFrame(
                state,
                status=RunStatus.LOSS,
                owner=TurnOwner.TERMINAL,
                info=info,
            )
        if state.phase not in {"BLIND_SELECT", "SHOP"}:
            raise HeadlessTransitionError(
                "backend exposed a non-strategic nonterminal boundary"
            )
        return EnvStateFrame(
            state,
            status=RunStatus.RUNNING,
            owner=TurnOwner.AGENT,
            info=info,
        )

    def reset(self, seed: str | int) -> EnvStateFrame:
        run = pristine_red_white_reset(seed)
        frame = self._boundary_frame(run, 0)
        self._run = run
        self._frame = frame
        self._tactical_actions = 0
        return frame

    def legal_actions(self) -> tuple[EnvAction, ...]:
        run = self.run
        if self._frame is None or self._frame.status.terminal:
            return ()
        if run.public.phase == "SHOP":
            return ShopTransitionEngine().legal_actions(run)
        actions: list[EnvAction] = []
        if can_skip_blind_exact(run):
            actions.append(EnvAction.from_alias("SKIP_BLIND"))
        if can_select_blind_exact(run):
            actions.append(EnvAction.from_alias("SELECT_BLIND"))
        return tuple(actions)

    def _settle_tactical_round(
        self,
        run: HeadlessRunState,
    ) -> tuple[HeadlessRunState, int]:
        next_run = run
        tactical_actions = self._tactical_actions
        while next_run.public.phase == "SELECTING_HAND":
            if tactical_actions >= _MAX_TACTICAL_ACTIONS:
                raise HeadlessTransitionError(
                    "tactical settlement exceeded its exact action cap"
                )
            next_run = apply_planned_tactical_step(
                next_run,
                self._tactical_decision_engine,
            )
            tactical_actions += 1
        if next_run.public.phase == "ROUND_EVAL":
            resolution = resolve_supported_ordinary_round(
                next_run,
                next_run.require_blind_progression_state(),
            )
            shop = resolution.run.public
            if shop.phase != "SHOP" or not shop.shop_active or any(
                (
                    shop.shop_jokers,
                    shop.shop_consumables,
                    shop.shop_boosters,
                    shop.shop_vouchers,
                )
            ):
                raise HeadlessTransitionError(
                    "ordinary cash-out did not reach an ungenerated SHOP"
                )
            generated = generate_progression_normal_shop_inventory(
                resolution.run,
                first_buffoon_variant=(
                    PPO_TRAINING_PROFILE.first_shop_buffoon_variant
                ),
                banned_booster_keys=PPO_TRAINING_PROFILE.banned_center_keys,
            )
            return generated.run, tactical_actions
        if next_run.public.phase != "GAME_OVER":
            raise HeadlessTransitionError(
                f"tactical settlement reached unsupported phase {next_run.public.phase!r}"
            )
        return next_run, tactical_actions

    def step(self, action: EnvAction) -> BackendStep:
        if action not in self.legal_actions():
            raise HeadlessTransitionError(f"illegal backend action: {action.alias}")
        run = self.run
        tactical_actions = self._tactical_actions
        if run.public.phase == "SHOP":
            next_run = ShopTransitionEngine().step(run, action)
        elif action.alias == "SKIP_BLIND":
            next_run = skip_blind_exact(run)
        elif action.alias == "SELECT_BLIND":
            activated = activate_selected_blind_progression(run)
            next_run, tactical_actions = self._settle_tactical_round(
                select_blind_exact(activated)
            )
        else:
            raise HeadlessTransitionError(f"unsupported backend action: {action.alias}")
        frame = self._boundary_frame(next_run, tactical_actions)
        self._run = next_run
        self._frame = frame
        self._tactical_actions = tactical_actions
        return BackendStep(
            frame=frame,
            reward=sparse_terminal_reward(frame.status),
            truncated=False,
        )

    def serialize(self) -> dict[str, Any]:
        run = self.run
        if self._frame is None:
            raise RuntimeError("backend has not been reset")
        return {
            "schema": PPO_HEADLESS_BACKEND_SCHEMA,
            "tactical_actions": self._tactical_actions,
            "run": serialize_headless_run_state(run),
        }

    def restore(self, payload: dict[str, Any]) -> EnvStateFrame:
        if not isinstance(payload, dict) or set(payload) != {
            "schema",
            "tactical_actions",
            "run",
        }:
            raise HeadlessTransitionError("backend snapshot fields are incomplete")
        if payload["schema"] != PPO_HEADLESS_BACKEND_SCHEMA:
            raise HeadlessTransitionError("backend snapshot schema mismatch")
        actions = payload["tactical_actions"]
        if isinstance(actions, bool) or not isinstance(actions, int) or actions < 0:
            raise HeadlessTransitionError("backend tactical action count is invalid")
        run = restore_headless_run_state(payload["run"])
        frame = self._boundary_frame(run, actions)
        self._run = run
        self._frame = frame
        self._tactical_actions = actions
        return frame
