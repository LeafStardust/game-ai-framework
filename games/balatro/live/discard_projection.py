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


class UnsupportedDiscardProjection(RuntimeError):
    """Raised when exact visible discard history required by a Joker is absent."""


class LiveDiscardJokerProjector:
    """Project exact deterministic Joker effects caused by one visible discard."""

    ACTIVE_CLASS_NAMES = frozenset(
        {
            "BurntJoker",
            "FacelessJoker",
            "MailInRebateJoker",
            "TradingCardJoker",
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

    def project(self, state, cards):
        if state is None:
            return None

        branch_state = state.copy()
        branch_state.jokers = deepcopy(list(getattr(state, "jokers", [])))
        discarded = list(cards or [])
        active = self._active_jokers(branch_state)
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
                "level_up_hands": [],
                "destroyed_cards": [],
            },
        )
        for joker in active:
            context = joker.apply(context)

        self._apply_hand_level_ups(branch_state, context.data.get("level_up_hands"))
        project_destroyed_playing_cards(
            branch_state,
            context.data.get("destroyed_cards", ()),
        )
        if discards_used is not None:
            branch_state.discards_used = max(0, int(discards_used)) + 1
        return branch_state

    def _active_jokers(self, state) -> list:
        active = []
        for joker in getattr(state, "jokers", []) or []:
            class_name = type(joker).__name__
            if class_name in self.ACTIVE_CLASS_NAMES:
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
