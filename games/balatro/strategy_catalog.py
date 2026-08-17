from __future__ import annotations

from types import MappingProxyType

from .strategy import StrategyDefinition


def _names(*values: str) -> frozenset[str]:
    normalized = {
        "".join(character for character in value.lower() if character.isalnum())
        for value in values
    }
    # Joker model classes conventionally append "Joker" to the in-game name
    # (TheDuoJoker, RunnerJoker, etc.). Keep strategy knowledge in game-name form
    # while accepting either representation from mechanics/live translation.
    return frozenset(
        {
            *normalized,
            *(f"{value}joker" for value in normalized if not value.endswith("joker")),
        }
    )


def _strategy(
    strategy_id: str,
    name: str,
    hand: str,
    *,
    gold_jokers=(),
    silver_jokers=(),
    bronze_jokers=(),
    silver_consumables=(),
    bronze_consumables=(),
    gold_planets=(),
    silver_planets=(),
    bronze_planets=(),
    conflicts=(),
) -> StrategyDefinition:
    return StrategyDefinition(
        strategy_id=strategy_id,
        name=name,
        primary_hands=(hand,),
        gold_jokers=_names(*gold_jokers),
        silver_jokers=_names(*silver_jokers),
        bronze_jokers=_names(*bronze_jokers),
        silver_consumables=_names(*silver_consumables),
        bronze_consumables=_names(*bronze_consumables),
        gold_planets=_names(*gold_planets),
        silver_planets=_names(*silver_planets),
        bronze_planets=_names(*bronze_planets),
        conflicts=_names(*conflicts),
    )


# Universal Balatro strategy knowledge. Deck/stake cartridges do not redefine this
# catalog; they only enable/disable or scale strategies for their environment.
UNIVERSAL_BALATRO_STRATEGIES = MappingProxyType(
    {
        "high_card": _strategy(
            "high_card",
            "High Card scaling",
            "HIGH_CARD",
            gold_jokers=("HalfJoker", "CardSharp"),
            silver_jokers=("GreenJoker", "RideTheBus", "Supernova"),
            bronze_jokers=("Banner", "BlueJoker"),
            bronze_consumables=("The Hanged Man", "Death"),
            gold_planets=("Pluto",),
        ),
        "pair": _strategy(
            "pair",
            "Pair scaling",
            "PAIR",
            gold_jokers=("TheDuo",),
            silver_jokers=("JollyJoker", "SlyJoker"),
            bronze_jokers=("HalfJoker", "Supernova"),
            silver_consumables=("Strength", "Death"),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Mercury",),
        ),
        "two_pair": _strategy(
            "two_pair",
            "Two Pair scaling",
            "TWO_PAIR",
            gold_jokers=("SpareTrousers",),
            silver_jokers=("MadJoker", "CleverJoker"),
            bronze_jokers=("TheDuo", "Supernova"),
            silver_consumables=("Strength", "Death"),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Uranus",),
        ),
        "three_kind": _strategy(
            "three_kind",
            "Three of a Kind scaling",
            "THREE_OF_A_KIND",
            gold_jokers=("TheTrio",),
            silver_jokers=("ZanyJoker", "WilyJoker"),
            bronze_jokers=("TheDuo", "Supernova"),
            silver_consumables=("Strength", "Death"),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Venus",),
        ),
        "straight": _strategy(
            "straight",
            "Straight scaling",
            "STRAIGHT",
            gold_jokers=("TheOrder", "Runner"),
            silver_jokers=("CrazyJoker", "DeviousJoker", "Shortcut"),
            bronze_jokers=("FourFingers", "Supernova"),
            silver_consumables=("Strength", "Death"),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Saturn",),
        ),
        "flush": _strategy(
            "flush",
            "Flush scaling",
            "FLUSH",
            gold_jokers=("TheTribe",),
            silver_jokers=("DrollJoker", "CraftyJoker", "FourFingers"),
            bronze_jokers=("Bloodstone", "Arrowhead", "OnyxAgate", "RoughGem"),
            silver_consumables=("The Star", "The Moon", "The Sun", "The World"),
            bronze_consumables=("Death", "The Hanged Man"),
            gold_planets=("Jupiter",),
        ),
        "full_house": _strategy(
            "full_house",
            "Full House scaling",
            "FULL_HOUSE",
            gold_jokers=("TheDuo", "TheTrio"),
            silver_jokers=("JollyJoker", "ZanyJoker", "SlyJoker", "WilyJoker"),
            bronze_jokers=("Supernova",),
            silver_consumables=("Strength", "Death"),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Earth",),
        ),
        "four_kind": _strategy(
            "four_kind",
            "Four of a Kind scaling",
            "FOUR_OF_A_KIND",
            gold_jokers=("TheFamily",),
            silver_jokers=("TheTrio", "ZanyJoker", "WilyJoker"),
            bronze_jokers=("TheDuo", "Supernova"),
            silver_consumables=("Strength", "Death"),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Mars",),
        ),
        "straight_flush": _strategy(
            "straight_flush",
            "Straight Flush scaling",
            "STRAIGHT_FLUSH",
            gold_jokers=("TheOrder", "TheTribe"),
            silver_jokers=("FourFingers", "Shortcut", "Runner"),
            bronze_jokers=("CrazyJoker", "DrollJoker", "DeviousJoker", "CraftyJoker"),
            silver_consumables=(
                "Strength",
                "Death",
                "The Star",
                "The Moon",
                "The Sun",
                "The World",
            ),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Neptune",),
        ),
        "five_kind": _strategy(
            "five_kind",
            "Five of a Kind scaling",
            "FIVE_OF_A_KIND",
            gold_jokers=("TheFamily", "TheTrio"),
            silver_consumables=("Strength", "Death"),
            bronze_consumables=("The Hanged Man",),
            gold_planets=("Planet X",),
        ),
        "flush_house": _strategy(
            "flush_house",
            "Flush House scaling",
            "FLUSH_HOUSE",
            gold_jokers=("TheTribe", "TheTrio", "TheDuo"),
            silver_jokers=("FourFingers",),
            silver_consumables=(
                "Death",
                "The Star",
                "The Moon",
                "The Sun",
                "The World",
            ),
            gold_planets=("Ceres",),
        ),
        "flush_five": _strategy(
            "flush_five",
            "Flush Five scaling",
            "FLUSH_FIVE",
            gold_jokers=("TheTribe", "TheFamily"),
            silver_jokers=("TheTrio",),
            silver_consumables=(
                "Death",
                "The Star",
                "The Moon",
                "The Sun",
                "The World",
            ),
            gold_planets=("Eris",),
        ),
    }
)
