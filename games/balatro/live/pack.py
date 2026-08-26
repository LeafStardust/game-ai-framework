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
    """Generate candidate actions for a currently visible booster pack.

    Full-roster Buffoon Jokers remain visible to policy by default. They are not
    directly selectable while capacity is full; the playbook pack policy may turn
    a worthwhile visible replacement into a separate SELL_JOKER checkpoint first.
    Deterministic destructive Tarots such as Hanged Man remain visible too; B6 owns
    their target/opportunity-cost decision instead of the generator hard-vetoing a
    potentially profitable mechanical tradeoff.
    """

    def __init__(self, *, include_capacity_blocked_jokers: bool = True) -> None:
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
                data = dict(item)
                data.update(playing)
                data["area_index"] = index
                data["ability_set"] = "PLAYING_CARD"
            else:
                data = item

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
            if (
                choice.kind == "JOKER"
                and joker_count >= joker_slots
                and not self.include_capacity_blocked_jokers
            ):
                continue
            if choice.kind == "JOKER" and has_free_joker_slot:
                has_selectable_joker = True
            actions.append(BalatroAction(SELECT_PACK_CARD, target=choice))

        force_joker_pick = (
            phase == "BUFFOON_PACK"
            and has_free_joker_slot
            and has_selectable_joker
        )
        if not force_joker_pick:
            actions.append(BalatroAction(SKIP_BOOSTER))
        return actions
