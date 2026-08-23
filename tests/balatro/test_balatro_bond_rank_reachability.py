from types import SimpleNamespace

from games.balatro.bonds.evaluation import EVALUATORS
from games.balatro.bonds.model import BondRank
from games.balatro.bonds.realization import FROZEN_BOND_IDS


JOKERS = (
    "burntjoker", "blueprintjoker", "brainstormjoker", "spacejoker",
    "baronjoker", "shootthemoonjoker", "raisedfistjoker", "blackboardjoker",
    "mimejoker", "steeljoker", "theduojoker", "jollyjoker", "slyjoker",
    "halfjoker", "stuntmanjoker", "scholarjoker", "fibonaccijoker", "dnajoker",
    "greenjoker", "burglarjoker", "delayedgratificationjoker", "ramenjoker",
    "bannerjoker", "bulljoker", "bootstrapsjoker", "rocketjoker", "goldenjoker",
    "tothemoonjoker", "satellitejoker", "reservedparkingjoker", "cloud9joker",
    "luckycatjoker", "oopsall6sjoker", "glassjoker", "pareidoliajoker",
    "sockandbuskinjoker", "photographjoker", "scaryfacejoker", "smileyfacejoker",
    "businesscardjoker", "sparetrousers", "squarejoker", "thetrio", "zanyjoker",
    "wilyjoker", "thefamily", "madjoker", "cleverjoker", "theorder", "crazyjoker",
    "deviousjoker", "shortcut", "fourfingers", "runner", "superposition",
    "thetribe", "drolljoker", "craftyjoker", "smearedjoker", "hackjoker",
    "hangingchad", "duskjoker", "stonejoker", "marblejoker", "goldenticket",
    "midasmask", "erosionjoker", "tradingcard", "sixthsense", "certificate",
    "hologramjoker", "weejoker", "evenstevenjoker", "walkietalkiejoker",
    "bloodstone", "lustyjoker", "arrowhead", "wrathfuljoker", "onyxagate",
    "gluttonousjoker", "roughgem", "greedyjoker", "triboulet", "hittheroad",
    "cartomancer", "vagabond", "hallucination", "fortuneteller", "8ball",
    "constellation", "astronomer", "yorick", "castle", "mailinrebate",
    "facelessjoker", "throwback", "dietcola", "swashbuckler", "giftcard",
    "eggjoker", "ceremonialdagger", "madness", "riffraff", "canio",
    "cardsharp", "supernova", "driverslicense", "ridethebusjoker", "vampire",
)

VOUCHERS = (
    "telescope", "tarotmerchant", "tarottycoon", "planetmerchant", "planettycoon",
)

HAND_TYPES = (
    "HIGH_CARD", "PAIR", "TWO_PAIR", "THREE_OF_A_KIND", "FOUR_OF_A_KIND",
    "STRAIGHT", "FLUSH", "FULL_HOUSE", "STRAIGHT_FLUSH", "FIVE_OF_A_KIND",
    "FLUSH_HOUSE", "FLUSH_FIVE",
)


def card(rank="2", suit="Hearts", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement, seal=seal)


def maximal_deck():
    deck = []
    for rank in ("A", "K", "Q", "J", "2", "3", "4", "5"):
        deck.extend(card(rank=rank, suit="Hearts") for _ in range(50))
    deck.extend(card(rank="2", suit="Hearts", enhancement="wild") for _ in range(60))
    deck.extend(card(rank="K", suit="Spades", enhancement="steel", seal="red") for _ in range(20))
    deck.extend(card(rank="2", suit="Clubs", enhancement="lucky") for _ in range(20))
    deck.extend(card(rank="K", suit="Diamonds", enhancement="glass") for _ in range(20))
    deck.extend(card(rank="2", suit="Hearts", enhancement="gold") for _ in range(20))
    deck.extend(card(rank="2", suit="Clubs", enhancement="stone") for _ in range(20))
    deck.extend(card(rank="A", suit="Spades", seal="blue") for _ in range(20))
    return tuple(deck)


def maximal_state():
    return SimpleNamespace(
        jokers=JOKERS,
        vouchers=VOUCHERS,
        owned_deck=maximal_deck(),
        hand_levels={hand: 30 for hand in HAND_TYPES},
        hand_play_counts={hand: 100 for hand in HAND_TYPES},
        money=1000,
        hand_size=12,
        discards_per_round=6,
        glass_cards_destroyed=100,
        blinds_skipped=100,
        joker_sell_value_total=100,
        jokers_destroyed=100,
        cards_destroyed=100,
        vampire_enhancements_consumed=100,
    )


def no_face_capstone_state():
    state = maximal_state()
    state.owned_deck = tuple(card(rank="2", suit="Hearts") for _ in range(52))
    return state


def test_every_frozen_bond_has_an_r5_reachable_structural_state():
    state = maximal_state()
    failures = {}
    for bond_id in FROZEN_BOND_IDS:
        candidate_state = no_face_capstone_state() if bond_id == "no_face_cards" else state
        development = EVALUATORS[bond_id](candidate_state)
        if development.rank != BondRank.R5:
            failures[bond_id] = (development.rank, development.contribution, development.next_rank_threshold)
    assert not failures, failures


def test_low_ranks_r5_is_reachable_without_extra_joker_capacity():
    state = SimpleNamespace(
        jokers=("hackjoker", "weejoker", "fibonaccijoker", "evenstevenjoker", "walkietalkiejoker"),
        owned_deck=tuple(card(rank="2") for _ in range(30)),
    )
    development = EVALUATORS["low_ranks"](state)
    assert development.rank == BondRank.R5
    assert development.contribution == 27.0


def test_cash_r5_is_reachable_with_five_ordinary_joker_slots():
    state = SimpleNamespace(
        jokers=("bulljoker", "bootstrapsjoker", "rocketjoker", "goldenjoker", "tothemoonjoker"),
        owned_deck=(),
        money=150,
    )
    development = EVALUATORS["cash"](state)
    assert development.rank == BondRank.R5
    assert development.contribution == 27.0


def test_discard_r5_does_not_require_negative_joker_capacity():
    state = SimpleNamespace(
        jokers=("yorick", "castle", "mailinrebate", "facelessjoker", "hittheroad"),
        owned_deck=(),
        discards_per_round=6,
    )
    development = EVALUATORS["discard"](state)
    assert development.rank == BondRank.R5
    assert development.contribution == 26.0
