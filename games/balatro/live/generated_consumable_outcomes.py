from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import comb

from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.card_destruction import project_destroyed_playing_cards
from games.balatro.live.copy_projection import (
    COPY_JOKER_CLASS_NAMES,
    resolve_copy_target,
)
from games.balatro.live.post_hand_outcomes import (
    LiveVisibleCardScoreOutcomeModel,
    _LiveOnScoredScorer,
    _LiveOutcomeJokerProjector,
    _LiveProjectedStochasticScorer,
)
from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
)
from games.balatro.scoring import BalatroScorer


@dataclass
class ProjectedGeneratedConsumable:
    """Identity-abstract Tarot/Spectral created inside a hypothetical branch.

    Random generated-card identity is strategically unavailable before Balatro
    resolves its RNG. D1 currently does not execute held consumables recursively,
    so enumerating every Tarot/Spectral identity would multiply search size without
    changing the current blind-clear score. The placeholder preserves exact slot
    occupancy and category; authoritative re-observation supplies the real card
    before B6 can act on it.
    """

    category: str
    name: str
    live_id: None = None
    projected_random_identity: bool = True


class _GeneratedConsumableOutcomeJokerProjector(_LiveOutcomeJokerProjector):
    GENERATED_CLASS_NAMES = frozenset(
        {
            "EightBallJoker",
            "SeanceJoker",
            "SixthSenseJoker",
            "SuperpositionJoker",
            "VagabondJoker",
        }
    )

    SUPPORTED_CLASS_NAMES = (
        _LiveOutcomeJokerProjector.SUPPORTED_CLASS_NAMES
        | GENERATED_CLASS_NAMES
    )

    @classmethod
    def supports_in_state(cls, joker, state) -> bool:
        class_name = type(joker).__name__
        if class_name == "SixthSenseJoker":
            return (
                state is not None
                and getattr(state, "owned_deck", None) is not None
                and isinstance(getattr(state, "round_hand_play_counts", None), dict)
            )

        if class_name in COPY_JOKER_CLASS_NAMES:
            target, resolvable = resolve_copy_target(joker, state)
            if not resolvable:
                return False
            # Sixth Sense is explicitly Blueprint-incompatible in Balatro. A
            # copier aimed at it is a validated no-op rather than an unsupported
            # scoring effect.
            if target is not None and type(target).__name__ == "SixthSenseJoker":
                return True

        return super().supports_in_state(joker, state)


