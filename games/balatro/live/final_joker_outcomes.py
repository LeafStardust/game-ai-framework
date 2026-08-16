from __future__ import annotations

from copy import deepcopy
from itertools import combinations

from games.balatro.boss_trigger import (
    boss_blind_disabled_by_owned_jokers,
    boss_hand_is_debuffed,
    matador_boss_hand_triggered,
    matador_state_resolvable,
    record_accepted_boss_hand,
)
from games.balatro.hand import PokerHand
from games.balatro.joker import JokerContext
from games.balatro.live.copy_projection import project_independent_copy_jokers
from games.balatro.live.discard_projection import (
    LiveDiscardJokerProjector,
    UnsupportedDiscardProjection,
)
from games.balatro.live.generated_consumable_outcomes import (
    LiveGeneratedConsumableScoreOutcomeModel,
    _GeneratedConsumableOutcomeJokerProjector,
)
from games.balatro.live.post_hand_outcomes import (
    _LiveOnScoredScorer,
    _LiveProjectedStochasticScorer,
)
from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
)
from games.balatro.scoring import BalatroScorer, HandScore


_SECRET_HAND_SCORES = {
    PokerHand.FIVE_OF_A_KIND: HandScore(120, 12),
    PokerHand.FLUSH_HOUSE: HandScore(140, 14),
    PokerHand.FLUSH_FIVE: HandScore(160, 16),
}


class _FinalLiveScorer(_LiveOnScoredScorer):
    SCORES = {**BalatroScorer.SCORES, **_SECRET_HAND_SCORES}


class _FinalProjectedStochasticScorer(_LiveProjectedStochasticScorer):
    SCORES = {**BalatroScorer.SCORES, **_SECRET_HAND_SCORES}


class LiveFinalJokerScoreProjector(_GeneratedConsumableOutcomeJokerProjector):
    """Final D1 support contract for every admitted live Joker."""

    SUPPORTED_CLASS_NAMES = (
        _GeneratedConsumableOutcomeJokerProjector.SUPPORTED_CLASS_NAMES
        | frozenset({"MatadorJoker", "ToDoListJoker"})
    )

    @classmethod
    def supports_in_state(cls, joker, state) -> bool:
        class_name = type(joker).__name__
        if class_name == "ToDoListJoker":
            # The target is a public per-card ability field. Absence means live
            # observation could not reconstruct the current request, so fail closed.
            if getattr(joker, "target_hand", None) is None:
                return False
        if class_name == "MatadorJoker" and not matador_state_resolvable(state):
            # The Ox's tie-broken most-played target and unresolved boss-owned
            # hand history cannot be reconstructed exactly from current state.
            return False
        return super().supports_in_state(joker, state)


