"""Exact fail-closed booster-pack strategic transitions.

Pinned vanilla G.FUNCS.skip_booster first notifies every Joker with the
skipping_booster context, where Red Card is the only gameplay mutation, then
closes the pack and restores G.GAME.PACK_INTERRUPT. This owner requires that
return origin explicitly because public pack phase alone cannot distinguish a
purchased pack from a Tag-opened pack.
"""

from __future__ import annotations

from games.balatro.env.actions import EnvAction
from games.balatro.env.joker_order import JokerOrderError
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.red_card import RedCardJoker
from games.balatro.env.transition import _EXACT_R1_JOKER_ACQUISITION_TYPES


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


def validate_choose_pack_option_exact(
    run: HeadlessRunState,
    option_index: int,
) -> None:
    """Validate a one-pick Buffoon choice with inventory-only Joker lifecycle."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "BUFFOON_PACK":
        raise HeadlessTransitionError(
            "exact CHOOSE_PACK_OPTION currently supports BUFFOON_PACK only"
        )
    if run.pack_return_phase not in {"SHOP", "BLIND_SELECT"}:
        raise HeadlessTransitionError(
            "CHOOSE_PACK_OPTION requires authoritative pack return phase"
        )
    if run.pack_choices_remaining != 1:
        raise HeadlessTransitionError(
            "CHOOSE_PACK_OPTION currently requires an exact final pack choice"
        )
    if isinstance(option_index, bool) or not isinstance(option_index, int):
        raise HeadlessTransitionError("pack option index must be an exact integer")
    if option_index < 0 or option_index >= len(run.pack_choices):
        raise HeadlessTransitionError("pack option index is out of range")
    if state.hand or state.shop_active:
        raise HeadlessTransitionError("Buffoon choice requires exact isolated pack state")
    if len(state.jokers) >= state.joker_slots:
        raise HeadlessTransitionError("no Joker capacity for Buffoon choice")

    joker = run.pack_choices[option_index]
    if type(joker) not in _EXACT_R1_JOKER_ACQUISITION_TYPES:
        raise HeadlessTransitionError(
            "Buffoon Joker acquisition lifecycle is not exactly owned"
        )
    if getattr(joker, "edition", None) is not None:
        raise HeadlessTransitionError("Buffoon Joker editions remain fail-closed")
    if type(joker).__name__ == "JugglerJoker":
        raise HeadlessTransitionError(
            "resource-mutating Buffoon Joker acquisition remains fail-closed"
        )
    if run.joker_order_state is not None:
        run.require_joker_order_state()


def can_choose_pack_option_exact(run: HeadlessRunState, option_index: int) -> bool:
    try:
        validate_choose_pack_option_exact(run, option_index)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def choose_pack_option_exact(
    run: HeadlessRunState,
    option_index: int,
) -> HeadlessRunState:
    validate_choose_pack_option_exact(run, option_index)
    next_run = run.copy()
    joker = next_run.pack_choices[option_index]
    if next_run.joker_order_state is not None:
        try:
            next_run.joker_order_state.acquire(joker, next_run.public.jokers)
        except JokerOrderError as exc:
            raise HeadlessTransitionError(
                "cannot retain exact Joker order after Buffoon choice"
            ) from exc
    next_run.public.jokers.append(joker)
    next_run.public.phase = next_run.pack_return_phase
    next_run.public.shop_active = next_run.pack_return_phase == "SHOP"
    next_run.pack_choices.clear()
    next_run.pack_choices_remaining = 0
    next_run.pack_return_phase = None
    return next_run


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
    next_run.pack_choices_remaining = 0
    next_run.pack_return_phase = None
    return next_run


class PackTransitionEngine:
    def legal_actions(self, run: HeadlessRunState) -> tuple[EnvAction, ...]:
        actions = [
            EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": index})
            for index in range(len(run.pack_choices))
            if can_choose_pack_option_exact(run, index)
        ]
        if can_skip_pack_exact(run):
            actions.append(EnvAction.from_alias("SKIP_PACK"))
        return tuple(actions)

    def step(self, run: HeadlessRunState, action: EnvAction) -> HeadlessRunState:
        if action not in self.legal_actions(run):
            raise HeadlessTransitionError(f"illegal pack transition: {action.alias}")
        if action.alias == "CHOOSE_PACK_OPTION":
            option_index = action.payload().get("option_index")
            return choose_pack_option_exact(run, option_index)
        if action.alias == "SKIP_PACK":
            return skip_pack_exact(run)
        raise HeadlessTransitionError(f"unimplemented pack transition: {action.alias}")
