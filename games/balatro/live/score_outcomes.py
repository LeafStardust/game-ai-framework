from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import comb

from games.balatro.hand import PokerHand
from games.balatro.hand_rules import hand_rules_for_state
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
    mult_successes: int
    money_successes: int
    successful_triggers: int
    probability: float


@dataclass(frozen=True)
class _GlassBranch:
    face_breaks: int
    probability: float


class VisibleCardScoreOutcomeModel:
    """Project public visible scoring without consuming Balatro's hidden RNG."""

    LUCKY_MULT_PROBABILITY = 0.2
    LUCKY_MONEY_PROBABILITY = 1.0 / 15.0
    LUCKY_MULT_BONUS = 20
    LUCKY_MONEY_REWARD = 20
    LUCKY_CAT_X_MULT_GAIN = 0.25
    GLASS_BREAK_PROBABILITY = 0.25
    CANIO_X_MULT_GAIN = 1.0

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
        canio_face_glass = self._canio_face_glass_count(
            hand,
            copied_cards,
            projected_state,
            rules=rules,
        )

        if lucky_triggers == 0 and canio_face_glass == 0:
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

        lucky_branches = self._lucky_branches(
            lucky_triggers,
            projected_state,
        )
        glass_branches = self._glass_branches(canio_face_glass)
        outcomes: list[ScoreOutcome] = []

        for lucky_branch in lucky_branches:
            score = self._score_lucky_branch(
                base,
                projected_state,
                lucky_branch,
            )
            for glass_branch in glass_branches:
                branch_state = self._branch_state(
                    projected_state,
                    lucky_branch,
                    glass_branch,
                )
                outcomes.append(
                    ScoreOutcome(
                        score=score,
                        probability=(
                            lucky_branch.probability * glass_branch.probability
                        ),
                        state_after_scoring=branch_state,
                    )
                )

        random_sources: list[str] = []
        if lucky_triggers:
            if self._requires_joint_lucky_state(projected_state):
                random_sources.append(f"Lucky effects x{lucky_triggers}")
            else:
                random_sources.append(f"Lucky mult x{lucky_triggers}")
        if canio_face_glass:
            random_sources.append(f"Glass break x{canio_face_glass}")

        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(outcomes),
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

    def _canio_face_glass_count(
        self,
        hand: PokerHand,
        cards,
        state,
        *,
        rules: dict | None = None,
    ) -> int:
        if not self._jokers_named(state, "CanioJoker"):
            return 0
        return sum(
            1
            for card in self.scorer.scoring_cards(hand, cards, rules=rules)
            if not self.scorer.is_card_debuffed(card)
            and getattr(card, "enhancement", None) == "Glass"
            and str(getattr(card, "rank", "")) in {"J", "Q", "K"}
        )

    def _lucky_branches(self, triggers: int, state) -> tuple[_LuckyBranch, ...]:
        if triggers <= 0:
            return (_LuckyBranch(0, 0, 0, 1.0),)

        if not self._requires_joint_lucky_state(state):
            p = self.LUCKY_MULT_PROBABILITY
            return tuple(
                _LuckyBranch(
                    mult_successes=successes,
                    money_successes=0,
                    successful_triggers=0,
                    probability=(
                        comb(triggers, successes)
                        * (p ** successes)
                        * ((1.0 - p) ** (triggers - successes))
                    ),
                )
                for successes in range(triggers + 1)
            )

        p_mult = self.LUCKY_MULT_PROBABILITY
        p_money = self.LUCKY_MONEY_PROBABILITY
        per_trigger = (
            (0, 0, 0, (1.0 - p_mult) * (1.0 - p_money)),
            (1, 0, 1, p_mult * (1.0 - p_money)),
            (0, 1, 1, (1.0 - p_mult) * p_money),
            (1, 1, 1, p_mult * p_money),
        )
        probabilities: dict[tuple[int, int, int], float] = {(0, 0, 0): 1.0}
        for _ in range(triggers):
            updated: dict[tuple[int, int, int], float] = {}
            for (mults, money, successes), probability in probabilities.items():
                for add_mult, add_money, add_success, branch_probability in per_trigger:
                    key = (
                        mults + add_mult,
                        money + add_money,
                        successes + add_success,
                    )
                    updated[key] = (
                        updated.get(key, 0.0)
                        + probability * branch_probability
                    )
            probabilities = updated

        return tuple(
            _LuckyBranch(
                mult_successes=key[0],
                money_successes=key[1],
                successful_triggers=key[2],
                probability=probability,
            )
            for key, probability in sorted(probabilities.items())
            if probability > 0.0
        )

    def _glass_branches(self, face_glass_cards: int) -> tuple[_GlassBranch, ...]:
        if face_glass_cards <= 0:
            return (_GlassBranch(0, 1.0),)
        p = self.GLASS_BREAK_PROBABILITY
        return tuple(
            _GlassBranch(
                face_breaks=breaks,
                probability=(
                    comb(face_glass_cards, breaks)
                    * (p ** breaks)
                    * ((1.0 - p) ** (face_glass_cards - breaks))
                ),
            )
            for breaks in range(face_glass_cards + 1)
        )

    def _score_lucky_branch(self, base, state, branch: _LuckyBranch) -> int:
        mult = float(base.mult + self.LUCKY_MULT_BONUS * branch.mult_successes)
        x_mult = float(base.x_mult)

        if state is not None and branch.money_successes:
            initial_money = int(getattr(state, "money", 0) or 0)
            money_after = (
                initial_money
                + self.LUCKY_MONEY_REWARD * branch.money_successes
            )
            bootstrap_count = len(self._jokers_named(state, "BootstrapsJoker"))
            if bootstrap_count:
                before_steps = initial_money // 5
                after_steps = money_after // 5
                mult += (after_steps - before_steps) * 2 * bootstrap_count

        if state is not None and branch.successful_triggers:
            for lucky_cat in self._jokers_named(state, "LuckyCatJoker"):
                current = float(getattr(lucky_cat, "x_mult", 1.0) or 1.0)
                grown = (
                    current
                    + self.LUCKY_CAT_X_MULT_GAIN * branch.successful_triggers
                )
                x_mult *= grown / current

        return int(float(base.chips) * mult * x_mult)

    def _branch_state(
        self,
        state,
        lucky_branch: _LuckyBranch,
        glass_branch: _GlassBranch,
    ):
        if state is None:
            return None

        branch_state = deepcopy(state)
        if lucky_branch.money_successes:
            branch_state.money = (
                int(getattr(branch_state, "money", 0) or 0)
                + self.LUCKY_MONEY_REWARD * lucky_branch.money_successes
            )

        if lucky_branch.successful_triggers:
            for lucky_cat in self._jokers_named(branch_state, "LuckyCatJoker"):
                lucky_cat.x_mult = (
                    float(getattr(lucky_cat, "x_mult", 1.0) or 1.0)
                    + self.LUCKY_CAT_X_MULT_GAIN
                    * lucky_branch.successful_triggers
                )

        if glass_branch.face_breaks:
            for canio in self._jokers_named(branch_state, "CanioJoker"):
                canio.x_mult = (
                    float(getattr(canio, "x_mult", 1.0) or 1.0)
                    + self.CANIO_X_MULT_GAIN * glass_branch.face_breaks
                )
            if hasattr(branch_state, "glass_cards_destroyed"):
                branch_state.glass_cards_destroyed = (
                    int(getattr(branch_state, "glass_cards_destroyed", 0) or 0)
                    + glass_branch.face_breaks
                )

        return branch_state

    def _requires_joint_lucky_state(self, state) -> bool:
        return bool(
            self._jokers_named(state, "LuckyCatJoker")
            or self._jokers_named(state, "BootstrapsJoker")
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
