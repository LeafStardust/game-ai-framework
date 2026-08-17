from __future__ import annotations

from dataclasses import dataclass, fields

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND
from games.balatro.blind_skip_policy import (
    BlindSkipDecision,
    BlindSkipThresholds,
    BuildAwareBlindSkipPolicy,
)
from games.balatro.strategy import BalatroStrategyTracker, StrategyDefinition
from games.balatro.strategy_compat import NeutralLegacyPlaystyleIntentTracker


_STRATEGY_SENSITIVE_TAGS = frozenset(
    {
        "tag_buffoon",
        "tag_charm",
        "tag_ethereal",
        "tag_meteor",
        "tag_orbital",
        "tag_standard",
        "tag_voucher",
    }
)


@dataclass(frozen=True)
class StrategyAwareBlindSkipDecision(BlindSkipDecision):
    strategy_tag_adjustment: float = 0.0
    dominant_strategy_id: str | None = None
    relevant_strategy_ids: tuple[str, ...] = ()
    strategy_tag_support: str = "none"

    @property
    def notes(self) -> tuple[str, ...]:
        relevant = ",".join(self.relevant_strategy_ids) or "NONE"
        return (
            *super().notes,
            f"strategy_dominant={self.dominant_strategy_id or 'NONE'}",
            f"strategy_relevant={relevant}",
            f"strategy_tag_adjustment={self.strategy_tag_adjustment:.3f}",
            f"strategy_tag_support={self.strategy_tag_support}",
        )


def _positive_joker_support(definition: StrategyDefinition) -> bool:
    return bool(
        definition.gold_jokers
        or definition.silver_jokers
        or definition.bronze_jokers
    )


def _positive_consumable_support(definition: StrategyDefinition) -> bool:
    return bool(
        definition.gold_consumables
        or definition.silver_consumables
        or definition.bronze_consumables
    )


def _positive_planet_support(definition: StrategyDefinition) -> bool:
    return bool(
        definition.gold_planets
        or definition.silver_planets
        or definition.bronze_planets
    )


def _positive_voucher_support(definition: StrategyDefinition) -> bool:
    return bool(
        definition.gold_vouchers
        or definition.silver_vouchers
        or definition.bronze_vouchers
    )


def _deck_shaping_support(definition: StrategyDefinition) -> bool:
    return bool(
        definition.primary_hands
        or definition.preferred_suits
        or definition.preferred_enhancements
        or definition.preferred_seals
        or definition.preferred_editions
        or definition.preferred_ranks
        or definition.face_mode
        or definition.any_suit_concentration
    )


def _unique_most_played_hand(state) -> str | None:
    counts = getattr(state, "hand_play_counts", {}) or {}
    positive = {
        str(hand).upper(): max(0, int(count or 0))
        for hand, count in counts.items()
        if int(count or 0) > 0
    }
    if not positive:
        return None
    best = max(positive.values())
    leaders = sorted(hand for hand, count in positive.items() if count == best)
    return leaders[0] if len(leaders) == 1 else None


def _definition_supports_tag(
    definition: StrategyDefinition,
    tag_key: str | None,
    state,
) -> bool:
    if tag_key == "tag_buffoon":
        # Buffoon packs expose choices after opening, so current strategy knowledge
        # can legitimately raise the value of the opportunity without assuming the
        # hidden pack contents before the skip decision.
        return _positive_joker_support(definition)
    if tag_key in {"tag_charm", "tag_ethereal"}:
        return _positive_consumable_support(definition)
    if tag_key == "tag_meteor":
        return bool(definition.primary_hands) and _positive_planet_support(definition)
    if tag_key == "tag_orbital":
        most_played = _unique_most_played_hand(state)
        return most_played is not None and most_played in definition.primary_hands
    if tag_key == "tag_standard":
        return _deck_shaping_support(definition)
    if tag_key == "tag_voucher":
        return _positive_voucher_support(definition)
    return False


