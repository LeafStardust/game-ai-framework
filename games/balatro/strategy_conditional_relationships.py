from __future__ import annotations

from collections import Counter

from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import card_matches_suit, hand_rules_for_state
from games.balatro.strategy import (
    BANNED,
    BRONZE,
    GOLD,
    NEUTRAL,
    SILVER,
    BalatroStrategyTracker,
    StrategyDefinition,
)


_RELATIONSHIP_PRIORITY = {
    NEUTRAL: 0,
    BRONZE: 1,
    SILVER: 2,
    GOLD: 3,
    BANNED: 4,
}
_SUITS = ("Hearts", "Diamonds", "Clubs", "Spades")
_STRAIGHT_FLUSH_SUIT_JOKERS = {
    "arrowheadjoker": "Spades",
    "bloodstonejoker": "Hearts",
    "onyxagatejoker": "Clubs",
    "roughgemjoker": "Diamonds",
}


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _owned_deck(state) -> list:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        return list(owned)
    return list(getattr(state, "deck", ()) or ())


def _regular_deck(state) -> list:
    return [
        card
        for card in _owned_deck(state)
        if str(getattr(card, "enhancement", "")) != "Stone"
    ]


def _item_token(item: object) -> str:
    return _normalize(type(item).__name__)


def _straight_exists_in_effective_suit(state, suit: str) -> bool:
    rules = hand_rules_for_state(state)
    suited = [
        card
        for card in _regular_deck(state)
        if card_matches_suit(card, suit, rules)
    ]
    return HandEvaluator().contains(suited, PokerHand.STRAIGHT, rules=rules)


def _seeing_double_flush_is_feasible(state) -> bool:
    """Return whether one current flush can also satisfy Seeing Double's trigger."""
    rules = hand_rules_for_state(state)
    required = max(1, int(rules.get("flush_size", 5) or 5))
    deck = _regular_deck(state)
    for flush_suit in _SUITS:
        pool = [card for card in deck if card_matches_suit(card, flush_suit, rules)]
        if len(pool) < required:
            continue
        for club_index, club_card in enumerate(pool):
            if not card_matches_suit(club_card, "Clubs", rules):
                continue
            for other_index, other_card in enumerate(pool):
                if other_index == club_index:
                    continue
                if any(
                    card_matches_suit(other_card, suit, rules)
                    for suit in ("Hearts", "Diamonds", "Spades")
                ):
                    return True
    return False


def _idol_counts(state, idol) -> tuple[int, int]:
    rank = str(getattr(idol, "rank", ""))
    suit = str(getattr(idol, "suit", ""))
    if not rank or suit not in _SUITS:
        return 0, 0
    rules = hand_rules_for_state(state)
    rank_cards = [
        card
        for card in _regular_deck(state)
        if str(getattr(card, "rank", "")) == rank
    ]
    effective_target = sum(
        card_matches_suit(card, suit, rules)
        for card in rank_cards
    )
    return len(rank_cards), effective_target


def _dna_rank_collapse_conflicts_with_straight_flush(state) -> bool:
    """Fail closed unless public deck shape shows unambiguous rank collapse.

    A duplicated rank alone is not enough to blame DNA or declare a conflict. The
    relationship becomes Banned only when the current deck both contains a rank
    beyond the natural four-copy baseline and cannot form any Straight under the
    owned public passive hand rules. That makes the conflict structural rather than
    inferred from hidden use history.
    """
    deck = _regular_deck(state)
    if not deck:
        return False
    rank_counts = Counter(str(getattr(card, "rank", "")) for card in deck)
    if max(rank_counts.values(), default=0) <= 4:
        return False
    rules = hand_rules_for_state(state)
    return not HandEvaluator().contains(deck, PokerHand.STRAIGHT, rules=rules)


def conditional_joker_relationship(
    state,
    strategy_id: str,
    item: object,
) -> str:
    """Resolve state-dependent Joker relationships from current public run state."""
    token = _item_token(item)

    if strategy_id == "flush" and token == "seeingdoublejoker":
        return BRONZE if _seeing_double_flush_is_feasible(state) else NEUTRAL

    if strategy_id == "straight_flush" and token in _STRAIGHT_FLUSH_SUIT_JOKERS:
        suit = _STRAIGHT_FLUSH_SUIT_JOKERS[token]
        return BRONZE if _straight_exists_in_effective_suit(state, suit) else NEUTRAL

    if strategy_id == "straight_flush" and token == "dnajoker":
        return (
            BANNED
            if _dna_rank_collapse_conflicts_with_straight_flush(state)
            else NEUTRAL
        )

    if token == "theidoljoker" and strategy_id in {"five_kind", "flush_five"}:
        rank_count, effective_target_count = _idol_counts(state, item)
        if strategy_id == "flush_five":
            # Five copies of the Idol's exact effective rank+suit target make the
            # defining Flush Five shell currently reachable.
            return GOLD if effective_target_count >= 5 else NEUTRAL
        # Five of a Kind must already be reachable by rank, and at least one exact
        # target duplicate must exist. Two identical effective rank+suit cards is
        # the first state that proves concentration beyond an ordinary deck copy.
        return (
            SILVER
            if rank_count >= 5 and effective_target_count >= 2
            else NEUTRAL
        )

    return NEUTRAL


class _ConditionalDefinitionView:
    """Bind one universal definition to a public state for owned-item assessment."""

    def __init__(self, definition: StrategyDefinition, state) -> None:
        self._definition = definition
        self._state = state

    def __getattr__(self, name):
        return getattr(self._definition, name)

    def relationship_for(self, item: object, *, kind: str) -> str:
        static = self._definition.relationship_for(item, kind=kind)
        if str(kind).upper() != "JOKER":
            return static
        conditional = conditional_joker_relationship(
            self._state,
            self._definition.strategy_id,
            item,
        )
        return (
            conditional
            if _RELATIONSHIP_PRIORITY[conditional] > _RELATIONSHIP_PRIORITY[static]
            else static
        )


class StateAwareBalatroStrategyTracker(BalatroStrategyTracker):
    """Universal tracker with public-state conditional component relationships.

    Static exact relationships remain in the universal catalogue/guard. This
    subclass supplies only relationships whose documented tier depends on current
    public deck/Joker state, allowing inherited scoring, shortlist, pivot and Ante
    pressure logic to remain authoritative.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._relationship_state = None

    def assess(self, state):
        self._relationship_state = state
        assessments = [
            result
            for definition in self.definitions.values()
            if (
                result := self._assess(
                    state,
                    _ConditionalDefinitionView(definition, state),
                )
            )
            is not None
        ]
        return tuple(sorted(assessments, key=lambda assessment: (-assessment.score, assessment.strategy_id)))

    def _relationships_for(self, item: object, *, kind: str) -> dict[str, str]:
        found = super()._relationships_for(item, kind=kind)
        if str(kind).upper() != "JOKER" or self._relationship_state is None:
            return found
        for strategy_id in self.definitions:
            conditional = conditional_joker_relationship(
                self._relationship_state,
                strategy_id,
                item,
            )
            if conditional == NEUTRAL:
                continue
            previous = found.get(strategy_id, NEUTRAL)
            if _RELATIONSHIP_PRIORITY[conditional] > _RELATIONSHIP_PRIORITY[previous]:
                found[strategy_id] = conditional
        return found

    def evaluate_item(self, state, item: object, *, kind: str):
        self._relationship_state = state
        return super().evaluate_item(state, item, kind=kind)
