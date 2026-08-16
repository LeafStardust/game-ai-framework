STANDARD_STARTING_DECK_SIZES = {
    "BASE": 52,
    "RED": 52,
    "BLUE": 52,
    "YELLOW": 52,
    "GREEN": 52,
    "BLACK": 52,
    "MAGIC": 52,
    "NEBULA": 52,
    "GHOST": 52,
    "ABANDONED": 40,
    "CHECKERED": 52,
    "ZODIAC": 52,
    "PAINTED": 52,
    "ANAGLYPH": 52,
    "PLASMA": 52,
    "ERRATIC": 52,
}


def starting_deck_size_for_name(deck_name: str | None) -> int | None:
    if not isinstance(deck_name, str) or not deck_name:
        return None
    return STANDARD_STARTING_DECK_SIZES.get(deck_name.upper())
