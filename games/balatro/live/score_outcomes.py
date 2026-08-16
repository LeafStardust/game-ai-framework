from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import product
from math import comb

from games.balatro.hand import PokerHand
from games.balatro.hand_rules import (
    card_is_face,
    card_matches_suit,
    hand_rules_for_state,
)
from games.balatro.live.copy_projection import (
    COPY_JOKER_CLASS_NAMES,
    resolve_copy_target,
)
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.scoring import BalatroScorer


@dataclass(frozen=True)
class ScoreOutcome:
    score: int
    probability: float
    state_after_scoring: object | None = field(
        default=None,
        compare=False,
        repr=False,
    )


@dataclass(frozen=True)
class ScoreOutcomeDistribution:
    """Discrete scoring outcomes for one visible play."""

    outcomes: tuple[ScoreOutcome, ...]
    random_sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.outcomes:
            raise ValueError("score outcome distribution requires at least one outcome")
        total_probability = sum(outcome.probability for outcome in self.outcomes)
        if abs(total_probability - 1.0) > 1e-9:
            raise ValueError(
                "score outcome probabilities must sum to 1.0, got "
                f"{total_probability}"
            )

    @property
    def minimum(self) -> int:
        return min(outcome.score for outcome in self.outcomes)

    @property
    def maximum(self) -> int:
        return max(outcome.score for outcome in self.outcomes)

    @property
    def expected(self) -> float:
        return sum(
            outcome.score * outcome.probability
            for outcome in self.outcomes
        )

    @property
    def deterministic(self) -> bool:
        return len(self.outcomes) == 1

    def probability_at_least(self, threshold: int | float) -> float:
        return sum(
            outcome.probability
            for outcome in self.outcomes
            if outcome.score >= threshold
        )


@dataclass(frozen=True)
class ScoreProjectionTransition:
    """Score distribution plus the isolated post-scoring branch state."""

    distribution: ScoreOutcomeDistribution
    state_after_scoring: object | None
    unsupported_jokers: tuple[str, ...] = ()

    @property
    def joker_projection_complete(self) -> bool:
        return not self.unsupported_jokers


@dataclass(frozen=True)
class _LuckyBranch:
    mult_results: tuple[bool, ...]
    money_successes: int
    successful_triggers: int
    probability: float


@dataclass(frozen=True)
class _BloodstoneBranch:
    results: tuple[bool, ...]
    probability: float


@dataclass(frozen=True)
class _GlassBranch:
    broken_indices: tuple[int, ...]
    probability: float


class _ProjectedStochasticScorer(BalatroScorer):
    """Replay explicit scored-card/Joker RNG branches without hidden RNG."""

    def __init__(
        self,
        lucky_mult_results: tuple[bool, ...] = (),
        bloodstone_results: tuple[bool, ...] = (),
        misprint_results: tuple[int, ...] = (),
    ):
        self._lucky_mult_results = tuple(bool(value) for value in lucky_mult_results)
        self._lucky_mult_index = 0
        self._bloodstone_result_iter = iter(
            tuple(bool(value) for value in bloodstone_results)
        )
        self._misprint_results = tuple(int(value) for value in misprint_results)

    def score(
        self,
        hand,
        state=None,
        cards=None,
        *,
        include_card_chips: bool = False,
        resolve_random_effects: bool = True,
        joker_data: dict | None = None,
    ):
        branch_data = dict(joker_data or {})
        branch_data["misprint_results"] = iter(self._misprint_results)
        return super().score(
            hand,
            state,
            cards=cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=resolve_random_effects,
            joker_data=branch_data,
        )

    def _apply_single_card_modifier(
        self,
        score,
        card,
        *,
        resolve_random_effects: bool = True,
    ) -> None:
        if (
            getattr(card, "enhancement", None) != "Lucky"
            or resolve_random_effects
        ):
            super()._apply_single_card_modifier(
                score,
                card,
                resolve_random_effects=resolve_random_effects,
            )
            return

        success = False
        if self._lucky_mult_index < len(self._lucky_mult_results):
            success = self._lucky_mult_results[self._lucky_mult_index]
        self._lucky_mult_index += 1

        if success:
            score.mult += 20

        edition = getattr(card, "edition", None)
        if edition == "Foil":
            score.chips += 50
        elif edition == "Holographic":
            score.mult += 10
        elif edition == "Polychrome":
            score.x_mult *= 1.5
            self._fold_x_mult(score)

    def _apply_scoring_card_phase(
        self,
        score,
        hand,
        state,
        played_cards,
        scoring_cards,
        *,
        extra_retriggers: int = 0,
        resolve_random_effects: bool = True,
        context_data: dict | None = None,
    ) -> None:
        branch_data = dict(context_data or {})
        branch_data["bloodstone_results"] = self._bloodstone_result_iter
        super()._apply_scoring_card_phase(
            score,
            hand,
            state,
            played_cards,
            scoring_cards,
            extra_retriggers=extra_retriggers,
            resolve_random_effects=resolve_random_effects,
            context_data=branch_data,
        )


