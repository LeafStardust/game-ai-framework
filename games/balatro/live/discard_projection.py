from __future__ import annotations

from copy import deepcopy

from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.live.card_destruction import project_destroyed_playing_cards
from games.balatro.live.copy_projection import (
    COPY_JOKER_CLASS_NAMES,
    resolve_copy_target,
)
from games.balatro.live.generated_consumable_outcomes import ProjectedGeneratedConsumable


class UnsupportedDiscardProjection(RuntimeError):
    """Raised when exact visible discard history required by a Joker is absent."""


class LiveDiscardJokerProjector:
    """Project exact deterministic effects caused by one visible discard event.

    ``consume_discard_use`` distinguishes a player-requested discard from forced
    game mechanics such as The Hook. Forced Hook discards trigger ordinary discard
    effects such as Green Joker, Ramen, Purple Seal, Castle, and Yorick without
    consuming one of the player's discard uses. Burnt Joker is a documented
    exception: The Hook's forced discard does not activate its first-discard hand
    level-up effect.
    """

    ACTIVE_CLASS_NAMES = frozenset(
        {
            "BurntJoker",
            "CastleJoker",
            "FacelessJoker",
            "GreenJoker",
            "HitTheRoadJoker",
            "MailInRebateJoker",
            "RamenJoker",
            "TradingCardJoker",
            "YorickJoker",
        }
    )
    FIRST_DISCARD_CLASS_NAMES = frozenset(
        {
            "BurntJoker",
            "TradingCardJoker",
        }
    )
    COPYABLE_DISCARD_CLASS_NAMES = frozenset(
        {
            "BurntJoker",
            "FacelessJoker",
            "MailInRebateJoker",
        }
    )

    def __init__(self, hand_evaluator: HandEvaluator | None = None):
        self.hand_evaluator = hand_evaluator or HandEvaluator()

    def project(self, state, cards, *, consume_discard_use: bool = True):
        if state is None:
            return None

        branch_state = state.copy()
        branch_state.jokers = deepcopy(list(getattr(state, "jokers", [])))
        discarded = list(cards or [])
        active = self._active_jokers(
            branch_state,
            consume_discard_use=consume_discard_use,
        )
        discards_used = getattr(branch_state, "discards_used", None)
        if discards_used is None and any(
            type(joker).__name__ in self.FIRST_DISCARD_CLASS_NAMES
            for joker in active
        ):
            raise UnsupportedDiscardProjection(
                "first-discard Joker projection requires public discards_used"
            )

        rules = hand_rules_for_state(branch_state)
        first_discard = discards_used == 0
        discarded_hand = self.hand_evaluator.evaluate(discarded, rules=rules)
        context = JokerContext(
            state=branch_state,
            cards=discarded,
            trigger="DISCARD",
            event=BalatroEvent(BalatroEventType.CARDS_DISCARDED, discarded),
            data={
                "hand_rules": rules,
                "first_discard": first_discard,
                "discarded_hand": discarded_hand,
                "consume_discard_use": bool(consume_discard_use),
                "level_up_hands": [],
                "destroyed_cards": [],
            },
        )
        for joker in active:
            context = joker.apply(context)

        # Purple Seals trigger on the discard event before a Trading Card can
        # permanently destroy the same playing card. Random Tarot identity is
        # intentionally abstracted until authoritative re-observation.
        self._apply_purple_seals(branch_state, discarded)
        self._apply_hand_level_ups(branch_state, context.data.get("level_up_hands"))
        destroyed = project_destroyed_playing_cards(
            branch_state,
            context.data.get("destroyed_cards", ()),
        )
        self._append_discard_pile(branch_state, discarded, destroyed)
        if consume_discard_use and discards_used is not None:
            branch_state.discards_used = max(0, int(discards_used)) + 1
        return branch_state

    def _active_jokers(self, state, *, consume_discard_use: bool = True) -> list:
        active = []
        for joker in getattr(state, "jokers", []) or []:
            class_name = type(joker).__name__
            if class_name in self.ACTIVE_CLASS_NAMES:
                if class_name == "BurntJoker" and not consume_discard_use:
                    continue
                active.append(joker)
                continue
            if class_name not in COPY_JOKER_CLASS_NAMES:
                continue
            target, resolvable = resolve_copy_target(joker, state)
            if (
                resolvable
                and target is not None
                and type(target).__name__ in self.COPYABLE_DISCARD_CLASS_NAMES
            ):
                if (
                    type(target).__name__ == "BurntJoker"
                    and not consume_discard_use
                ):
                    continue
                active.append(target)
        return active

    @staticmethod
    def _apply_hand_level_ups(state, hands) -> None:
        for hand in list(hands or []):
            key = getattr(hand, "value", hand)
            key = str(key)
            if key not in getattr(state, "hand_levels", {}):
                continue
            state.hand_levels[key] = int(state.hand_levels[key]) + 1

    @staticmethod
    def _apply_purple_seals(state, cards) -> None:
        room = max(
            0,
            int(getattr(state, "consumable_slots", 0) or 0)
            - len(getattr(state, "consumables", []) or []),
        )
        if room <= 0:
            return

        for card in list(cards or []):
            if room <= 0:
                break
            if bool(getattr(card, "debuffed", False)):
                continue
            if str(getattr(card, "seal", "") or "").upper() != "PURPLE":
                continue
            state.consumables.append(
                ProjectedGeneratedConsumable(
                    category="TAROT",
                    name="Projected Tarot",
                )
            )
            room -= 1

    @staticmethod
    def _append_discard_pile(state, discarded, destroyed) -> None:
        destroyed_ids = {
            ("live", getattr(card, "live_id", None))
            if getattr(card, "live_id", None) is not None
            else ("object", id(card))
            for card in list(destroyed or [])
        }
        pile = list(getattr(state, "discard_pile", []) or [])
        for card in list(discarded or []):
            identity = (
                ("live", getattr(card, "live_id", None))
                if getattr(card, "live_id", None) is not None
                else ("object", id(card))
            )
            if identity not in destroyed_ids:
                pile.append(card)
        state.discard_pile = pile