class StrategyAwareBlindSkipPolicy(BuildAwareBlindSkipPolicy):
    """D13 tag EV with bounded universal-strategy reinforcement.

    Blind reward, interest, lost-shop value and pre-boss preparation remain the
    primary play-vs-skip economics from ``BuildAwareBlindSkipPolicy``. This layer
    only changes the tag side of that comparison when the tag's public effect can
    actually reinforce a dominant/relevant universal strategy. Hidden future tag
    contents are never inspected or assumed.
    """

    def __init__(
        self,
        *,
        strategy_tracker: BalatroStrategyTracker,
        profiler=None,
        intent_tracker=None,
    ) -> None:
        super().__init__(
            profiler=profiler,
            intent_tracker=(
                intent_tracker or NeutralLegacyPlaystyleIntentTracker()
            ),
        )
        self.strategy_tracker = strategy_tracker

    def _strategy_tag_adjustment(
        self,
        state,
        *,
        tag_key: str | None,
        thresholds: BlindSkipThresholds,
    ) -> tuple[float, str, str | None, tuple[str, ...]]:
        resolution = self.strategy_tracker.observe(state)
        dominant_id = resolution.dominant_strategy_id
        relevant_ids = resolution.relevant_strategy_ids
        if dominant_id is None:
            return 0.0, "no-positive-strategy-evidence", None, relevant_ids
        if tag_key not in _STRATEGY_SENSITIVE_TAGS:
            return 0.0, "tag-has-no-strategy-specific-public-effect", dominant_id, relevant_ids

        shortlist = resolution.shortlist_strategy_ids
        shortlist_weights = (1.0, 0.65, 0.45)
        support = 0.0
        supporting: list[str] = []
        for index, strategy_id in enumerate(shortlist):
            definition = self.strategy_tracker.definitions.get(strategy_id)
            if definition is None:
                continue
            if not _definition_supports_tag(definition, tag_key, state):
                continue
            weight = shortlist_weights[min(index, len(shortlist_weights) - 1)]
            support = max(support, weight)
            supporting.append(strategy_id)

        pressure = float(self.strategy_tracker.strategy_pressure(state))
        fit_weight = float(thresholds.tag_build_fit_weight)
        cap = float(thresholds.max_tag_build_adjustment)
        if support > 0.0:
            adjustment = min(cap, support * pressure * fit_weight)
            return (
                adjustment,
                "supports:" + ",".join(supporting),
                dominant_id,
                relevant_ids,
            )

        # Choice-preserving development tags should not be penalized merely because
        # the unopened reward does not map to the current shortlist: D9/D10 may
        # inspect the exposed choices and skip them. Orbital is different because
        # its target hand is public and deterministic at blind-select time.
        if tag_key != "tag_orbital":
            return 0.0, "choice-preserving-tag-neutral", dominant_id, relevant_ids

        # A known Orbital upgrade aimed at an off-shortlist hand is never hard-banned.
        # Early exploration remains neutral; convergence introduces only a bounded
        # opportunity-cost penalty as the run becomes more committed.
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante <= 2:
            return 0.0, "early-exploration-neutral", dominant_id, relevant_ids
        penalty_fraction = 0.25 if ante <= 5 else 0.50
        adjustment = -min(cap, penalty_fraction * pressure * fit_weight)
        return adjustment, "off-shortlist-development-tag", dominant_id, relevant_ids

    def decide(
        self,
        snapshot,
        state,
        *,
        thresholds: BlindSkipThresholds | None = None,
    ) -> StrategyAwareBlindSkipDecision:
        thresholds = thresholds or BlindSkipThresholds()
        base = super().decide(snapshot, state, thresholds=thresholds)
        strategy_adjustment, support, dominant_id, relevant_ids = (
            self._strategy_tag_adjustment(
                state,
                tag_key=base.tag_key,
                thresholds=thresholds,
            )
        )

        skip_ev = float(base.skip_ev) + strategy_adjustment
        margin = skip_ev - float(base.play_ev)
        action_name = (
            SKIP_BLIND
            if base.blind_type in {"SMALL", "BIG"}
            and margin >= float(base.threshold)
            else SELECT_BLIND
        )

        values = {
            field.name: getattr(base, field.name)
            for field in fields(BlindSkipDecision)
        }
        values.update(
            action_name=action_name,
            skip_ev=skip_ev,
            margin=margin,
        )
        return StrategyAwareBlindSkipDecision(
            **values,
            strategy_tag_adjustment=strategy_adjustment,
            dominant_strategy_id=dominant_id,
            relevant_strategy_ids=tuple(relevant_ids),
            strategy_tag_support=support,
        )
