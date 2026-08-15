from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.joker import JokerContext
from games.balatro.scoring import BalatroScorer, HandScore


@dataclass(frozen=True)
class JokerScoreProjection:
    """One side-effect-free Joker-aware scoring transition.

    ``state_after_scoring`` is an isolated branch state. Stateful supported Jokers
    may mutate inside that branch, but the authoritative observed state is never
    touched. Cards remain shared on the hot path unless a validated effect such as
    Vampire requires branch-local card mutation.
    """

    score: HandScore
    state_after_scoring: object | None
    cards_after_copy: tuple
    unsupported_jokers: tuple[str, ...] = ()
    played_card_retriggers: int = 0

    @property
    def complete(self) -> bool:
        return not self.unsupported_jokers


class LiveJokerScoreProjector:
    """Apply explicitly validated live Jokers on an isolated branch state.

    Live-state hydration and score-transition support are separate contracts. A
    Joker can be reconstructed perfectly from public memory and still require event
    sequencing or stochastic branch semantics that the planner does not model.

    The projector executes the small pre-score ``HAND_PLAYED`` transition required
    by admitted Jokers before delegating ordinary ``HAND_SCORED`` resolution to the
    scorer. Card copies are created only when a supported Joker mutates card state;
    otherwise the original cheap identity-preserving branch copy remains in use.
    """

    SUPPORTED_CLASS_NAMES = frozenset(
        {
            "AncientJoker",
            "BannerJoker",
            "BootstrapsJoker",
            "CampfireJoker",
            "CanioJoker",
            "CastleJoker",
            "CavendishJoker",
            "CleverJoker",
            "ConstellationJoker",
            "CraftyJoker",
            "DaggerJoker",
            "DrollJoker",
            "EggJoker",
            "EvenStevenJoker",
            "FibonacciJoker",
            "FlashCardJoker",
            "FortuneTellerJoker",
            "GluttonousJoker",
            "GreenJoker",
            "GreedyJoker",
            "GrosMichelJoker",
            "HalfJoker",
            "HitTheRoadJoker",
            "HologramJoker",
            "IceCreamJoker",
            "InvisibleJoker",
            "JollyJoker",
            "LoyaltyCardJoker",
            "LuckyCatJoker",
            "LustyJoker",
            "MadnessJoker",
            "ObeliskJoker",
            "OddToddJoker",
            "PerkeoJoker",
            "PhotographJoker",
            "PopcornJoker",
            "RamenJoker",
            "RedCardJoker",
            "RideTheBusJoker",
            "RunnerJoker",
            "ScaryFaceJoker",
            "ScholarJoker",
            "SeltzerJoker",
            "SlyJoker",
            "SmileyFaceJoker",
            "SpareTrousersJoker",
            "SquareJoker",
            "ThrowbackJoker",
            "TribouletJoker",
            "TurtleBeanJoker",
            "VampireJoker",
            "WeeJoker",
            "WilyJoker",
            "WrathfulJoker",
            "YorickJoker",
        }
    )

    DEFERRED_HYDRATED_CLASS_NAMES = frozenset()
    DEFERRED_REASONS_BY_CLASS = {}

    HAND_PLAYED_CLASS_NAMES = frozenset(
        {
            "LoyaltyCardJoker",
            "VampireJoker",
        }
    )

    CARD_MUTATING_CLASS_NAMES = frozenset(
        {
            "VampireJoker",
        }
    )

    def __init__(self, scorer: BalatroScorer | None = None):
        self.scorer = scorer or BalatroScorer()

    @classmethod
    def supports(cls, joker) -> bool:
        return type(joker).__name__ in cls.SUPPORTED_CLASS_NAMES

    @classmethod
    def deferred_reason(cls, class_name: str) -> str | None:
        if class_name not in cls.DEFERRED_HYDRATED_CLASS_NAMES:
            return None
        return cls.DEFERRED_REASONS_BY_CLASS.get(
            class_name,
            "requires explicit HAND_SCORED/event-transition validation",
        )

    def unsupported_jokers(self, state) -> tuple[str, ...]:
        if state is None:
            return ()
        return tuple(
            self._joker_name(joker)
            for joker in getattr(state, "jokers", [])
            if not self.supports(joker)
        )

    def score(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
        resolve_random_effects: bool = False,
    ) -> JokerScoreProjection:
        if state is None:
            score = self.scorer.score(
                hand,
                None,
                cards=list(cards or []),
                include_card_chips=include_card_chips,
                resolve_random_effects=resolve_random_effects,
            )
            return JokerScoreProjection(
                score=score,
                state_after_scoring=None,
                cards_after_copy=tuple(cards or ()),
            )

        safe_state = state.copy()
        safe_state.jokers = deepcopy(list(getattr(state, "jokers", [])))

        all_jokers = list(getattr(safe_state, "jokers", []))
        supported = [joker for joker in all_jokers if self.supports(joker)]
        unsupported = tuple(
            self._joker_name(joker)
            for joker in all_jokers
            if not self.supports(joker)
        )

        if self._requires_card_isolation(supported):
            safe_cards = self._isolate_branch_cards(state, safe_state, cards)
        else:
            safe_cards = list(cards or [])

        safe_state.jokers = supported
        joker_data = self._prepare_hand_play(
            hand,
            safe_state,
            safe_cards,
            supported,
        )
        played_card_retriggers = self._seltzer_retriggers(supported)
        if played_card_retriggers:
            joker_data["retrigger_played_cards"] = (
                int(joker_data.get("retrigger_played_cards", 0) or 0)
                + played_card_retriggers
            )

        score = self.scorer.score(
            hand,
            safe_state,
            cards=safe_cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=resolve_random_effects,
            joker_data=joker_data,
        )
        self._consume_seltzer_hand(supported)
        self._increment_hand_play_count(safe_state, hand)
        safe_state.jokers = all_jokers

        return JokerScoreProjection(
            score=score,
            state_after_scoring=safe_state,
            cards_after_copy=tuple(safe_cards),
            unsupported_jokers=unsupported,
            played_card_retriggers=played_card_retriggers,
        )

    def _prepare_hand_play(self, hand, state, cards, jokers) -> dict:
        active = [
            joker
            for joker in jokers
            if type(joker).__name__ in self.HAND_PLAYED_CLASS_NAMES
        ]
        if not active:
            return {}

        scoring_cards = [
            card
            for card in self.scorer.scoring_cards(hand, cards)
            if not self.scorer.is_card_debuffed(card)
        ]
        context = JokerContext(
            state=state,
            poker_hand=hand,
            cards=list(cards or []),
            trigger="HAND_PLAYED",
            data={"scoring_cards": scoring_cards},
        )
        for joker in active:
            context = joker.apply(context)
        return context.data

    @staticmethod
    def _seltzer_retriggers(jokers) -> int:
        return sum(
            1
            for joker in jokers
            if type(joker).__name__ == "SeltzerJoker"
            and int(getattr(joker, "rounds_remaining", 0) or 0) > 0
        )

    @staticmethod
    def _consume_seltzer_hand(jokers) -> None:
        for joker in jokers:
            if type(joker).__name__ != "SeltzerJoker":
                continue
            remaining = int(getattr(joker, "rounds_remaining", 0) or 0)
            if remaining > 0:
                joker.rounds_remaining = remaining - 1

    @classmethod
    def _requires_card_isolation(cls, jokers) -> bool:
        return any(
            type(joker).__name__ in cls.CARD_MUTATING_CLASS_NAMES
            for joker in jokers
        )

    @staticmethod
    def _isolate_branch_cards(state, safe_state, cards) -> list:
        copies: dict[int, object] = {}

        def clone(card):
            key = id(card)
            if key not in copies:
                copies[key] = deepcopy(card)
            return copies[key]

        safe_state.hand = [clone(card) for card in getattr(state, "hand", [])]
        safe_state.deck = [clone(card) for card in getattr(state, "deck", [])]
        return [clone(card) for card in list(cards or [])]

    @staticmethod
    def _increment_hand_play_count(state, hand) -> None:
        counts = getattr(state, "hand_play_counts", None)
        if not isinstance(counts, dict):
            return

        current = int(counts.get(hand.value, counts.get(hand, 0)) or 0)
        updated = current + 1
        counts[hand.value] = updated
        if hand in counts:
            counts[hand] = updated

    @staticmethod
    def _joker_name(joker) -> str:
        label = getattr(joker, "label", None)
        if isinstance(label, str) and label:
            return label
        name = type(joker).__name__
        return name.removesuffix("Joker").replace("_", " ")