class VisibleCardScoreOutcomeModel:
    """Project public visible scoring without consuming Balatro's hidden RNG."""

    LUCKY_MULT_PROBABILITY = 0.2
    LUCKY_MONEY_PROBABILITY = 1.0 / 15.0
    LUCKY_MULT_BONUS = 20
    LUCKY_MONEY_REWARD = 20
    LUCKY_CAT_X_MULT_GAIN = 0.25
    BLOODSTONE_PROBABILITY = 0.5
    GLASS_BREAK_PROBABILITY = 0.25
    CANIO_X_MULT_GAIN = 1.0
    MISPRINT_RESULT_COUNT = 24

    def __init__(
        self,
        scorer: BalatroScorer | None = None,
        joker_projector: LiveJokerScoreProjector | None = None,
    ):
        self.scorer = scorer or BalatroScorer()
        self.joker_projector = joker_projector or LiveJokerScoreProjector(self.scorer)

    def project(
        self,
        hand: PokerHand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreOutcomeDistribution:
        return self.project_transition(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
        ).distribution

    def project_transition(
        self,
        hand: PokerHand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreProjectionTransition:
        joker_projection = self.joker_projector.score(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
        base = joker_projection.score
        copied_cards = joker_projection.cards_after_copy
        projected_state = joker_projection.state_after_scoring
        extra_retriggers = joker_projection.played_card_retriggers
        rules = hand_rules_for_state(projected_state)

        lucky_triggers = self._lucky_scoring_triggers(
            hand,
            copied_cards,
            rules=rules,
            extra_retriggers=extra_retriggers,
        )
        bloodstone_triggers = self._bloodstone_scoring_triggers(
            hand,
            copied_cards,
            projected_state,
            rules=rules,
            extra_retriggers=extra_retriggers,
        )
        glass_cards = self._glass_scoring_cards(
            hand,
            copied_cards,
            rules=rules,
        )
        misprint_triggers = self._misprint_activation_count(projected_state)

        if (
            lucky_triggers == 0
            and bloodstone_triggers == 0
            and not glass_cards
            and misprint_triggers == 0
        ):
            distribution = ScoreOutcomeDistribution(
                outcomes=(
                    ScoreOutcome(
                        base.total,
                        1.0,
                        state_after_scoring=projected_state,
                    ),
                ),
            )
            return ScoreProjectionTransition(
                distribution=distribution,
                state_after_scoring=projected_state,
                unsupported_jokers=joker_projection.unsupported_jokers,
            )

        joint_lucky_state = bool(
            lucky_triggers and self._requires_joint_lucky_state(projected_state)
        )
        lucky_branches = self._lucky_branches(
            lucky_triggers,
            projected_state,
        )
        bloodstone_branches = self._bloodstone_branches(
            bloodstone_triggers,
            projected_state,
        )
        glass_branches = self._glass_branches(
            len(glass_cards),
            projected_state,
        )
        grouped: dict[tuple, list] = {}

        for lucky_branch in lucky_branches:
            for bloodstone_branch in bloodstone_branches:
                if lucky_triggers or bloodstone_triggers or misprint_triggers:
                    zero_results = (0,) * misprint_triggers
                    branch_projection = self._project_stochastic_branch(
                        hand,
                        state,
                        cards,
                        include_card_chips=include_card_chips,
                        lucky_branch=lucky_branch,
                        bloodstone_branch=bloodstone_branch,
                        misprint_results=zero_results,
                    )
                    zero_score = branch_projection.score
                    score_state = branch_projection.state_after_scoring
                    branch_probability = (
                        lucky_branch.probability
                        * bloodstone_branch.probability
                    )
                else:
                    zero_score = base
                    score_state = projected_state
                    branch_probability = 1.0

                misprint_distribution = ((Fraction(0), 1.0),)
                if misprint_triggers:
                    coefficients = self._misprint_coefficients(
                        hand,
                        state,
                        cards,
                        include_card_chips=include_card_chips,
                        lucky_branch=lucky_branch,
                        bloodstone_branch=bloodstone_branch,
                        zero_score=zero_score,
                        triggers=misprint_triggers,
                    )
                    misprint_distribution = self._misprint_increment_distribution(
                        coefficients
                    )

                for glass_branch in glass_branches:
                    branch_state = self._glass_branch_state(
                        score_state,
                        glass_branch,
                        glass_cards,
                        rules=rules,
                    )
                    for increment, misprint_probability in misprint_distribution:
                        score = self._score_with_misprint_increment(
                            zero_score,
                            increment,
                        )
                        probability = (
                            branch_probability
                            * glass_branch.probability
                            * misprint_probability
                        )
                        if joint_lucky_state:
                            key = (
                                score,
                                lucky_branch.money_successes,
                                lucky_branch.successful_triggers,
                                glass_branch.broken_indices,
                            )
                        else:
                            key = (score, glass_branch.broken_indices)

                        if key not in grouped:
                            grouped[key] = [0.0, branch_state]
                        grouped[key][0] += probability

        outcomes = tuple(
            ScoreOutcome(
                score=key[0],
                probability=grouped[key][0],
                state_after_scoring=grouped[key][1],
            )
            for key in sorted(grouped)
            if grouped[key][0] > 0.0
        )

        random_sources: list[str] = []
        if lucky_triggers:
            if joint_lucky_state:
                random_sources.append(f"Lucky effects x{lucky_triggers}")
            else:
                random_sources.append(f"Lucky mult x{lucky_triggers}")
        if bloodstone_triggers:
            random_sources.append(f"Bloodstone x{bloodstone_triggers}")
        if glass_cards:
            random_sources.append(f"Glass break x{len(glass_cards)}")
        if misprint_triggers:
            random_sources.append(f"Misprint x{misprint_triggers}")

        distribution = ScoreOutcomeDistribution(
            outcomes=outcomes,
            random_sources=tuple(random_sources),
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=projected_state,
            unsupported_jokers=joker_projection.unsupported_jokers,
        )

    def _lucky_scoring_triggers(
        self,
        hand: PokerHand,
        cards,
        *,
        rules: dict | None = None,
        extra_retriggers: int = 0,
    ) -> int:
        triggers = 0
        for card in self.scorer.scoring_cards(hand, cards, rules=rules):
            if self.scorer.is_card_debuffed(card):
                continue
            if getattr(card, "enhancement", None) != "Lucky":
                continue
            triggers += self.scorer._played_card_trigger_count(
                card,
                extra_retriggers,
            )
        return triggers

    def _bloodstone_scoring_triggers(
        self,
        hand: PokerHand,
        cards,
        state,
        *,
        rules: dict | None = None,
        extra_retriggers: int = 0,
    ) -> int:
        bloodstone_count = len(self._jokers_named(state, "BloodstoneJoker"))
        if bloodstone_count <= 0:
            return 0

        heart_triggers = 0
        for card in self.scorer.scoring_cards(hand, cards, rules=rules):
            if self.scorer.is_card_debuffed(card):
                continue
            if not card_matches_suit(card, "Hearts", rules):
                continue
            heart_triggers += self.scorer._played_card_trigger_count(
                card,
                extra_retriggers,
            )
        return bloodstone_count * heart_triggers

    def _glass_scoring_cards(
        self,
        hand: PokerHand,
        cards,
        *,
        rules: dict | None = None,
    ) -> tuple:
        return tuple(
            card
            for card in self.scorer.scoring_cards(hand, cards, rules=rules)
            if not self.scorer.is_card_debuffed(card)
            and getattr(card, "enhancement", None) == "Glass"
        )

    def _misprint_activation_count(self, state) -> int:
        if state is None:
            return 0

        activations = 0
        for joker in getattr(state, "jokers", []):
            class_name = type(joker).__name__
            if class_name == "MisprintJoker":
                activations += 1
                continue
            if class_name not in COPY_JOKER_CLASS_NAMES:
                continue
            target, resolvable = resolve_copy_target(joker, state)
            if (
                resolvable
                and target is not None
                and type(target).__name__ == "MisprintJoker"
            ):
                activations += 1
        return activations

    def _misprint_coefficients(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
        lucky_branch: _LuckyBranch,
        bloodstone_branch: _BloodstoneBranch,
        zero_score,
        triggers: int,
    ) -> tuple[Fraction, ...]:
        zero_mult = self._fraction(zero_score.mult)
        coefficients = []
        for index in range(triggers):
            results = [0] * triggers
            results[index] = 1
            projection = self._project_stochastic_branch(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
                lucky_branch=lucky_branch,
                bloodstone_branch=bloodstone_branch,
                misprint_results=tuple(results),
            )
            coefficients.append(
                self._fraction(projection.score.mult) - zero_mult
            )
        return tuple(coefficients)

    def _misprint_increment_distribution(
        self,
        coefficients: tuple[Fraction, ...],
    ) -> tuple[tuple[Fraction, float], ...]:
        counts: dict[Fraction, int] = {Fraction(0): 1}
        for coefficient in coefficients:
            next_counts: dict[Fraction, int] = {}
            for subtotal, count in counts.items():
                for result in range(self.MISPRINT_RESULT_COUNT):
                    increment = subtotal + coefficient * result
                    next_counts[increment] = next_counts.get(increment, 0) + count
            counts = next_counts

        denominator = self.MISPRINT_RESULT_COUNT ** len(coefficients)
        return tuple(
            (increment, count / denominator)
            for increment, count in sorted(counts.items())
        )

    def _score_with_misprint_increment(self, zero_score, increment: Fraction) -> int:
        total = (
            self._fraction(zero_score.chips)
            * (self._fraction(zero_score.mult) + increment)
            * self._fraction(zero_score.x_mult)
        )
        return int(float(total))

    @staticmethod
    def _fraction(value) -> Fraction:
        rounded = round(float(value), 12)
        return Fraction(str(rounded)).limit_denominator(1_000_000)

    def _lucky_branches(self, triggers: int, state) -> tuple[_LuckyBranch, ...]:
        if triggers <= 0:
            return (_LuckyBranch((), 0, 0, 1.0),)

        p_mult = self._listed_probability(self.LUCKY_MULT_PROBABILITY, state)
        if not self._requires_joint_lucky_state(state):
            branches = []
            for results in product((False, True), repeat=triggers):
                successes = sum(results)
                probability = (
                    (p_mult ** successes)
                    * ((1.0 - p_mult) ** (triggers - successes))
                )
                branches.append(
                    _LuckyBranch(
                        mult_results=tuple(results),
                        money_successes=0,
                        successful_triggers=successes,
                        probability=probability,
                    )
                )
            return tuple(branches)

        p_money = self._listed_probability(self.LUCKY_MONEY_PROBABILITY, state)
        branches = []
        for results in product((False, True), repeat=triggers):
            mult_successes = sum(results)
            mult_failures = triggers - mult_successes
            mult_probability = (
                (p_mult ** mult_successes)
                * ((1.0 - p_mult) ** mult_failures)
            )
            for money_on_mult in range(mult_successes + 1):
                p_money_on_mult = (
                    comb(mult_successes, money_on_mult)
                    * (p_money ** money_on_mult)
                    * ((1.0 - p_money) ** (mult_successes - money_on_mult))
                )
                for money_on_failure in range(mult_failures + 1):
                    p_money_on_failure = (
                        comb(mult_failures, money_on_failure)
                        * (p_money ** money_on_failure)
                        * ((1.0 - p_money) ** (mult_failures - money_on_failure))
                    )
                    probability = (
                        mult_probability
                        * p_money_on_mult
                        * p_money_on_failure
                    )
                    if probability <= 0.0:
                        continue
                    branches.append(
                        _LuckyBranch(
                            mult_results=tuple(results),
                            money_successes=(money_on_mult + money_on_failure),
                            successful_triggers=(
                                mult_successes + money_on_failure
                            ),
                            probability=probability,
                        )
                    )
        return tuple(branches)

    def _bloodstone_branches(
        self,
        triggers: int,
        state,
    ) -> tuple[_BloodstoneBranch, ...]:
        if triggers <= 0:
            return (_BloodstoneBranch((), 1.0),)

        p = self._listed_probability(self.BLOODSTONE_PROBABILITY, state)
        return tuple(
            _BloodstoneBranch(
                results=tuple(results),
                probability=(
                    (p ** sum(results))
                    * ((1.0 - p) ** (triggers - sum(results)))
                ),
            )
            for results in product((False, True), repeat=triggers)
            if (
                (p ** sum(results))
                * ((1.0 - p) ** (triggers - sum(results)))
            ) > 0.0
        )

    def _project_stochastic_branch(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
        lucky_branch: _LuckyBranch,
        bloodstone_branch: _BloodstoneBranch,
        misprint_results: tuple[int, ...] = (),
    ):
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _ProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
            misprint_results=misprint_results,
        )
        branch_projector = type(self.joker_projector)(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )

    def _lucky_branch_input_state(self, state, branch: _LuckyBranch):
        if state is None:
            return None

        branch_state = state.copy()
        branch_state.jokers = deepcopy(list(getattr(state, "jokers", [])))
        if branch.money_successes:
            branch_state.money = (
                int(getattr(branch_state, "money", 0) or 0)
                + self.LUCKY_MONEY_REWARD * branch.money_successes
            )

        if branch.successful_triggers:
            for lucky_cat in self._jokers_named(branch_state, "LuckyCatJoker"):
                lucky_cat.x_mult = (
                    float(getattr(lucky_cat, "x_mult", 1.0) or 1.0)
                    + self.LUCKY_CAT_X_MULT_GAIN * branch.successful_triggers
                )

        return branch_state

    def _glass_branches(
        self,
        glass_cards: int,
        state,
    ) -> tuple[_GlassBranch, ...]:
        if glass_cards <= 0:
            return (_GlassBranch((), 1.0),)

        p = self._listed_probability(self.GLASS_BREAK_PROBABILITY, state)
        branches = []
        for results in product((False, True), repeat=glass_cards):
            broken_indices = tuple(
                index
                for index, broken in enumerate(results)
                if broken
            )
            breaks = len(broken_indices)
            probability = (
                (p ** breaks)
                * ((1.0 - p) ** (glass_cards - breaks))
            )
            if probability <= 0.0:
                continue
            branches.append(
                _GlassBranch(
                    broken_indices=broken_indices,
                    probability=probability,
                )
            )
        return tuple(branches)

    def _glass_branch_state(
        self,
        state,
        glass_branch: _GlassBranch,
        glass_cards,
        *,
        rules: dict | None = None,
    ):
        if state is None:
            return None

        branch_state = deepcopy(state)
        broken_cards = [
            glass_cards[index]
            for index in glass_branch.broken_indices
        ]
        if not broken_cards:
            return branch_state

        face_breaks = sum(
            card_is_face(card, rules)
            for card in broken_cards
        )
        if face_breaks:
            for canio in self._jokers_named(branch_state, "CanioJoker"):
                canio.x_mult = (
                    float(getattr(canio, "x_mult", 1.0) or 1.0)
                    + self.CANIO_X_MULT_GAIN * face_breaks
                )

        if hasattr(branch_state, "glass_cards_destroyed"):
            branch_state.glass_cards_destroyed = (
                int(getattr(branch_state, "glass_cards_destroyed", 0) or 0)
                + len(broken_cards)
            )

        self._remove_owned_cards(branch_state, broken_cards)
        return branch_state

    @classmethod
    def _remove_owned_cards(cls, state, broken_cards) -> None:
        owned_deck = getattr(state, "owned_deck", None)
        if owned_deck is None:
            return

        for broken in broken_cards:
            index = cls._matching_owned_card_index(owned_deck, broken)
            if index is not None:
                owned_deck.pop(index)

    @staticmethod
    def _matching_owned_card_index(owned_deck, broken) -> int | None:
        broken_live_id = getattr(broken, "live_id", None)
        if broken_live_id is not None:
            for index, candidate in enumerate(owned_deck):
                if getattr(candidate, "live_id", None) == broken_live_id:
                    return index

        signature = (
            str(getattr(broken, "rank", "")),
            str(getattr(broken, "suit", "")),
            getattr(broken, "enhancement", None),
            getattr(broken, "edition", None),
            getattr(broken, "seal", None),
        )
        for index, candidate in enumerate(owned_deck):
            candidate_signature = (
                str(getattr(candidate, "rank", "")),
                str(getattr(candidate, "suit", "")),
                getattr(candidate, "enhancement", None),
                getattr(candidate, "edition", None),
                getattr(candidate, "seal", None),
            )
            if candidate_signature == signature:
                return index
        return None

    def _listed_probability(self, base_probability: float, state) -> float:
        copies = len(self._jokers_named(state, "OopsAll6sJoker"))
        return min(1.0, float(base_probability) * (2.0 ** copies))

    def _requires_joint_lucky_state(self, state) -> bool:
        return bool(
            self._jokers_named(state, "LuckyCatJoker")
            or self._jokers_named(state, "BootstrapsJoker")
            or self._jokers_named(state, "BullJoker")
        )

    @staticmethod
    def _jokers_named(state, class_name: str) -> list:
        if state is None:
            return []
        return [
            joker
            for joker in getattr(state, "jokers", [])
            if type(joker).__name__ == class_name
        ]
