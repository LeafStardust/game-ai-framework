"""Retain the round target used by Castle in the headless agent."""

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.castle import CASTLE_SUITS, CastleJoker


def reset_castle_round_suit(run: HeadlessRunState) -> None:
    """Reset the target on an already isolated run at initialization or round win."""
    eligible = [card for card in run.require_playing_card_order() if not card.is_stone]
    if any(not isinstance(card.suit, str) or card.suit not in CASTLE_SUITS for card in eligible):
        raise HeadlessTransitionError("Castle reset requires exact permanent card suits")

    suit = "Spades"
    if eligible:
        index = run.rng.pseudorandom_element_index(len(eligible), f"cas{run.public.ante}")
        suit = eligible[index].suit

    run.castle_suit = suit
    for joker in run.public.jokers:
        if type(joker) is CastleJoker:
            joker.suit = suit
