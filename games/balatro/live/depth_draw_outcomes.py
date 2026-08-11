from __future__ import annotations

from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel


class DepthAwarePublicDrawOutcomeModel:
    """Use fuller sampling at the root and a smaller sample below it.

    Live expectimax evaluates several root actions against the same authoritative
    remaining-deck population. After a hypothetical play/discard, that public
    population shrinks, so population size provides a simple depth boundary
    without exposing or depending on hidden deck order.

    Exact outcome spaces stay exact because both delegated models use the same
    ``exact_combination_limit``. Only sampled spaces use fewer branches below
    the root.
    """

    def __init__(
        self,
        *,
        exact_combination_limit: int,
        root_sample_count: int,
        child_sample_count: int,
        seed: int = 0,
    ):
        if child_sample_count < 1:
            raise ValueError("child_sample_count must be positive")

        self.exact_combination_limit = int(exact_combination_limit)
        self.sample_count = int(root_sample_count)
        self.child_sample_count = int(child_sample_count)
        self.seed = int(seed)
        self._root_population_size: int | None = None
        self._root = PublicDrawOutcomeModel(
            exact_combination_limit=self.exact_combination_limit,
            sample_count=self.sample_count,
            seed=self.seed,
        )
        self._child = PublicDrawOutcomeModel(
            exact_combination_limit=self.exact_combination_limit,
            sample_count=self.child_sample_count,
            seed=self.seed,
        )

    def distribution(self, composition, draws: int):
        population_size = int(composition.total_cards)
        if self._root_population_size is None:
            self._root_population_size = population_size

        model = (
            self._root
            if population_size == self._root_population_size
            else self._child
        )
        return model.distribution(composition, draws)

    def remaining_cards(self, composition, outcome):
        return self._root.remaining_cards(composition, outcome)

    @staticmethod
    def card_from_signature(signature):
        return PublicDrawOutcomeModel.card_from_signature(signature)
