from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.scoring import BalatroScorer, HandScore


@dataclass(frozen=True)
class JokerScoreProjection:
    """One side-effect-free Joker-aware scoring transition.

    ``state_after_scoring`` is an isolated branch state. Stateful supported Jokers
    may mutate inside that branch, but the authoritative observed state is never
    touched. Playing cards remain shared immutable observation objects so the
    scorer's played/held identity checks stay correct without copying the deck.
    """

    score: HandScore
    state_after_scoring: object | None
    cards_after_copy: tuple
    unsupported_jokers: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.unsupported_jokers


class LiveJokerScoreProjector:
    """Apply explicitly supported live Jokers on an isolated branch state.

    Mutable Joker run state is reconstructed by the live observer/factory before
    this layer runs. The stateful classes below are therefore safe to execute on a
    hypothetical ``HAND_SCORED`` branch without falling back to constructor
    defaults. Bootstraps remains explicitly admitted from the original validated
    stateless support.

    The contract is deliberately fail-closed: adding a new Joker implementation or
    a new mutable live-state contract does not silently make it part of score
    projection. Tests require every currently hydrated mutable Joker to be listed
    here, while still leaving unrelated/stateless projection expansion as a
    separate validation task.

    Live score search is extremely hot code. ``BalatroState.copy()`` already gives
    us independent state containers while deliberately retaining playing-card
    identity. Only Joker objects need a deep copy. This avoids deep-copying the full
    hand/deck on every hypothetical score probe while still isolating stateful Joker
    mutation such as Ice Cream decay, Green Joker growth and Runner growth.
    """

    SUPPORTED_CLASS_NAMES = frozenset(
        {
            "AncientJoker",
            "BootstrapsJoker",
            "CampfireJoker",
            "CanioJoker",
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
            "LoyaltyCardJoker",
            "LuckyCatJoker",
            "MadnessJoker",
            "ObeliskJoker",
            "PopcornJoker",
            "RamenJoker",
            "RedCardJoker",
            "RideTheBusJoker",
            "RunnerJoker",
            "SeltzerJoker",
            "SpareTrousersJoker",
            "SquareJoker",
            "TheIdolJoker",
            "ThrowbackJoker",
            "TurtleBeanJoker",
            "VampireJoker",
            "WeeJoker",
            "YorickJoker",
        }
    )

    def __init__(self, scorer: BalatroScorer | None = None):
        self.scorer = scorer or BalatroScorer()

    @classmethod
    def supports(cls, joker) -> bool:
        return type(joker).__name__ in cls.SUPPORTED_CLASS_NAMES

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
        # deck lists, so action cards still match objects in safe_state.hand. The
        # scorer relies on that identity to exclude played cards from held effects.
        # Deep-copy Jokers because validated live Jokers may mutate themselves.
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
