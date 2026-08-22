"""Explicit disposition registry for Jokers not represented purely by Bond quota.

This prevents coverage from being confused with quota. A Joker may be strategically
accounted for as a Bond contributor, motif component, or tactical/support piece.
The registry is intentionally conservative: being scalable does not make a Bond.
"""
from __future__ import annotations

BOND_WIRED = {
    "Superposition": ("straight", "tarot"),
    "Blackboard": ("held_cards",),
    "Square Joker": ("two_pair",),
    "Erosion": ("deck_thinning",),
    "Vampire": ("vampire",),
}

MOTIF_OR_COMPOSER = {
    "Ancient Joker": "rotating-suit scoring payoff; evaluate against current suit/flush composition rather than permanent suit quota",
    "The Idol": "dynamic rank+suit payoff for highly concentrated decks",
    "Hiker": "permanent per-card quality growth, not an independent strategic axis",
    "Flower Pot": "multi-suit scoring condition; explicitly removed from Four-of-a-Kind quota",
}

TACTICAL_SUPPORT = {
    "Seance": "niche Straight-Flush-triggered Spectral generation; does not materially establish the Straight Flush win condition",
    "Campfire": "sell-to-scale tactical shop engine; intentionally unsupported as a persistent Bond",
    "Obelisk": "rotation scaler; intentionally unsupported due to brittle planning cost versus value",
    "Flash Card": "reroll scaler; shop/economy tactical valuation rather than Bond authority",
    "Red Card": "pack-skip scaler; tactical shop valuation rather than persistent deck architecture",
}

# Generic, temporary, boss utility, slot/hand modifiers, or standalone value pieces.
GENERIC_OR_TACTICAL = {
    "8 Ball", "Abstract Joker", "Acrobat", "Baseball Card", "Blue Joker",
    "Cavendish", "Chaos the Clown", "Chicot", "Cloud 9", "Credit Card",
    "Drunkard", "Gros Michel", "Ice Cream", "Invisible Joker", "Joker",
    "Joker Stencil", "Juggler", "Loyalty Card", "Luchador", "Matador",
    "Merry Andy", "Misprint", "Mr. Bones", "Mystic Summit", "Odd Todd",
    "Perkeo", "Popcorn", "Seeing Double", "Seltzer", "Showman", "Splash",
    "To Do List", "Troubadour", "Turtle Bean",
}

def disposition(name: str) -> str:
    if name in BOND_WIRED: return "bond"
    if name in MOTIF_OR_COMPOSER: return "motif_or_composer"
    if name in TACTICAL_SUPPORT: return "tactical_support"
    if name in GENERIC_OR_TACTICAL: return "generic_or_tactical"
    return "unclassified"
