from __future__ import annotations

from copy import deepcopy
from math import comb

from games.balatro.events import BalatroEvent, BalatroEventType
from games.balatro.hand_rules import card_is_face, hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.live.joker_projection import LiveJokerScoreProjector
from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
    VisibleCardScoreOutcomeModel,
    _ProjectedStochasticScorer,
)
from games.balatro.scoring import BalatroScorer


class _LiveOnScoredScorer(BalatroScorer):
    ON_SCORED_JOKER_CLASS_NAMES = (
        BalatroScorer.ON_SCORED_JOKER_CLASS_NAMES
        | frozenset({"BusinessCardJoker"})
    )


class _LiveProjectedStochasticScorer(_ProjectedStochasticScorer):
    ON_SCORED_JOKER_CLASS_NAMES = (
        _ProjectedStochasticScorer.ON_SCORED_JOKER_CLASS_NAMES
        | frozenset({"BusinessCardJoker"})
    )


class _LiveOutcomeJokerProjector(LiveJokerScoreProjector):
    SUPPORTED_CLASS_NAMES = (
        LiveJokerScoreProjector.SUPPORTED_CLASS_NAMES
        | frozenset(
            {
                "BusinessCardJoker",
                "CartomancerJoker",
                "CertificateJoker",
                "ChicotJoker",
                "Cloud9Joker",
                "DNAJoker",
                "DelayedGratificationJoker",
                "FacelessJoker",
                "GiftCardJoker",
                "GlassJoker",
                "GoldenJoker",
                "HallucinationJoker",
                "LuchadorJoker",
                "MailInRebateJoker",
                "MarbleJoker",
                "MisprintJoker",
                "MrBonesJoker",
                "ReservedParkingJoker",
                "RiffRaffJoker",
                "RocketJoker",
                "SatelliteJoker",
                "ToTheMoonJoker",
            }
        )
    )

    @classmethod
    def supports_in_state(cls, joker, state) -> bool:
        if type(joker).__name__ == "DNAJoker":
            return (
                state is not None
                and getattr(state, "owned_deck", None) is not None
                and isinstance(getattr(state, "round_hand_play_counts", None), dict)
            )
        return super().supports_in_state(joker, state)

    def score(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
        resolve_random_effects: bool = False,
    ):
        dna_count = self._dna_trigger_count(state, cards)
        if dna_count <= 0:
            return super().score(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
                resolve_random_effects=resolve_random_effects,
            )

        working_state = deepcopy(state)
        source_index = self._played_card_index(state, cards[0])
        if source_index is None:
            return super().score(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
                resolve_random_effects=resolve_random_effects,
            )

        source = working_state.hand[source_index]
        copied_cards = []
        for _ in range(dna_count):
            copied = deepcopy(source)
            copied.live_id = None
            copied_cards.append(copied)
            working_state.hand.append(copied)
            working_state.owned_deck.append(copied)

        self._apply_cards_added_jokers(working_state, copied_cards)
        return super().score(
            hand,
            working_state,
            [source],
            include_card_chips=include_card_chips,
            resolve_random_effects=resolve_random_effects,
        )

    @classmethod
    def _dna_trigger_count(cls, state, cards) -> int:
        cards = list(cards or [])
        if state is None or len(cards) != 1:
            return 0
        if getattr(state, "owned_deck", None) is None:
            return 0
        counts = getattr(state, "round_hand_play_counts", None)
        if not isinstance(counts, dict):
            return 0
        if any(int(value or 0) > 0 for value in counts.values()):
            return 0
        if cls._played_card_index(state, cards[0]) is None:
            return 0
        return sum(
            1
            for joker in getattr(state, "jokers", [])
            if type(joker).__name__ == "DNAJoker"
        )

    @staticmethod
    def _played_card_index(state, selected) -> int | None:
        selected_live_id = getattr(selected, "live_id", None)
        for index, card in enumerate(getattr(state, "hand", [])):
            if card is selected:
                return index
            if (
                selected_live_id is not None
                and getattr(card, "live_id", None) == selected_live_id
            ):
                return index
        return None

    @staticmethod
    def _apply_cards_added_jokers(state, cards) -> None:
        if not cards:
            return
        context = JokerContext(
            state=state,
            cards=list(cards),
            trigger="CARDS_ADDED",
            event=BalatroEvent(BalatroEventType.CARDS_ADDED, list(cards)),
            data={},
        )
        for joker in getattr(state, "jokers", []):
            if type(joker).__name__ == "HologramJoker":
                context = joker.apply(context)


