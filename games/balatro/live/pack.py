from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER, BalatroAction

from .external.live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _normalize_card,
    _normalize_item,
    _string,
    _table_fields,
)


@dataclass(frozen=True)
class LivePackChoice:
    """One currently visible public booster-pack choice."""

    area_index: int
    address: int
    data: dict[str, Any]

    @property
    def label(self) -> str | None:
        return self.data.get("label") or self.data.get("ability_name") or self.data.get("center")

    @property
    def live_id(self):
        return self.data.get("live_id")

    @property
    def kind(self) -> str:
        value = self.data.get("ability_set")
        if isinstance(value, str) and value:
            return value.upper()
        card = self.data.get("value") or {}
        if card.get("rank") is not None and card.get("suit") is not None:
            return "PLAYING_CARD"
        return "UNKNOWN"


class LivePackActionGenerator:
    """Generate legal actions for a currently visible booster pack."""

    def __init__(self, *, include_capacity_blocked_jokers: bool = False) -> None:
        self.include_capacity_blocked_jokers = bool(
            include_capacity_blocked_jokers
        )

    def read_choices(self, observer: LiveMemoryBalatroObserver) -> list[LivePackChoice]:
        snapshot = observer.observe()
        if not snapshot.phase.endswith("_PACK"):
            return []

        decoder, _, root = observer._root()
        game = _table_fields(decoder, root.get("GAME"))
        last_tarot_planet = _string(game.get("last_tarot_planet"))
        area = _table_fields(decoder, root.get("pack_cards"))
        choices: list[LivePackChoice] = []
        for index, (_, address) in enumerate(_array_table_values(decoder, area.get("cards"))):
            item = _normalize_item(decoder, address, area_index=index)
            playing = _normalize_card(decoder, address)
            value = playing.get("value") or {}
            if value.get("rank") is not None and value.get("suit") is not None:
                # Keep card modifiers/rank/suit while retaining any useful item metadata.
                data = dict(item)
                data.update(playing)
                data["area_index"] = index
                data["ability_set"] = "PLAYING_CARD"
            else:
                data = item

            # The Fool's copy target is ordinary public run history stored by
            # Balatro as G.GAME.last_tarot_planet. Whitelist only the center key;
            # no RNG state or hidden draw order is exposed.
            if last_tarot_planet is not None:
                data["last_tarot_planet"] = last_tarot_planet

            choices.append(LivePackChoice(index, address, data))
        return choices

    def generate_actions(self, state, choices: list[LivePackChoice]) -> list[BalatroAction]:
        phase = str(getattr(state, "phase", ""))
        if not phase.endswith("_PACK"):
            return []

        actions: list[BalatroAction] = []
        joker_slots = int(getattr(state, "joker_slots", 0))
        joker_count = len(getattr(state, "jokers", []))
        has_free_joker_slot = joker_count < joker_slots
        has_selectable_joker = False

        for choice in choices:
            # Balatro cannot take another Joker from a Buffoon pack when all Joker
            # slots are occupied unless the player first sells one. That is a
            # separate action and is deliberately not hidden inside pack selection.
            if (
                choice.kind == "JOKER"
                and joker_count >= joker_slots
                and not self.include_capacity_blocked_jokers
            ):
                continue
            if choice.kind == "JOKER" and has_free_joker_slot:
                has_selectable_joker = True
            actions.append(BalatroAction(SELECT_PACK_CARD, target=choice))

        # A Buffoon pack with a genuinely free Joker slot should resolve by taking
        # one of its visible Jokers. In particular, Joker Stencil's temporary value
        # from an empty slot may influence which Joker is preferred, but must never
        # make the agent throw away the whole pack while capacity is available.
        # Full-roster Buffoon packs keep Skip because replacement requires a
        # separate sell action.
        force_joker_pick = (
            phase == "BUFFOON_PACK"
            and has_free_joker_slot
            and has_selectable_joker
        )
        if not force_joker_pick:
            # Every normal booster-pack screen exposes Skip. The executor still
            # requires the exact live skip_booster/can_skip_booster identity before
            # it can click.
            actions.append(BalatroAction(SKIP_BOOSTER))
        return actions
