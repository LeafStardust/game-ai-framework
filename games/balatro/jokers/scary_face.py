from games.balatro.hand_rules import card_is_face
from games.balatro.joker import Joker, JokerContext


class ScaryFaceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        rules = context.data.get("hand_rules", {})
        faces = sum(
            card_is_face(card, rules)
            for card in scoring_cards
        )

        context.score.chips += faces * 30

        return context