class LiveGeneratedConsumableScoreOutcomeModel(LiveVisibleCardScoreOutcomeModel):
    """Project consumable-generating Joker effects without hidden RNG sampling."""

    EIGHT_BALL_PROBABILITY = 0.25
    COPYABLE_GENERATOR_NAMES = frozenset(
        {
            "EightBallJoker",
            "SeanceJoker",
            "SuperpositionJoker",
            "VagabondJoker",
        }
    )
    MAIN_GENERATOR_NAMES = frozenset(
        {
            "SeanceJoker",
            "SuperpositionJoker",
            "VagabondJoker",
        }
    )

    def __init__(
        self,
        scorer: BalatroScorer | None = None,
        joker_projector=None,
    ) -> None:
        if joker_projector is not None:
            super().__init__(scorer=scorer, joker_projector=joker_projector)
            self._suppress_single_glass_break = False
            return

        live_scorer = (
            scorer
            if isinstance(scorer, _LiveOnScoredScorer)
            else _LiveOnScoredScorer()
        )
        super().__init__(
            scorer=live_scorer,
            joker_projector=_GeneratedConsumableOutcomeJokerProjector(live_scorer),
        )
        self._suppress_single_glass_break = False

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
        """Keep generated-Joker support inside nested score RNG branches."""
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _LiveProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
            misprint_results=misprint_results,
        )
        branch_projector = _GeneratedConsumableOutcomeJokerProjector(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )

    def _glass_scoring_cards(
        self,
        hand,
        cards,
        *,
        rules: dict | None = None,
    ) -> tuple:
        glass_cards = super()._glass_scoring_cards(
            hand,
            cards,
            rules=rules,
        )
        if self._suppress_single_glass_break and len(glass_cards) == 1:
            return ()
        return glass_cards

    def project_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ) -> ScoreProjectionTransition:
        if state is None:
            return super().project_transition(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
            )

        played_cards = list(cards or [])
        money_at_hand_play = int(getattr(state, "money", 0) or 0)
        first_hand = self._is_first_hand(state)
        superposition_eligible = self._superposition_eligible(state, played_cards)

        # A qualifying Glass 6 is deterministically destroyed by Sixth Sense.
        # Suppress the independent natural Glass-shatter RNG branch only when a
        # consumable slot will still remain after earlier joker-main generators.
        suppress_glass_break = self._sixth_sense_will_destroy_glass(
            state,
            played_cards,
            first_hand=first_hand,
            money_at_hand_play=money_at_hand_play,
        )

        # Probe once on an isolated projector branch to recover exact scoring-card
        # membership and retrigger counts for 8 Ball. No generated identity or
        # Python RNG is consumed by the Joker models themselves.
        probe = self.joker_projector.score(
            hand,
            state,
            played_cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
        eight_ball_attempts = self._eight_ball_attempts(
            hand,
            state,
            probe.cards_after_copy,
            extra_retriggers=probe.played_card_retriggers,
        )

        previous_suppression = self._suppress_single_glass_break
        self._suppress_single_glass_break = suppress_glass_break
        try:
            transition = super().project_transition(
                hand,
                state,
                played_cards,
                include_card_chips=include_card_chips,
            )
        finally:
            self._suppress_single_glass_break = previous_suppression

        outcomes = []
        added_random_sources = list(transition.distribution.random_sources)
        saw_tarot_identity = False
        saw_spectral_identity = False
        saw_eight_ball_roll = False

        for score_outcome in transition.distribution.outcomes:
            source_state = (
                score_outcome.state_after_scoring
                if score_outcome.state_after_scoring is not None
                else transition.state_after_scoring
            )
            if source_state is None:
                outcomes.append(score_outcome)
                continue

            initial_room = self._consumable_room(source_state)
            eight_ball_branches = self._capped_success_branches(
                eight_ball_attempts,
                self._listed_probability(self.EIGHT_BALL_PROBABILITY, state),
                initial_room,
            )
            if eight_ball_attempts > 0 and initial_room > 0:
                saw_eight_ball_roll = True

            for eight_ball_created, probability in eight_ball_branches:
                branch_state = deepcopy(source_state)
                if eight_ball_created:
                    self._add_abstract_consumables(
                        branch_state,
                        category="TAROT",
                        count=eight_ball_created,
                    )
                    saw_tarot_identity = True

                created_tarot, created_spectral = self._apply_main_generators(
                    branch_state,
                    hand=hand,
                    money_at_hand_play=money_at_hand_play,
                    superposition_eligible=superposition_eligible,
                )
                saw_tarot_identity = saw_tarot_identity or created_tarot > 0
                saw_spectral_identity = saw_spectral_identity or created_spectral > 0

                if self._apply_sixth_sense(
                    branch_state,
                    played_cards,
                    first_hand=first_hand,
                ):
                    saw_spectral_identity = True

                outcomes.append(
                    ScoreOutcome(
                        score=score_outcome.score,
                        probability=score_outcome.probability * probability,
                        state_after_scoring=branch_state,
                    )
                )

        if saw_eight_ball_roll:
            added_random_sources.append(f"8 Ball x{eight_ball_attempts}")
        if saw_tarot_identity:
            added_random_sources.append("generated Tarot identity (abstracted)")
        if saw_spectral_identity:
            added_random_sources.append("generated Spectral identity (abstracted)")

        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(outcomes),
            random_sources=tuple(dict.fromkeys(added_random_sources)),
        )
        common_state = (
            outcomes[0].state_after_scoring
            if len(outcomes) == 1
            else transition.state_after_scoring
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=common_state,
            unsupported_jokers=transition.unsupported_jokers,
        )

    def _eight_ball_attempts(
        self,
        hand,
        state,
        cards,
        *,
        extra_retriggers: int,
    ) -> int:
        copies = self._activation_count(state, "EightBallJoker")
        if copies <= 0:
            return 0

        rules = hand_rules_for_state(state)
        scored_eight_triggers = 0
        for card in self.scorer.scoring_cards(hand, cards, rules=rules):
            if self.scorer.is_card_debuffed(card):
                continue
            if str(getattr(card, "rank", "")) != "8":
                continue
            scored_eight_triggers += self.scorer._played_card_trigger_count(
                card,
                extra_retriggers,
            )
        return copies * scored_eight_triggers

    def _apply_main_generators(
        self,
        state,
        *,
        hand,
        money_at_hand_play: int,
        superposition_eligible: bool,
    ) -> tuple[int, int]:
        tarot_created = 0
        spectral_created = 0
        for ability_name in self._effective_main_abilities(state):
            if self._consumable_room(state) <= 0:
                break

            if ability_name == "VagabondJoker":
                if money_at_hand_play > 4:
                    continue
                self._add_abstract_consumables(state, category="TAROT", count=1)
                tarot_created += 1
                continue

            if ability_name == "SuperpositionJoker":
                if not superposition_eligible:
                    continue
                self._add_abstract_consumables(state, category="TAROT", count=1)
                tarot_created += 1
                continue

            if ability_name == "SeanceJoker":
                if hand != PokerHand.STRAIGHT_FLUSH:
                    continue
                self._add_abstract_consumables(state, category="SPECTRAL", count=1)
                spectral_created += 1

        return tarot_created, spectral_created

    def _apply_sixth_sense(self, state, played_cards, *, first_hand: bool) -> bool:
        if not first_hand or len(played_cards) != 1:
            return False
        if str(getattr(played_cards[0], "rank", "")) != "6":
            return False
        if self._consumable_room(state) <= 0:
            return False
        if not any(
            type(joker).__name__ == "SixthSenseJoker" and self._joker_active(joker)
            for joker in getattr(state, "jokers", []) or []
        ):
            return False

        branch_card = self._matching_owned_card(state, played_cards[0])
        if branch_card is None:
            return False

        destroyed = project_destroyed_playing_cards(state, [branch_card])
        if not destroyed:
            return False
        self._add_abstract_consumables(state, category="SPECTRAL", count=1)
        return True

    def _sixth_sense_will_destroy_glass(
        self,
        state,
        played_cards,
        *,
        first_hand: bool,
        money_at_hand_play: int,
    ) -> bool:
        if not first_hand or len(played_cards) != 1:
            return False
        card = played_cards[0]
        if (
            str(getattr(card, "rank", "")) != "6"
            or getattr(card, "enhancement", None) != "Glass"
        ):
            return False
        if not any(
            type(joker).__name__ == "SixthSenseJoker" and self._joker_active(joker)
            for joker in getattr(state, "jokers", []) or []
        ):
            return False

        room = self._consumable_room(state)
        if room <= 0:
            return False

        # On a single 6, Vagabond is the only supported earlier joker-main
        # consumable generator that can claim capacity before Sixth Sense's
        # destroying-card context. Its trigger uses money from hand-play time.
        if money_at_hand_play <= 4:
            room -= min(room, self._activation_count(state, "VagabondJoker"))
        return room > 0

    def _effective_main_abilities(self, state) -> tuple[str, ...]:
        result = []
        for joker in getattr(state, "jokers", []) or []:
            if not self._joker_active(joker):
                continue
            class_name = type(joker).__name__
            if class_name in self.MAIN_GENERATOR_NAMES:
                result.append(class_name)
                continue
            if class_name not in COPY_JOKER_CLASS_NAMES:
                continue
            target, resolvable = resolve_copy_target(joker, state)
            if not resolvable or target is None or not self._joker_active(target):
                continue
            target_name = type(target).__name__
            if target_name in self.MAIN_GENERATOR_NAMES:
                result.append(target_name)
        return tuple(result)

    def _activation_count(self, state, class_name: str) -> int:
        activations = 0
        for joker in getattr(state, "jokers", []) or []:
            if not self._joker_active(joker):
                continue
            joker_name = type(joker).__name__
            if joker_name == class_name:
                activations += 1
                continue
            if joker_name not in COPY_JOKER_CLASS_NAMES:
                continue
            target, resolvable = resolve_copy_target(joker, state)
            if not resolvable or target is None or not self._joker_active(target):
                continue
            if (
                class_name in self.COPYABLE_GENERATOR_NAMES
                and type(target).__name__ == class_name
            ):
                activations += 1
        return activations

    @staticmethod
    def _joker_active(joker) -> bool:
        return not bool(
            getattr(joker, "debuffed", False)
            or getattr(joker, "debuff", False)
        )

    @staticmethod
    def _is_first_hand(state) -> bool:
        counts = getattr(state, "round_hand_play_counts", None)
        if not isinstance(counts, dict):
            return False
        return not any(int(value or 0) > 0 for value in counts.values())

    @staticmethod
    def _consumable_room(state) -> int:
        slots = max(0, int(getattr(state, "consumable_slots", 0) or 0))
        held = len(getattr(state, "consumables", []) or [])
        return max(0, slots - held)

    @classmethod
    def _add_abstract_consumables(cls, state, *, category: str, count: int) -> int:
        created = min(max(0, int(count)), cls._consumable_room(state))
        label = (
            "Projected random Tarot"
            if category == "TAROT"
            else "Projected random Spectral"
        )
        for _ in range(created):
            state.consumables.append(
                ProjectedGeneratedConsumable(
                    category=category,
                    name=label,
                )
            )
        return created

    @staticmethod
    def _capped_success_branches(
        attempts: int,
        probability: float,
        capacity: int,
    ) -> tuple[tuple[int, float], ...]:
        attempts = max(0, int(attempts))
        capacity = max(0, int(capacity))
        if attempts <= 0 or capacity <= 0:
            return ((0, 1.0),)

        grouped: dict[int, float] = {}
        for successes in range(attempts + 1):
            branch_probability = (
                comb(attempts, successes)
                * (probability ** successes)
                * ((1.0 - probability) ** (attempts - successes))
            )
            created = min(successes, capacity)
            grouped[created] = grouped.get(created, 0.0) + branch_probability
        return tuple(sorted(grouped.items()))

    @staticmethod
    def _superposition_eligible(state, cards) -> bool:
        rules = hand_rules_for_state(state)
        straight_cards = HandEvaluator().scoring_cards(
            PokerHand.STRAIGHT,
            list(cards or []),
            rules=rules,
        )
        return bool(straight_cards) and any(
            str(getattr(card, "rank", "")) == "A"
            for card in straight_cards
        )

    @staticmethod
    def _matching_owned_card(state, selected):
        owned_deck = getattr(state, "owned_deck", None)
        if owned_deck is None:
            return None

        live_id = getattr(selected, "live_id", None)
        if live_id is not None:
            for card in owned_deck:
                if getattr(card, "live_id", None) == live_id:
                    return card
            return None

        signature = (
            str(getattr(selected, "rank", "")),
            str(getattr(selected, "suit", "")),
            getattr(selected, "enhancement", None),
            getattr(selected, "edition", None),
            getattr(selected, "seal", None),
            int(getattr(selected, "permanent_bonus", 0) or 0),
        )
        for card in owned_deck:
            candidate = (
                str(getattr(card, "rank", "")),
                str(getattr(card, "suit", "")),
                getattr(card, "enhancement", None),
                getattr(card, "edition", None),
                getattr(card, "seal", None),
                int(getattr(card, "permanent_bonus", 0) or 0),
            )
            if candidate == signature:
                return card
        return None
