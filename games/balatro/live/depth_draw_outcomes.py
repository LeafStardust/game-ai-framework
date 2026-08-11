from __future__ import annotations

from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel


class DepthAwarePublicDrawOutcomeModel:
    """Use fuller public draw branching at the root and tighter branching below it.

    Live expectimax evaluates several root actions against the same authoritative
    remaining-deck population. After a hypothetical play/discard, that public
    population shrinks, so population size provides a simple depth boundary
    without exposing or depending on hidden deck order.

    Root and child nodes may use different exact-enumeration limits as well as
    different sample counts. By default child nodes enumerate only outcome spaces
    of at most eight combinations exactly; larger child spaces are sampled. This
    prevents common one-card child redraws (roughly 40 possible cards early in a
    run) from exploding merely because the root exact limit is generous.
    """

    DEFAULT_CHILD_EXACT_COMBINATION_LIMIT = 8

    def __init__(
        self,
        *,
        exact_combination_limit: int,
        root_sample_count: int,
        child_sample_count: int,
        child_exact_combination_limit: int | None = None,
        seed: int = 0,
    ):
        if exact_combination_limit < 1:
            raise ValueError("exact_combination_limit must be positive")
        if root_sample_count < 1:
            raise ValueError("root_sample_count must be positive")
        if child_sample_count < 1:
            raise ValueError("child_sample_count must be positive")
        if (
            child_exact_combination_limit is not None
            and child_exact_combination_limit < 1
        ):
            raise ValueError("child_exact_combination_limit must be positive")

        self.exact_combination_limit = int(exact_combination_limit)
        default_child_limit = min(
            self.exact_combination_limit,
            self.DEFAULT_CHILD_EXACT_COMBINATION_LIMIT,
        )
        self.child_exact_combination_limit = int(
            default_child_limit
            if child_exact_combination_limit is None
            else child_exact_combination_limit
        )
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
            exact_combination_limit=self.child_exact_combination_limit,
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
