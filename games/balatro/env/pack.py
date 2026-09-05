"""Exact fail-closed booster-pack strategic transitions.

Pinned vanilla G.FUNCS.skip_booster first notifies every Joker with the
skipping_booster context, where Red Card is the only gameplay mutation, then
closes the pack and restores G.GAME.PACK_INTERRUPT. This owner requires that
return origin explicitly because public pack phase alone cannot distinguish a
purchased pack from a Tag-opened pack.
"""

from __future__ import annotations

from games.balatro.env.actions import EnvAction
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.red_card import RedCardJoker


PACK_PHASES = frozenset(
    {"BUFFOON_PACK", "PLANET_PACK", "SPECTRAL_PACK", "STANDARD_PACK", "TAROT_PACK"}
)


def validate_skip_pack_exact(run: HeadlessRunState) -> None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase not in PACK_PHASES:
        raise HeadlessTransitionError("SKIP_PACK requires an exact open-pack phase")
    if run.pack_return_phase not in {"SHOP", "BLIND_SELECT"}:
        raise HeadlessTransitionError(
            "SKIP_PACK requires authoritative SHOP or BLIND_SELECT return phase"
        )
    if not run.pack_choices:
        raise HeadlessTransitionError("SKIP_PACK requires authoritative offered choices")
    if state.hand:
        raise HeadlessTransitionError("SKIP_PACK does not own nonempty hand-to-deck cleanup")
    if state.shop_active:
        raise HeadlessTransitionError("open-pack public state cannot remain an active main shop")


def can_skip_pack_exact(run: HeadlessRunState) -> bool:
    try:
        validate_skip_pack_exact(run)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def skip_pack_exact(run: HeadlessRunState) -> HeadlessRunState:
    validate_skip_pack_exact(run)
    next_run = run.copy()
    for joker in next_run.public.jokers:
        if type(joker) is RedCardJoker:
            joker.mult += 3
    next_run.public.phase = next_run.pack_return_phase
    next_run.public.shop_active = next_run.pack_return_phase == "SHOP"
    next_run.pack_choices.clear()
    next_run.pack_return_phase = None
    return next_run


class PackTransitionEngine:
    def legal_actions(self, run: HeadlessRunState) -> tuple[EnvAction, ...]:
        return (EnvAction.from_alias("SKIP_PACK"),) if can_skip_pack_exact(run) else ()

    def step(self, run: HeadlessRunState, action: EnvAction) -> HeadlessRunState:
        if action not in self.legal_actions(run):
            raise HeadlessTransitionError(f"illegal pack transition: {action.alias}")
        if action.alias == "SKIP_PACK":
            return skip_pack_exact(run)
        raise HeadlessTransitionError(f"unimplemented pack transition: {action.alias}")