class LiveVisibleCardScoreOutcomeModel(VisibleCardScoreOutcomeModel):
    """Extend visible score outcomes with exact live state RNG branches."""

    SPACE_JOKER_PROBABILITY = 0.25
    BUSINESS_CARD_PROBABILITY = 0.5
    BUSINESS_CARD_REWARD = 2
    RESERVED_PARKING_PROBABILITY = 0.5
    RESERVED_PARKING_REWARD = 1
    GLASS_JOKER_X_MULT_GAIN = 0.75

    def __init__(
        self,
        scorer: BalatroScorer | None = None,
        joker_projector: LiveJokerScoreProjector | None = None,
    ):
        if joker_projector is not None:
            super().__init__(scorer=scorer, joker_projector=joker_projector)
            return

        live_scorer = (
            scorer
            if isinstance(scorer, _LiveOnScoredScorer)
            else _LiveOnScoredScorer()
        )
        super().__init__(
            scorer=live_scorer,
            joker_projector=_LiveOutcomeJokerProjector(live_scorer),
        )

    def project_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreProjectionTransition:
        transition = self._project_scoring_transition(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
        )
        projected_state = transition.state_after_scoring
        space_jokers = len(self._jokers_named(projected_state, "SpaceJoker"))
        if space_jokers <= 0:
            return transition

        branches = self._space_joker_branches(space_jokers, projected_state)
        outcomes = []
        for score_outcome in transition.distribution.outcomes:
            source_state = (
                score_outcome.state_after_scoring
                if score_outcome.state_after_scoring is not None
                else projected_state
            )
            for level_ups, probability in branches:
                branch_state = deepcopy(source_state)
                self._apply_space_joker_level_ups(branch_state, hand, level_ups)
                outcomes.append(
                    ScoreOutcome(
                        score=score_outcome.score,
                        probability=score_outcome.probability * probability,
                        state_after_scoring=branch_state,
                    )
                )

        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(outcomes),
            random_sources=(
                *transition.distribution.random_sources,
                f"Space Joker x{space_jokers}",
            ),
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=projected_state,
            unsupported_jokers=transition.unsupported_jokers,
        )

    def _project_scoring_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
    ) -> ScoreProjectionTransition:
        business_cards = len(self._jokers_named(state, "BusinessCardJoker"))
        reserved_parking = len(self._jokers_named(state, "ReservedParkingJoker"))
        if business_cards <= 0 and reserved_parking <= 0:
            return super().project_transition(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
            )

        probe = self.joker_projector.score(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
        projected_state = probe.state_after_scoring
        rules = hand_rules_for_state(projected_state)
        business_triggers = self._business_card_scoring_triggers(
            hand,
            probe.cards_after_copy,
            projected_state,
            rules=rules,
            extra_retriggers=probe.played_card_retriggers,
        )
        reserved_triggers = self._reserved_parking_held_triggers(
            probe.cards_after_copy,
            projected_state,
            rules=rules,
        )
        if business_triggers <= 0 and reserved_triggers <= 0:
            return super().project_transition(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
            )

        business_branches = self._business_card_branches(
            business_triggers,
            projected_state,
        )
        reserved_branches = self._reserved_parking_branches(
            reserved_triggers,
            projected_state,
        )
        outcomes = []
        inner_random_sources: tuple[str, ...] = ()
        for business_successes, business_probability in business_branches:
            for reserved_successes, reserved_probability in reserved_branches:
                branch_state = state.copy()
                branch_state.money = (
                    int(getattr(branch_state, "money", 0) or 0)
                    + self.BUSINESS_CARD_REWARD * business_successes
                    + self.RESERVED_PARKING_REWARD * reserved_successes
                )
                branch_transition = super().project_transition(
                    hand,
                    branch_state,
                    cards,
                    include_card_chips=include_card_chips,
                )
                inner_random_sources = branch_transition.distribution.random_sources
                probability = business_probability * reserved_probability
                for outcome in branch_transition.distribution.outcomes:
                    outcomes.append(
                        ScoreOutcome(
                            score=outcome.score,
                            probability=outcome.probability * probability,
                            state_after_scoring=outcome.state_after_scoring,
                        )
                    )

        random_sources = list(inner_random_sources)
        if business_triggers:
            random_sources.append(f"Business Card x{business_triggers}")
        if reserved_triggers:
            random_sources.append(f"Reserved Parking x{reserved_triggers}")
        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(outcomes),
            random_sources=tuple(random_sources),
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=projected_state,
            unsupported_jokers=probe.unsupported_jokers,
        )

    def _business_card_scoring_triggers(
        self,
        hand,
        cards,
        state,
        *,
        rules: dict | None = None,
        extra_retriggers: int = 0,
    ) -> int:
        copies = len(self._jokers_named(state, "BusinessCardJoker"))
        if copies <= 0:
            return 0

        face_triggers = 0
        for card in self.scorer.scoring_cards(hand, cards, rules=rules):
            if self.scorer.is_card_debuffed(card):
                continue
            if not card_is_face(card, rules):
                continue
            face_triggers += self.scorer._played_card_trigger_count(
                card,
                extra_retriggers,
            )
        return copies * face_triggers

    def _reserved_parking_held_triggers(
        self,
        played_cards,
        state,
        *,
        rules: dict | None = None,
    ) -> int:
        copies = len(self._jokers_named(state, "ReservedParkingJoker"))
        if copies <= 0 or state is None:
            return 0

        played_ids = {id(card) for card in played_cards}
        mime_retriggers = len(self._jokers_named(state, "MimeJoker"))
        face_triggers = 0
        for card in getattr(state, "hand", []):
            if id(card) in played_ids or self.scorer.is_card_debuffed(card):
                continue
            if not card_is_face(card, rules):
                continue
            face_triggers += self.scorer._held_card_trigger_count(
                card,
                mime_retriggers,
            )
        return copies * face_triggers

    def _business_card_branches(
        self,
        triggers: int,
        state,
    ) -> tuple[tuple[int, float], ...]:
        probability = self._listed_probability(
            self.BUSINESS_CARD_PROBABILITY,
            state,
        )
        return self._binomial_branches(triggers, probability)

    def _reserved_parking_branches(
        self,
        triggers: int,
        state,
    ) -> tuple[tuple[int, float], ...]:
        probability = self._listed_probability(
            self.RESERVED_PARKING_PROBABILITY,
            state,
        )
        return self._binomial_branches(triggers, probability)

    @staticmethod
    def _binomial_branches(
        triggers: int,
        probability: float,
    ) -> tuple[tuple[int, float], ...]:
        if triggers <= 0:
            return ((0, 1.0),)
        branches = []
        for successes in range(triggers + 1):
            branch_probability = (
                comb(triggers, successes)
                * (probability ** successes)
                * ((1.0 - probability) ** (triggers - successes))
            )
            if branch_probability > 0.0:
                branches.append((successes, branch_probability))
        return tuple(branches)

    def _project_stochastic_branch(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
        lucky_branch,
        bloodstone_branch,
        misprint_results: tuple[int, ...] = (),
    ):
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _LiveProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
            misprint_results=misprint_results,
        )
        branch_projector = _LiveOutcomeJokerProjector(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )

    def _glass_branch_state(
        self,
        state,
        glass_branch,
        glass_cards,
        *,
        rules: dict | None = None,
    ):
        branch_state = super()._glass_branch_state(
            state,
            glass_branch,
            glass_cards,
            rules=rules,
        )
        if branch_state is None:
            return None

        breaks = len(glass_branch.broken_indices)
        if breaks <= 0:
            return branch_state

        for glass_joker in self._jokers_named(branch_state, "GlassJoker"):
            glass_joker.x_mult = (
                float(getattr(glass_joker, "x_mult", 1.0) or 1.0)
                + self.GLASS_JOKER_X_MULT_GAIN * breaks
            )
        return branch_state

    def _space_joker_branches(self, copies: int, state) -> tuple[tuple[int, float], ...]:
        probability = self._listed_probability(
            self.SPACE_JOKER_PROBABILITY,
            state,
        )
        branches = []
        for successes in range(copies + 1):
            branch_probability = (
                comb(copies, successes)
                * (probability ** successes)
                * ((1.0 - probability) ** (copies - successes))
            )
            if branch_probability > 0.0:
                branches.append((successes, branch_probability))
        return tuple(branches)

    @staticmethod
    def _apply_space_joker_level_ups(state, hand, level_ups: int) -> None:
        if state is None or level_ups <= 0:
            return
        levels = getattr(state, "hand_levels", None)
        if not isinstance(levels, dict):
            return

        key = hand.value
        current = int(levels.get(key, levels.get(hand, 1)) or 1)
        updated = current + int(level_ups)
        levels[key] = updated
        if hand in levels:
            levels[hand] = updated
