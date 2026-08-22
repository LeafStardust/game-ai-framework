"""Explicit disposition registry for Jokers not represented purely by Bond quota.

Coverage is broader than quota: a Joker may be represented as a Bond contributor,
motif/composer component, or tactical/support piece. Being scalable does not by
itself justify Bond authority.
"""
from __future__ import annotations

BOND_WIRED = {
    "Superposition": ("straight", "tarot"),
    "Blackboard": ("held_cards",),
    "Square Joker": ("two_pair",),
    "Erosion": ("deck_thinning",),
    "Vampire": ("vampire",),
    "Cloud 9": ("cash",),
    "8 Ball": ("tarot",),
    "Ancient Joker": ("flush",),
}

MOTIF_OR_COMPOSER = {
    "The Idol": "dynamic rank+suit payoff for highly concentrated decks",
    "Hiker": "permanent per-card quality growth, not an independent strategic axis",
    "Flower Pot": "multi-suit scoring condition; explicitly removed from Four-of-a-Kind quota",
    "Perkeo": "consumable duplication identity depends on the held consumable; resolve at composer/motif level",
    "Baseball Card": "rarity-composition payoff rather than a Bond-specific axis",
    "Joker Stencil": "empty-slot composition payoff rather than a Bond-specific axis",
}

TACTICAL_SUPPORT = {
    "Seance": "niche Straight-Flush-triggered Spectral generation; does not materially establish the Straight Flush win condition",
    "Campfire": "sell-to-scale tactical shop engine; intentionally unsupported as a persistent Bond",
    "Obelisk": "rotation scaler; intentionally unsupported due to brittle planning cost versus value",
    "Flash Card": "reroll scaler; shop/economy tactical valuation rather than Bond authority",
    "Red Card": "pack-skip scaler; tactical shop valuation rather than persistent deck architecture",
    "Seltzer": "temporary ten-hand retrigger window; tactical Played-Retrigger support but not persistent Bond development",
    "Seeing Double": "broad multi-suit XMult condition compatible with several hand families; composer-level tactical payoff",
}

GENERIC_OR_TACTICAL = {
    "Abstract Joker", "Acrobat", "Blue Joker", "Cavendish", "Chaos the Clown",
    "Chicot", "Credit Card", "Drunkard", "Gros Michel", "Ice Cream",
    "Invisible Joker", "Joker", "Juggler", "Loyalty Card", "Luchador",
    "Matador", "Merry Andy", "Misprint", "Mr. Bones", "Mystic Summit",
    "Odd Todd", "Popcorn", "Showman", "Splash", "To Do List", "Troubadour",
    "Turtle Bean",
}

def disposition(name: str) -> str:
    if name in BOND_WIRED: return "bond"
    if name in MOTIF_OR_COMPOSER: return "motif_or_composer"
    if name in TACTICAL_SUPPORT: return "tactical_support"
    if name in GENERIC_OR_TACTICAL: return "generic_or_tactical"
    return "unclassified"
