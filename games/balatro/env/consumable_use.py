"""Exact strategic held-consumable use slices."""

from __future__ import annotations

from games.balatro.consumable import ConsumableContext, PlanetCard
from games.balatro.env.actions import EnvAction
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.constellation import ConstellationJoker
from games.balatro.planets import PLANET_CARDS


_PLANET_KEY_BY_NAME = {
    planet.name: f"c_{name.lower()}"
    for name, planet in PLANET_CARDS.items()
}


def validate_use_planet_exact(run: HeadlessRunState, consumable_index: int) -> None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("exact Planet use requires active SHOP")
    if not run.consumable_usage_observed:
        raise HeadlessTransitionError("Planet use requires authoritative usage history")
    if isinstance(consumable_index, bool) or not isinstance(consumable_index, int):
        raise HeadlessTransitionError("consumable index must be an exact integer")
    if consumable_index < 0 or consumable_index >= len(state.consumables):
        raise HeadlessTransitionError("consumable index is out of range")

    planet = state.consumables[consumable_index]
    if type(planet) is not PlanetCard:
        raise HeadlessTransitionError("exact USE_CONSUMABLE currently supports Planet cards only")
    if getattr(planet, "debuffed", False):
        raise HeadlessTransitionError("debuffed Planet cannot be used")
    if planet.name not in _PLANET_KEY_BY_NAME:
        raise HeadlessTransitionError("Planet identity is not canonical")
    level = state.hand_levels.get(planet.hand_type)
    if type(level) is not int or level < 1:
        raise HeadlessTransitionError("Planet target hand level is not exact")
    context = ConsumableContext(state=state)
    if not planet.can_use(context):
        raise HeadlessTransitionError("Planet cannot be used in current state")


def can_use_planet_exact(run: HeadlessRunState, consumable_index: int) -> bool:
    try:
        validate_use_planet_exact(run, consumable_index)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def use_planet_exact(run: HeadlessRunState, consumable_index: int) -> HeadlessRunState:
    validate_use_planet_exact(run, consumable_index)
    next_run = run.copy()
    state = next_run.public
    planet = state.consumables.pop(consumable_index)
    key = _PLANET_KEY_BY_NAME[planet.name]

    planet.use(ConsumableContext(state=state))
    state.last_tarot_planet = key
    next_run.consumable_usage_counts[key] = (
        next_run.consumable_usage_counts.get(key, 0) + 1
    )
    for total_key in ("planet", "tarot_planet", "all"):
        next_run.consumable_usage_totals[total_key] = (
            next_run.consumable_usage_totals.get(total_key, 0) + 1
        )
    for joker in state.jokers:
        if type(joker) is ConstellationJoker:
            joker.x_mult += 0.1
    return next_run


class ConsumableTransitionEngine:
    def legal_actions(self, run: HeadlessRunState) -> tuple[EnvAction, ...]:
        return tuple(
            EnvAction.from_alias("USE_CONSUMABLE", {"consumable_index": index})
            for index in range(len(run.public.consumables))
            if can_use_planet_exact(run, index)
        )

    def step(self, run: HeadlessRunState, action: EnvAction) -> HeadlessRunState:
        if action not in self.legal_actions(run):
            raise HeadlessTransitionError(f"illegal consumable transition: {action.alias}")
        if action.alias == "USE_CONSUMABLE":
            return use_planet_exact(run, action.payload().get("consumable_index"))
        raise HeadlessTransitionError(f"unimplemented consumable transition: {action.alias}")
