from games.balatro.hand_rules import card_matches_suit
from games.balatro.joker import Joker, JokerContext


class SeeingDoubleJoker(Joker):

    OTHER_SUITS = ("Hearts", "Diamonds", "Spades")

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        rules = context.data.get("hand_rules", {})
        scoring_cards = list(context.data.get("scoring_cards", context.cards))

        for club_index, club_card in enumerate(scoring_cards):
            if not card_matches_suit(club_card, "Clubs", rules):
                continue
            for other_index, other_card in enumerate(scoring_cards):
                if other_index == club_index:
                    continue
                if any(
                    card_matches_suit(other_card, suit, rules)
                    for suit in self.OTHER_SUITS
                ):
                    context.score.x_mult *= 2
                    return context

        return context
