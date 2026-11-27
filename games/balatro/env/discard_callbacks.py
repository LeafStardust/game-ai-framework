"""Apply the owned callbacks to a complete discard before moving the cards."""

from games.balatro.card import BalatroCard
from games.balatro.env.transition import HeadlessRunState
from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.jokers.castle import CastleJoker
from games.balatro.jokers.faceless_joker import FacelessJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.mail_in_rebate import MailInRebateJoker


def apply_discard_callbacks(run: HeadlessRunState, cards: list[BalatroCard]) -> None:
    """Apply one batch-equivalent callback on the already isolated run."""
    jokers = [
        joker for joker in run.public.jokers
        if type(joker) in (CastleJoker, FacelessJoker, GreenJoker, MailInRebateJoker)
    ]
    if not jokers or not cards:
        return
    context = JokerContext(
        state=run.public,
        cards=cards,
        trigger="DISCARD",
        event=BalatroEvent(BalatroEventType.CARDS_DISCARDED, cards),
        data={"hand_rules": hand_rules_for_state(run.public)},
    )
    for joker in jokers:
        joker.apply(context)
