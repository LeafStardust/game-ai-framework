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
_HIGH_CARD_STRATEGY_ID = "high_card"
_HIGH_CARD_OBELISK_COMMITMENT_JOKERS = frozenset(
    {
        "burntjoker",
        "cardsharpjoker",
        "supernovajoker",
        "spacejoker",
        "halfjoker",
        "greenjoker",
        "burglarjoker",
        "stuntmanjoker",
    }
)
_PAIR_STRATEGY_ID = "pair"
_PAIR_DIRECT_COMMITMENT_JOKERS = frozenset(
    {"theduojoker", "jollyjoker", "slyjoker"}
)
_PAIR_CONDITIONAL_SUPPORT_JOKERS = frozenset(
    {
        "halfjoker",
        "supernovajoker",
        "cardsharpjoker",
        "spacejoker",
        "burntjoker",
        "greenjoker",
        "burglarjoker",
    }
)
_PAIR_CONDITIONAL_FILLER_JOKERS = frozenset(
    {
        "squarejoker",
        "raisedfistjoker",
        "blackboardjoker",
        "shootthemoonjoker",
        "hikerjoker",
        "hangingchadjoker",
    }
)
_TWO_PAIR_STRATEGY_ID = "two_pair"
_TWO_PAIR_DIRECT_COMMITMENT_JOKERS = frozenset(
    {"madjoker", "cleverjoker", "sparetrousersjoker"}
)
_TWO_PAIR_CONDITIONAL_SUPPORT_JOKERS = frozenset(
    {"theduojoker", "jollyjoker", "slyjoker", "supernovajoker", "cardsharpjoker", "spacejoker", "burntjoker"}
)
_BARON_MIME_STRATEGY_ID = "high_card_baron_mime"
_BARON_MIME_CONDITIONAL_POSITIVE_JOKERS = frozenset({"baronjoker", "mimejoker"})
_BARON_MIME_AUTHORITATIVE_CONDITIONAL_JOKERS = frozenset(
    {"baronjoker", "mimejoker", "stuntmanjoker"}
)
_ACES_SUPPORT_JOKERS = frozenset({"dnajoker", "fibonaccijoker", "oddtoddjoker"})
_TWOS_SILVER_SUPPORT_JOKERS = frozenset(
    {"hackjoker", "fibonaccijoker", "evenstevenjoker"}
)
_TWOS_BRONZE_SUPPORT_JOKERS = frozenset({"dnajoker", "hologramjoker"})
_TEN_FOUR_BRONZE_SUPPORT_JOKERS = frozenset(
    {"dnajoker", "hologramjoker"}
)
_PLAYED_CARD_RETRIGGER_JOKERS = frozenset(
    {
        "hangingchadjoker",
        "seltzerjoker",
        "duskjoker",
        "sockandbuskinjoker",
        "hackjoker",
    }
)
_SUIT_STRATEGY_PAYOFF_JOKERS = {
    "hearts": frozenset({"bloodstonejoker", "lustyjoker"}),
    "diamonds": frozenset({"roughgemjoker", "greedyjoker"}),
    "clubs": frozenset(
        {"onyxagatejoker", "seeingdoublejoker", "gluttonousjoker"}
    ),
    "spades": frozenset({"arrowheadjoker", "wrathfuljoker"}),
}
_SUIT_RETRIGGER_PAYOFF_JOKERS = {
    "diamonds": frozenset({"roughgemjoker", "greedyjoker"}),
    "spades": frozenset({"arrowheadjoker", "wrathfuljoker"}),
}
_FACE_PAREIDOLIA_PAYOFF_JOKERS = frozenset(
    {
        "scaryfacejoker",
        "smileyfacejoker",
        "businesscardjoker",
        "midasmaskjoker",
        "photographjoker",
        "sockandbuskinjoker",
        "reservedparkingjoker",
    }
)
_BUSINESS_CARD_SUPPORT_JOKERS = frozenset(
    {
        "oopsall6sjoker",
        "pareidoliajoker",
        "sockandbuskinjoker",
        "hangingchadjoker",
        "seltzerjoker",
        "duskjoker",
    }
)
_POKER_HAND_OBELISK_COMMITMENTS = {
    "three_kind": (
        "THREE_OF_A_KIND",
        frozenset({
            "thetriojoker", "zanyjoker", "wilyjoker", "dnajoker",
            "halfjoker", "theduojoker", "jollyjoker", "slyjoker",
            "tradingcardjoker",
        }),
    ),
    "straight": (
        "STRAIGHT",
        frozenset({
            "theorderjoker", "shortcutjoker", "fourfingersjoker", "runnerjoker",
            "superpositionjoker", "crazyjoker", "deviousjoker",
        }),
    ),
    "flush": (
        "FLUSH",
        frozenset({
            "thetribejoker", "drolljoker", "craftyjoker", "smearedjoker",
            "fourfingersjoker",
        }),
    ),
    "full_house": (
        "FULL_HOUSE",
        frozenset({
            "thetriojoker", "theduojoker", "sparetrousersjoker", "zanyjoker",
            "wilyjoker", "madjoker", "cleverjoker", "jollyjoker", "slyjoker",
            "dnajoker", "tradingcardjoker",
        }),
    ),
    "four_kind": (
        "FOUR_OF_A_KIND",
        frozenset({
            "thefamilyjoker", "thetriojoker", "dnajoker", "zanyjoker",
            "wilyjoker", "squarejoker", "theduojoker", "jollyjoker",
            "slyjoker", "tradingcardjoker",
        }),
    ),
    "straight_flush": (
        "STRAIGHT_FLUSH",
        frozenset({
            "theorderjoker", "thetribejoker", "shortcutjoker", "fourfingersjoker",
            "runnerjoker", "smearedjoker", "seancejoker", "crazyjoker",
            "deviousjoker", "drolljoker", "craftyjoker",
        }),
    ),
    "five_kind": (
        "FIVE_OF_A_KIND",
        frozenset({
            "thefamilyjoker", "thetriojoker", "dnajoker", "theidoljoker",
            "zanyjoker", "wilyjoker", "theduojoker", "jollyjoker", "slyjoker",
            "tradingcardjoker",
        }),
    ),
    "flush_house": (
        "FLUSH_HOUSE",
        frozenset({
            "thetribejoker", "thetriojoker", "theduojoker", "sparetrousersjoker",
            "zanyjoker", "wilyjoker", "madjoker", "cleverjoker", "smearedjoker",
            "drolljoker", "craftyjoker", "jollyjoker", "slyjoker", "dnajoker",
            "tradingcardjoker",
        }),
    ),
    "flush_five": (
        "FLUSH_FIVE",
        frozenset({
            "thefamilyjoker", "dnajoker", "theidoljoker", "thetribejoker",
            "thetriojoker", "zanyjoker", "wilyjoker", "smearedjoker",
            "drolljoker", "craftyjoker", "theduojoker", "jollyjoker",
            "slyjoker", "tradingcardjoker",
        }),
    ),
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


def _owned_joker_tokens(state) -> frozenset[str]:
    return frozenset(
        _item_token(joker)
        for joker in getattr(state, "jokers", ()) or ()
    )


def _has_joker(state, token: str) -> bool:
    return token in _owned_joker_tokens(state)


def _hand_level_is_invested(state, hand_key: str) -> bool:
    levels = getattr(state, "hand_levels", {}) or {}
    try:
        return int(levels.get(hand_key, 1) or 1) > 1
    except (TypeError, ValueError, AttributeError):
        return False


def _hand_is_most_played(state, hand_key: str) -> bool:
    """Use public play history only for mechanics that explicitly depend on it."""
    counts = getattr(state, "hand_play_counts", {}) or {}
    try:
        hand_count = int(counts.get(hand_key, 0) or 0)
    except (TypeError, ValueError, AttributeError):
        return False
    if hand_count <= 0:
        return False

    normalized_counts = []
    try:
        values = counts.values()
    except AttributeError:
        return False
    for value in values:
        try:
            normalized_counts.append(int(value or 0))
        except (TypeError, ValueError):
            normalized_counts.append(0)
    return hand_count == max(normalized_counts, default=0)


def _straight_exists_in_effective_suit(state, suit: str) -> bool:
    rules = hand_rules_for_state(state)
    deck = _regular_deck(state)
    if not deck:
        return False
    suited = [
        card
        for card in deck
        if card_matches_suit(card, suit, rules)
    ]
    # A normal undeveloped deck contains 13 cards of every suit and therefore many
    # theoretical same-suit straights. Treat the Joker as strategy evidence only
    # after its effective suit shell exceeds that ordinary 25% baseline.
    if len(suited) <= len(deck) / 4.0:
        return False
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


def _rank_is_concentrated(state, ranks: frozenset[str]) -> bool:
    deck = _regular_deck(state)
    if not deck or not ranks:
        return False
    matches = sum(str(getattr(card, "rank", "")) in ranks for card in deck)
    return matches > len(deck) * len(ranks) / 13.0


def _owned_idol(state):
    return next(
        (
            joker
            for joker in getattr(state, "jokers", ()) or ()
            if _item_token(joker) == "theidoljoker"
        ),
        None,
    )


def _idol_exact_relationship(state, idol) -> str:
    _, effective_target_count = _idol_counts(state, idol)
    if effective_target_count >= 4:
        return GOLD
    if effective_target_count >= 2:
        return SILVER
    return NEUTRAL


def _rank_strategy_relationship(state, strategy_id: str, item: object) -> str:
    token = _item_token(item)
    owned = _owned_joker_tokens(state)

    if strategy_id == "aces":
        committed = "scholarjoker" in owned or _rank_is_concentrated(
            state, frozenset({"A"})
        )
        if token in _ACES_SUPPORT_JOKERS:
            return SILVER if committed else NEUTRAL
        if token == "theidoljoker":
            _, exact = _idol_counts(state, item)
            return (
                BRONZE
                if str(getattr(item, "rank", "")) == "A" and exact >= 2
                else NEUTRAL
            )

    if strategy_id == "twos":
        committed = "weejoker" in owned or _rank_is_concentrated(
            state, frozenset({"2"})
        )
        if token in _TWOS_SILVER_SUPPORT_JOKERS:
            return SILVER if committed else NEUTRAL
        if token in _TWOS_BRONZE_SUPPORT_JOKERS:
            return BRONZE if committed else NEUTRAL
        if token == "theidoljoker":
            _, exact = _idol_counts(state, item)
            return (
                BRONZE
                if str(getattr(item, "rank", "")) == "2" and exact >= 2
                else NEUTRAL
            )

    if strategy_id == "ten_four":
        committed = "walkietalkiejoker" in owned or _rank_is_concentrated(
            state, frozenset({"10", "4"})
        )
        if token == "evenstevenjoker":
            return SILVER if committed else NEUTRAL
        if token == "hackjoker":
            four_committed = "walkietalkiejoker" in owned and (
                _rank_is_concentrated(state, frozenset({"4"}))
                or _rank_is_concentrated(state, frozenset({"10", "4"}))
            )
            return SILVER if four_committed else NEUTRAL
        if token in _TEN_FOUR_BRONZE_SUPPORT_JOKERS:
            return BRONZE if committed else NEUTRAL
        if token == "theidoljoker":
            _, exact = _idol_counts(state, item)
            return (
                BRONZE
                if str(getattr(item, "rank", "")) in {"10", "4"} and exact >= 2
                else NEUTRAL
            )

    if strategy_id == "sixes" and token == "evenstevenjoker":
        committed = "sixthsensejoker" in owned or _rank_is_concentrated(
            state, frozenset({"6"})
        )
        return SILVER if committed else NEUTRAL

    if strategy_id == "jacks_hit_road":
        if token == "mailinrebatejoker":
            return SILVER if str(getattr(item, "rank", "")) == "J" else NEUTRAL
        if token == "facelessjoker":
            committed = "hittheroadjoker" in owned or _rank_is_concentrated(
                state, frozenset({"J"})
            )
            return SILVER if committed else NEUTRAL
        if token in {"merryandyjoker", "drunkardjoker"}:
            return BRONZE if "hittheroadjoker" in owned else NEUTRAL

    if strategy_id == "queens_shoot_moon":
        committed = "shootthemoonjoker" in owned or _rank_is_concentrated(
            state, frozenset({"Q"})
        )
        if token == "mimejoker":
            return SILVER if committed else NEUTRAL
        if token == "reservedparkingjoker":
            return BRONZE if committed else NEUTRAL

    return NEUTRAL


def _section_three_relationship(state, strategy_id: str, item: object) -> str:
    """Resolve exact suit/held-card support without generic synergy leakage."""
    token = _item_token(item)
    owned = _owned_joker_tokens(state)

    if strategy_id in _SUIT_STRATEGY_PAYOFF_JOKERS and token == "smearedjoker":
        return (
            SILVER
            if owned & _SUIT_STRATEGY_PAYOFF_JOKERS[strategy_id]
            else NEUTRAL
        )

    if strategy_id in _SUIT_RETRIGGER_PAYOFF_JOKERS:
        if token in _PLAYED_CARD_RETRIGGER_JOKERS:
            return (
                SILVER
                if owned & _SUIT_RETRIGGER_PAYOFF_JOKERS[strategy_id]
                else NEUTRAL
            )

    if strategy_id == "hearts_bloodstone_oops" and token == "oopsall6sjoker":
        return GOLD if "bloodstonejoker" in owned else NEUTRAL

    if (
        strategy_id == "hearts_bloodstone_retrigger"
        and token in _PLAYED_CARD_RETRIGGER_JOKERS
    ):
        return SILVER if "bloodstonejoker" in owned else NEUTRAL

    if strategy_id == "clubs_onyx" and token in _PLAYED_CARD_RETRIGGER_JOKERS:
        return SILVER if "onyxagatejoker" in owned else NEUTRAL

    if strategy_id == "raised_fist" and token == "mimejoker":
        return SILVER if "raisedfistjoker" in owned else NEUTRAL

    if strategy_id == "ancient_suit_rotation":
        if token == "smearedjoker" or token in _PLAYED_CARD_RETRIGGER_JOKERS:
            return SILVER if "ancientjoker" in owned else NEUTRAL

    if strategy_id == "flower_pot_splash" and token == "splashjoker":
        return GOLD if "flowerpotjoker" in owned else NEUTRAL

    if strategy_id == "flower_pot_smeared" and token == "smearedjoker":
        return GOLD if "flowerpotjoker" in owned else NEUTRAL

    return NEUTRAL


def _face_branch_relationship(state, strategy_id: str, item: object) -> str:
    token = _item_token(item)
    owned = _owned_joker_tokens(state)

    if strategy_id == "face_photochad":
        if token == "hangingchadjoker":
            return GOLD if "photographjoker" in owned else NEUTRAL
        if token in {"sockandbuskinjoker", "seltzerjoker", "duskjoker"}:
            return SILVER if "photographjoker" in owned else NEUTRAL

    if strategy_id == "face_triboulet_sock":
        if token == "sockandbuskinjoker":
            return GOLD if "tribouletjoker" in owned else NEUTRAL
        if token in {"hangingchadjoker", "seltzerjoker", "duskjoker"}:
            return SILVER if "tribouletjoker" in owned else NEUTRAL

    if strategy_id == "face_pareidolia":
        if token == "pareidoliajoker":
            return (
                GOLD
                if owned & _FACE_PAREIDOLIA_PAYOFF_JOKERS
                else NEUTRAL
            )

    if strategy_id == "face_held_economy":
        if token in {"mimejoker", "pareidoliajoker"}:
            return SILVER if "reservedparkingjoker" in owned else NEUTRAL

    if strategy_id == "face_business_card" and token in _BUSINESS_CARD_SUPPORT_JOKERS:
        if "businesscardjoker" not in owned:
            return NEUTRAL
        return GOLD if token == "oopsall6sjoker" else SILVER

    if strategy_id == "faceless_ride_bus":
        if "ridethebusjoker" not in owned:
            return NEUTRAL
        if token == "tradingcardjoker":
            return SILVER
        if token in {"facelessjoker", "hittheroadjoker"}:
            return BRONZE

    if strategy_id == "faceless_discard_economy":
        if "facelessjoker" not in owned:
            return NEUTRAL
        if token == "pareidoliajoker":
            return GOLD
        if token in {
            "merryandyjoker",
            "drunkardjoker",
            "hittheroadjoker",
            "mailinrebatejoker",
        }:
            return SILVER

    return NEUTRAL


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


def _baron_mime_king_shell(state) -> tuple[list, bool]:
    """Return current Kings and whether public deck shaping deliberately supports them."""
    deck = _regular_deck(state)
    kings = [card for card in deck if str(getattr(card, "rank", "")) == "K"]
    if not kings:
        return kings, False

    # Rank density is evidence only above the current deck's natural 1/13 share.
    # This also correctly recognizes King-preserving deck thinning without needing
    # hidden card-add/remove history.
    if len(kings) > len(deck) / 13.0:
        return kings, True

    # A transformed King is deliberate held-card infrastructure even when the raw
    # number of Kings has not increased.
    shaped = any(
        _normalize(getattr(card, "enhancement", "")) == "steel"
        or _normalize(getattr(card, "seal", "")) == "red"
        for card in kings
    )
    return kings, shaped


def _baron_mime_relationship(state, token: str) -> str:
    kings, shaped_king_shell = _baron_mime_king_shell(state)
    if not kings:
        return NEUTRAL

    if token == "baronjoker":
        # Baron itself supplies the held-King payoff. Require either deliberate
        # King infrastructure or the defining Mime partner before treating ownership
        # as evidence for this specific leaf.
        return GOLD if shaped_king_shell or _has_joker(state, "mimejoker") else NEUTRAL

    if token == "mimejoker":
        # Mime alone does not make ordinary Kings useful. A Steel King gives Mime a
        # held-card ability to retrigger; alternatively an owned Baron makes every
        # held King a relevant retrigger target immediately.
        steel_king = any(
            _normalize(getattr(card, "enhancement", "")) == "steel"
            for card in kings
        )
        return GOLD if steel_king or _has_joker(state, "baronjoker") else NEUTRAL

    return NEUTRAL


def _baron_mime_held_engine_is_material(state) -> bool:
    """Return whether losing two held-card slots materially harms this exact leaf."""
    if (
        _has_joker(state, "baronjoker")
        and _baron_mime_relationship(state, "baronjoker") != NEUTRAL
    ):
        return True
    if (
        _has_joker(state, "mimejoker")
        and _baron_mime_relationship(state, "mimejoker") != NEUTRAL
    ):
        return True

    # Multiple Steel Kings are already a real held-card scoring shell even before
    # Baron/Mime arrives. One isolated Steel King remains below the specialization
    # floor and must not turn Stuntman into a hard conflict by itself.
    kings, _ = _baron_mime_king_shell(state)
    steel_kings = sum(
        _normalize(getattr(card, "enhancement", "")) == "steel"
        for card in kings
    )
    return steel_kings >= 2


def _high_card_has_obelisk_commitment(state) -> bool:
    """Require non-history build evidence before treating Obelisk as a conflict."""
    if _hand_level_is_invested(state, "HIGH_CARD"):
        return True

    if _owned_joker_tokens(state) & _HIGH_CARD_OBELISK_COMMITMENT_JOKERS:
        return True

    # Baron/Mime count only when their held engine already passes the same material
    # state checks used by the specialized leaf; ordinary unsupported ownership is
    # not enough to manufacture a High Card commitment.
    return _baron_mime_held_engine_is_material(state)


def _high_card_obelisk_conflicts(state) -> bool:
    return _hand_is_most_played(state, "HIGH_CARD") and _high_card_has_obelisk_commitment(state)


def _pair_has_independent_commitment(state) -> bool:
    """Return Pair evidence that does not come from generic repeat/small-hand support."""
    if _hand_level_is_invested(state, "PAIR"):
        return True
    return bool(_owned_joker_tokens(state) & _PAIR_DIRECT_COMMITMENT_JOKERS)


def _pair_conditional_support_relationship(state, token: str) -> str:
    if token not in (
        _PAIR_CONDITIONAL_SUPPORT_JOKERS | _PAIR_CONDITIONAL_FILLER_JOKERS
    ):
        return NEUTRAL
    if not _pair_has_independent_commitment(state):
        return NEUTRAL
    return SILVER if token in _PAIR_CONDITIONAL_SUPPORT_JOKERS else BRONZE


def _pair_obelisk_conflicts(state) -> bool:
    return _hand_is_most_played(state, "PAIR") and _pair_has_independent_commitment(state)


def _two_pair_has_independent_commitment(state) -> bool:
    """Return Two Pair evidence independent of generic pair/repetition support."""
    if _hand_level_is_invested(state, "TWO_PAIR"):
        return True
    return bool(_owned_joker_tokens(state) & _TWO_PAIR_DIRECT_COMMITMENT_JOKERS)


def _two_pair_conditional_support_relationship(state, token: str) -> str:
    if token not in _TWO_PAIR_CONDITIONAL_SUPPORT_JOKERS:
        return NEUTRAL
    return SILVER if _two_pair_has_independent_commitment(state) else NEUTRAL


def _two_pair_obelisk_conflicts(state) -> bool:
    return _hand_is_most_played(state, "TWO_PAIR") and _two_pair_has_independent_commitment(state)


def _other_poker_hand_obelisk_conflicts(state, strategy_id: str) -> bool:
    hand_key, commitment_jokers = _POKER_HAND_OBELISK_COMMITMENTS[strategy_id]
    committed = _hand_level_is_invested(state, hand_key) or bool(
        _owned_joker_tokens(state) & commitment_jokers
    )
    return committed and _hand_is_most_played(state, hand_key)


def _is_authoritative_conditional_relationship(strategy_id: str, item: object) -> bool:
    """Return whether conditional state is allowed to downgrade a static tier."""
    return (
        strategy_id == _BARON_MIME_STRATEGY_ID
        and _item_token(item) in _BARON_MIME_AUTHORITATIVE_CONDITIONAL_JOKERS
    )


def conditional_joker_relationship(
    state,
    strategy_id: str,
    item: object,
) -> str:
    """Resolve state-dependent Joker relationships from current public run state."""
    token = _item_token(item)

    if strategy_id in {
        "aces",
        "twos",
        "ten_four",
        "sixes",
        "jacks_hit_road",
        "queens_shoot_moon",
    }:
        rank_relationship = _rank_strategy_relationship(
            state,
            strategy_id,
            item,
        )
        if rank_relationship != NEUTRAL:
            return rank_relationship

    if strategy_id in {
        "hearts",
        "hearts_bloodstone_oops",
        "hearts_bloodstone_retrigger",
        "diamonds",
        "clubs",
        "clubs_onyx",
        "clubs_seeing_double",
        "spades",
        "blackboard",
        "raised_fist",
        "ancient_suit_rotation",
        "flower_pot",
        "flower_pot_splash",
        "flower_pot_smeared",
    }:
        section_three = _section_three_relationship(state, strategy_id, item)
        if section_three != NEUTRAL:
            return section_three

    if strategy_id in {
        "face_photochad",
        "face_triboulet_sock",
        "face_pareidolia",
        "face_held_economy",
        "face_business_card",
        "faceless_ride_bus",
        "faceless_discard_economy",
    }:
        branch_relationship = _face_branch_relationship(
            state,
            strategy_id,
            item,
        )
        if branch_relationship != NEUTRAL:
            return branch_relationship

    if strategy_id == "idol_exact":
        if token == "theidoljoker":
            return _idol_exact_relationship(state, item)
        if token in {"dnajoker", "tradingcardjoker"}:
            idol = _owned_idol(state)
            if idol is not None and _idol_exact_relationship(state, idol) != NEUTRAL:
                return SILVER

    if strategy_id == _HIGH_CARD_STRATEGY_ID and token == "obeliskjoker":
        return BANNED if _high_card_obelisk_conflicts(state) else NEUTRAL

    if strategy_id == _PAIR_STRATEGY_ID:
        if token == "obeliskjoker":
            return BANNED if _pair_obelisk_conflicts(state) else NEUTRAL
        if token in (
            _PAIR_CONDITIONAL_SUPPORT_JOKERS | _PAIR_CONDITIONAL_FILLER_JOKERS
        ):
            return _pair_conditional_support_relationship(state, token)

    if strategy_id == _TWO_PAIR_STRATEGY_ID:
        if token == "obeliskjoker":
            return BANNED if _two_pair_obelisk_conflicts(state) else NEUTRAL
        if token in _TWO_PAIR_CONDITIONAL_SUPPORT_JOKERS:
            return _two_pair_conditional_support_relationship(state, token)

    if token == "obeliskjoker" and strategy_id in _POKER_HAND_OBELISK_COMMITMENTS:
        return (
            BANNED
            if _other_poker_hand_obelisk_conflicts(state, strategy_id)
            else NEUTRAL
        )

    if strategy_id == _BARON_MIME_STRATEGY_ID:
        if token in _BARON_MIME_CONDITIONAL_POSITIVE_JOKERS:
            return _baron_mime_relationship(state, token)
        if token == "stuntmanjoker":
            return BANNED if _baron_mime_held_engine_is_material(state) else NEUTRAL

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
        if _is_authoritative_conditional_relationship(
            self._definition.strategy_id,
            item,
        ):
            return conditional
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
            if _is_authoritative_conditional_relationship(strategy_id, item):
                if conditional == NEUTRAL:
                    found.pop(strategy_id, None)
                else:
                    found[strategy_id] = conditional
                continue
            if conditional == NEUTRAL:
                continue
            previous = found.get(strategy_id, NEUTRAL)
            if _RELATIONSHIP_PRIORITY[conditional] > _RELATIONSHIP_PRIORITY[previous]:
                found[strategy_id] = conditional
        return found

    def evaluate_item(self, state, item: object, *, kind: str):
        self._relationship_state = state
        return super().evaluate_item(state, item, kind=kind)
