from games.balatro.card import BalatroCard


class HandProbability:
    """
    Estimates probabilities related to card draws.
    """

    def remaining_cards(
        self,
        deck_size: int,
        hand_size: int
    ) -> int:

        return deck_size - hand_size


    def draw_probability(
        self,
        desired_cards: int,
        total_cards: int,
        draws: int
    ) -> float:

        if total_cards <= 0:
            return 0.0

        if desired_cards <= 0:
            return 0.0

        return min(
            desired_cards / total_cards * draws,
            1.0
        )