class LiveFinalJokerScoreOutcomeModel(LiveGeneratedConsumableScoreOutcomeModel):
    """Complete D1 outcome stack, including boss hand-transition semantics."""

    def __init__(
        self,
        scorer: BalatroScorer | None = None,
        joker_projector=None,
    ) -> None:
        self.discard_joker_projector = LiveDiscardJokerProjector()
        if joker_projector is not None:
            super().__init__(scorer=scorer, joker_projector=joker_projector)
            return

        live_scorer = (
            scorer
            if isinstance(scorer, _FinalLiveScorer)
            else _FinalLiveScorer()
        )
        super().__init__(
            scorer=live_scorer,
            joker_projector=LiveFinalJokerScoreProjector(live_scorer),
        )

    def project_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
    ):
        if self._hook_active(state):
            return self._project_hook_transition(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
            )
        return self._project_non_hook_transition(
            hand,
            state,
            cards,
            include_card_chips=include_card_chips,
        )

    def _project_non_hook_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
    ) -> ScoreProjectionTransition:
        hand_debuff = boss_hand_is_debuffed(state, hand, cards)
        if not hand_debuff.resolvable:
            # Exact live observation normally makes Eye/Mouth resolvable. If a
            # legacy/manual state cannot reconstruct the Blind-owned history,
            # fail closed with a pessimistic zero-score branch instead of guessing.
            return self._unresolved_boss_hand_transition(state)
        if hand_debuff.triggered:
            return self._project_debuffed_hand(hand, state, cards)

        # The Ox resolves before independent Jokers. Apply its public deterministic
        # money reset before scoring so Joker order remains exact: Bull/Bootstraps
        # before Matador see $0, while those after Matador see the earned $8.
        projected_input = state
        result = matador_boss_hand_triggered(state, hand, cards)
        if (
            state is not None
            and result.resolvable
            and result.triggered
            and str(getattr(state, "boss_name", "") or "") == "The Ox"
        ):
            projected_input = state.copy()
            projected_input.money = 0

        transition = super().project_transition(
            hand,
            projected_input,
            cards,
            include_card_chips=include_card_chips,
        )
        self._record_accepted_boss_hand_on_transition(transition, hand)
        return transition

    def _project_hook_transition(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool,
    ) -> ScoreProjectionTransition:
        """Branch over The Hook's random forced discard before hand scoring."""
        held = self._held_cards_after_play_selection(state, cards)
        discard_count = min(2, len(held))
        if discard_count <= 0:
            return self._project_non_hook_transition(
                hand,
                state,
                cards,
                include_card_chips=include_card_chips,
            )

        forced_branches = tuple(combinations(held, discard_count))
        branch_probability = 1.0 / len(forced_branches)
        outcomes: list[ScoreOutcome] = []
        unsupported: list[str] = []
        random_sources: list[str] = []
        single_transition = None

        for forced_cards in forced_branches:
            try:
                branch_state = self.discard_joker_projector.project(
                    state,
                    forced_cards,
                    consume_discard_use=False,
                )
            except UnsupportedDiscardProjection:
                return self._unresolved_boss_hand_transition(state)

            branch_state.hand = self._remove_cards(
                branch_state.hand,
                forced_cards,
            )
            transition = self._project_non_hook_transition(
                hand,
                branch_state,
                cards,
                include_card_chips=include_card_chips,
            )
            single_transition = transition
            unsupported.extend(transition.unsupported_jokers)
            random_sources.extend(transition.distribution.random_sources)

            for outcome in transition.distribution.outcomes:
                outcomes.append(
                    ScoreOutcome(
                        score=outcome.score,
                        probability=outcome.probability * branch_probability,
                        state_after_scoring=outcome.state_after_scoring,
                    )
                )

        random_sources.append(f"The Hook forced discard x{discard_count}")
        distribution = ScoreOutcomeDistribution(
            outcomes=tuple(outcomes),
            random_sources=tuple(dict.fromkeys(random_sources)),
        )
        common_state = (
            single_transition.state_after_scoring
            if len(forced_branches) == 1 and single_transition is not None
            else None
        )
        return ScoreProjectionTransition(
            distribution=distribution,
            state_after_scoring=common_state,
            unsupported_jokers=tuple(dict.fromkeys(unsupported)),
        )

    def _project_debuffed_hand(self, hand, state, cards) -> ScoreProjectionTransition:
        """Project Psychic/Eye/Mouth's whole-hand debuff without normal scoring."""
        safe_state = state.copy() if state is not None else None
        unsupported = ()

        if safe_state is not None:
            safe_state.jokers = deepcopy(list(getattr(state, "jokers", [])))
            original_jokers = list(safe_state.jokers)
            projected_jokers = project_independent_copy_jokers(
                original_jokers,
                safe_state,
            )

            if not matador_state_resolvable(safe_state):
                unsupported = ("Matador",)
            else:
                context = JokerContext(
                    state=safe_state,
                    score=HandScore(0, 0),
                    poker_hand=hand,
                    cards=list(cards or []),
                    trigger="HAND_SCORED",
                    data={"debuffed_hand": True},
                )
                for joker in projected_jokers:
                    if self._is_matador_activation(joker):
                        context = joker.apply(context)

            # Projected copy proxies are scorer-only. Preserve real Joker objects
            # in the branch state after the special debuffed-hand calculation.
            safe_state.jokers = original_jokers

        outcome = ScoreOutcome(
            score=0,
            probability=1.0,
            state_after_scoring=safe_state,
        )
        return ScoreProjectionTransition(
            distribution=ScoreOutcomeDistribution(outcomes=(outcome,)),
            state_after_scoring=safe_state,
            unsupported_jokers=unsupported,
        )

    @staticmethod
    def _hook_active(state) -> bool:
        return (
            state is not None
            and str(getattr(state, "boss_name", "") or "") == "The Hook"
            and not boss_blind_disabled_by_owned_jokers(state)
        )

    @classmethod
    def _held_cards_after_play_selection(cls, state, played_cards) -> list:
        return cls._remove_cards(
            list(getattr(state, "hand", []) or []),
            played_cards,
        )

    @classmethod
    def _remove_cards(cls, source, removed) -> list:
        remaining = list(source or [])
        for selected in list(removed or []):
            selected_identity = cls._card_identity(selected)
            for index, candidate in enumerate(remaining):
                if cls._card_identity(candidate) == selected_identity:
                    del remaining[index]
                    break
        return remaining

    @staticmethod
    def _card_identity(card):
        live_id = getattr(card, "live_id", None)
        if live_id is not None:
            return ("live", live_id)
        return ("object", id(card))

    @staticmethod
    def _is_matador_activation(joker) -> bool:
        if type(joker).__name__ == "MatadorJoker":
            return True
        return type(getattr(joker, "_target", None)).__name__ == "MatadorJoker"

    @staticmethod
    def _unresolved_boss_hand_transition(state) -> ScoreProjectionTransition:
        safe_state = deepcopy(state) if state is not None else None
        boss_name = str(getattr(state, "boss_name", "Unknown") or "Unknown")
        outcome = ScoreOutcome(
            score=0,
            probability=1.0,
            state_after_scoring=safe_state,
        )
        return ScoreProjectionTransition(
            distribution=ScoreOutcomeDistribution(outcomes=(outcome,)),
            state_after_scoring=safe_state,
            unsupported_jokers=(f"BossBlind:{boss_name}",),
        )

    @staticmethod
    def _record_accepted_boss_hand_on_transition(transition, hand) -> None:
        branch_states = []
        if transition.state_after_scoring is not None:
            branch_states.append(transition.state_after_scoring)
        branch_states.extend(
            outcome.state_after_scoring
            for outcome in transition.distribution.outcomes
            if outcome.state_after_scoring is not None
        )

        seen = set()
        for branch_state in branch_states:
            marker = id(branch_state)
            if marker in seen:
                continue
            seen.add(marker)
            record_accepted_boss_hand(branch_state, hand)

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
        """Preserve final Joker support inside nested visible-RNG branches."""
        branch_state = self._lucky_branch_input_state(state, lucky_branch)
        branch_scorer = _FinalProjectedStochasticScorer(
            lucky_mult_results=lucky_branch.mult_results,
            bloodstone_results=bloodstone_branch.results,
            misprint_results=misprint_results,
        )
        branch_projector = LiveFinalJokerScoreProjector(branch_scorer)
        return branch_projector.score(
            hand,
            branch_state,
            cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=False,
        )
