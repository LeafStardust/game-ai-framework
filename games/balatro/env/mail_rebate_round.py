"""Own the retained target rank used by Mail-In Rebate."""

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.mail_in_rebate import MAIL_REBATE_RANKS, MailInRebateJoker


def reset_mail_rebate_rank(run: HeadlessRunState) -> None:
    """Roll from the non-Stone permanent cards in retained creation order."""
    cards = [card for card in run.require_playing_card_order() if not card.is_stone]
    if not cards or any(
        type(card.rank) is not str or card.rank not in MAIL_REBATE_RANKS for card in cards
    ):
        raise HeadlessTransitionError("Mail-In Rebate requires exact eligible permanent ranks")

    index = run.rng.pseudorandom_element_index(len(cards), f"mail{run.public.ante}")
    rank = cards[index].rank
    run.mail_rebate_rank = rank
    for joker in run.public.jokers:
        if type(joker) is MailInRebateJoker:
            joker.rank = rank
