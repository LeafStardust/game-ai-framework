from games.balatro.joker import Joker, JokerContext


class MailInRebateJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "DISCARD":
            return context

        rank = context.data.get("mail_in_rebate_rank")

        discarded = sum(
            card.rank == rank
            for card in context.cards
        )

        context.data["money"] = (
            context.data.get("money", 0) + discarded * 3
        )

        return context