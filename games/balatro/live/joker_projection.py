from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.scoring import BalatroScorer, HandScore


@dataclass(frozen=True)
class JokerScoreProjection:
    """One side-effect-free Joker-aware scoring transition.

    ``state_after_scoring`` is an isolated branch state. Stateful supported Jokers
    may mutate inside that branch, but the authoritative observed state is never
    touched. Playing cards remain shared observation objects so the scorer's
    played/held identity checks stay correct without copying the deck.
    """

    score: HandScore
    state_after_scoring: object | None
    cards_after_copy: tuple
    unsupported_jokers: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.unsupported_jokers


class LiveJokerScoreProjector:
    """Apply explicitly validated live Jokers on an isolated branch state.

    Live-state hydration and score-transition support are separate contracts. A
    Joker can be reconstructed perfectly from public memory and still require event
    sequencing, stochastic branch semantics, scoring-card identity, retriggers or
    card mutation isolation that this projector does not yet model.

    ``SUPPORTED_CLASS_NAMES`` contains only implementations whose current
    ``HAND_SCORED`` path is safe and complete under this projection context.
    ``DEFERRED_HYDRATED_CLASS_NAMES`` accounts for the remaining mutable hydrated
    Jokers so new live-state coverage cannot be mistaken for runtime support.

    Live score search is hot code. ``BalatroState.copy()`` gives independent state
    containers while deliberately retaining playing-card identity. Joker objects
    are deep-copied so validated mutable Joker transitions cannot touch the
    authoritative observed state.
    """

    SUPPORTED_CLASS_NAMES = frozenset(
        {
            "AncientJoker",
            "BootstrapsJoker",
            "CampfireJoker",
            "CastleJoker",
            "CavendishJoker",
            "ConstellationJoker",
            "DaggerJoker",
            "EggJoker",
            "FlashCardJoker",
            "FortuneTellerJoker",
            "GreenJoker",
            "GrosMichelJoker",
            "HitTheRoadJoker",
            "HologramJoker",
            "IceCreamJoker",
            "InvisibleJoker",
            "MadnessJoker",
            "PopcornJoker",
            "RamenJoker",
            "RunnerJoker",
            "SpareTrousersJoker",
            "SquareJoker",
            "ThrowbackJoker",
            "TurtleBeanJoker",
            "WeeJoker",
            "YorickJoker",
        }
    )

    DEFERRED_HYDRATED_CLASS_NAMES = frozenset(
        {
            "CanioJoker",
            "LoyaltyCardJoker",
            "LuckyCatJoker",
            "ObeliskJoker",
            "RedCardJoker",
            "RideTheBusJoker",
            "SeltzerJoker",
            "VampireJoker",
        }
    )

    DEFERRED_REASONS_BY_CLASS = {
        "CanioJoker": (
            "requires destroyed-card transition/stochastic propagation before scoring"
        ),
        "LoyaltyCardJoker": (
            "requires HAND_PLAYED transition sequencing before score projection"
        ),
        "LuckyCatJoker": (
            "requires LUCKY_TRIGGERED stochastic branch-state propagation"
        ),
        "ObeliskJoker": (
            "requires authoritative most-played-hand history in the scoring context"
        ),
        "RedCardJoker": (
            "model must apply accumulated hydrated Mult during ordinary HAND_SCORED"
        ),
        "RideTheBusJoker": (
            "requires scoring-card identity rather than treating every played card as scoring"
        ),
        "SeltzerJoker": (
            "requires played-card retrigger execution; scorer does not consume retrigger signal yet"
        ),
        "VampireJoker": (
            "mutates card enhancements and therefore requires isolated branch card copies"
        ),
    }

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

        # Keep card identity intact: BalatroState.copy() shallow-copies the hand and
        # deck lists, so action cards still match objects in safe_state.hand. This is
        # why card-mutating effects such as Vampire remain deferred for now.
        safe_state = state.copy()
        safe_state.jokers = deepcopy(list(getattr(state, "jokers", [])))
        safe_cards = list(cards or [])

        all_jokers = list(getattr(safe_state, "jokers", []))
        supported = [joker for joker in all_jokers if self.supports(joker)]
        unsupported = tuple(
            self._joker_name(joker)
            for joker in all_jokers
            if not self.supports(joker)
        )

        # Only validated Joker implementations participate in the score. Restore
        # the full copied list afterwards so the branch retains complete ownership
        # metadata for future validation/expansion.
        safe_state.jokers = supported
        score = self.scorer.score(
            hand,
            safe_state,
            cards=safe_cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=resolve_random_effects,
        )
        safe_state.jokers = all_jokers

        return JokerScoreProjection(
            score=score,
            state_after_scoring=safe_state,
            cards_after_copy=tuple(safe_cards),
            unsupported_jokers=unsupported,
        )

    @staticmethod
    def _joker_name(joker) -> str:
        label = getattr(joker, "label", None)
        if isinstance(label, str) and label:
            return label
        name = type(joker).__name__
        return name.removesuffix("Joker").replace("_", " ")
