class HandProbability:
    """
    Estimates probabilities related to card draws.
    """

    def remaining_cards(
        self,
        deck: list
    ) -> int:

        return len(deck)


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
            (desired_cards / total_cards) * draws,
            1.0
        )