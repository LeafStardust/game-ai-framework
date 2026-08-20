from __future__ import annotations

"""Public-state adapters for realized engine strength and Build Health.

This module intentionally reads only ordinary BalatroState/Joker state.  It does
not inspect hidden draw order, RNG state, seed data, or future shop contents.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.build_health import (
    BuildHealth,
    BuildHealthEvaluator,
    BuildHealthInputs,
    EngineState,
    RealizedEngineStrength,
)
from games.balatro.scoring import BalatroScorer
from games.balatro.strategy import BRONZE, GOLD, SILVER


_POSITIVE_TIERS = {GOLD, SILVER, BRONZE}


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    candidates = (
        getattr(joker, "name", None),
        getattr(joker, "label", None),
        getattr(joker, "ability_name", None),
        type(joker).__name__,
    )
    for candidate in candidates:
        token = _normalize(candidate or "")
        if token:
            return token
    return ""


def _public_number(joker: object, key: str, default: float = 0.0) -> float:
    value = getattr(joker, key, None)
    if value is None:
        public = getattr(joker, "public_state", None)
        if isinstance(public, dict):
            value = public.get(key, default)
        elif public is not None:
            value = getattr(public, key, default)
        else:
            value = default
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _blind_target(state) -> float:
    for value in (
        getattr(state, "blind_score", 0),
        getattr(state, "blind_requirement", 0),
    ):
        try:
            number = float(value or 0)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    blind = getattr(state, "blind", None)
    for key in ("requirement", "score", "chips"):
        try:
            number = float(getattr(blind, key, 0) or 0)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return 0.0


def _hands_budget(state) -> int:
    try:
        hands = int(getattr(state, "hands_remaining", 0) or 0)
    except (TypeError, ValueError):
        hands = 0
    # Shop observations may retain zero hands from the completed blind.  The next
    # Red/White blind restores the ordinary four-hand budget, so do not diagnose a
    # certain loss merely from that stale round counter.
    if hands <= 0 and str(getattr(state, "phase", "")).upper() == "SHOP":
        return 4
    return max(1, hands)


def _deck_size(state) -> int:
    owned = getattr(state, "owned_deck", None)
    if owned is not None:
        try:
            return len(owned)
        except TypeError:
            pass
    try:
        return len(getattr(state, "deck", ()) or ())
    except TypeError:
        return 0


def _progress_state(progress_ratio: float) -> EngineState:
    progress = max(0.0, float(progress_ratio))
    if progress <= 0.0:
        return EngineState.OWNED_INACTIVE
    if progress < 0.50:
        return EngineState.ACTIVATED_WEAK
    if progress < 1.50:
        return EngineState.ACTIVATED_HEALTHY
    return EngineState.MATURE


def _runway_need(state: EngineState, ante: int) -> float:
    base = {
        EngineState.NOT_OWNED: 0.0,
        EngineState.OWNED_INACTIVE: 0.75,
        EngineState.ACTIVATED_WEAK: 0.50,
        EngineState.ACTIVATED_HEALTHY: 0.20,
        EngineState.MATURE: 0.0,
    }[state]
    if state in {EngineState.OWNED_INACTIVE, EngineState.ACTIVATED_WEAK} and ante >= 5:
        base += 0.15
    return min(1.0, base)


@dataclass(frozen=True)
class RealizedEngineAnalyzer:
    """Translate observable Joker progress into comparable engine lifecycle states."""

    def analyze(self, state) -> tuple[RealizedEngineStrength, ...]:
        jokers = tuple(getattr(state, "jokers", ()) or ())
        tokens = {_joker_token(joker): joker for joker in jokers}
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        target = _blind_target(state)
        pace = target / max(1, _hands_budget(state)) if target > 0 else 0.0
        engines: list[RealizedEngineStrength] = []

        def find(*needles: str):
            normalized = tuple(_normalize(value) for value in needles)
            for token, joker in tokens.items():
                if any(token == needle or token.endswith(needle) for needle in normalized):
                    return joker
            return None

        hologram = find("hologram", "hologramjoker")
        if hologram is not None:
            x_mult = max(1.0, _public_number(hologram, "x_mult", 1.0))
            gain = max(0.0, x_mult - 1.0)
            # One added playing card per completed Ante is a deliberately modest
            # realized-growth schedule; the relationship catalogue remains separate.
            target_gain = max(0.25, 0.25 * max(1, ante - 1))
            progress = gain / target_gain if target_gain else 0.0
            engine_state = _progress_state(progress)
            has_generator = find("certificate", "certificatejoker", "marblejoker", "marble") is not None
            engines.append(
                RealizedEngineStrength(
                    engine_id="hologram",
                    state=engine_state,
                    current_strength=x_mult,
                    growth_rate=1.0 if has_generator else (0.25 if gain > 0 else 0.0),
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"public Hologram xMult={x_mult:.2f}",
                        f"realized growth target for Ante {ante}=+{target_gain:.2f} xMult",
                        f"card generator owned={'yes' if has_generator else 'no'}",
                    ),
                )
            )

        blue = find("bluejoker", "bluejokerjoker")
        if blue is not None:
            cards = _deck_size(state)
            chips = max(0.0, cards * 2.0)
            progress = chips / max(pace * 0.20, 1.0) if pace > 0 else chips / 100.0
            engine_state = _progress_state(progress)
            engines.append(
                RealizedEngineStrength(
                    engine_id="blue_joker",
                    state=engine_state,
                    current_strength=chips,
                    growth_rate=0.50 if cards >= 52 else 0.20,
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"owned deck size={cards}; Blue Joker contribution={chips:.0f} chips",
                        "strength normalized against 20% of current per-hand blind pace",
                    ),
                )
            )

        green = find("greenjoker", "greenjokerjoker")
        if green is not None:
            mult = max(0.0, _public_number(green, "mult", 0.0))
            target_mult = max(4.0, float(ante * 2))
            engine_state = _progress_state(mult / target_mult)
            engines.append(
                RealizedEngineStrength(
                    engine_id="green_joker",
                    state=engine_state,
                    current_strength=mult,
                    growth_rate=1.0,
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"public Green Joker Mult=+{mult:.0f}",
                        f"realized Ante {ante} target=+{target_mult:.0f} Mult",
                    ),
                )
            )

        castle = find("castle", "castlejoker")
        if castle is not None:
            chips = max(0.0, _public_number(castle, "chips", 0.0))
            progress = chips / max(pace * 0.10, 1.0) if pace > 0 else chips / 30.0
            engine_state = _progress_state(progress)
            discards = max(0, int(getattr(state, "discards_remaining", 0) or 0))
            engines.append(
                RealizedEngineStrength(
                    engine_id="castle",
                    state=engine_state,
                    current_strength=chips,
                    growth_rate=min(1.0, discards / 3.0),
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"public Castle chips=+{chips:.0f}",
                        f"discards currently available={discards}",
                    ),
                )
            )

        runner = find("runner", "runnerjoker")
        if runner is not None:
            chips = max(0.0, _public_number(runner, "chips", 0.0))
            progress = chips / max(pace * 0.10, 15.0) if pace > 0 else chips / 30.0
            engine_state = _progress_state(progress)
            counts = getattr(state, "hand_play_counts", {}) or {}
            straight_plays = int(counts.get("STRAIGHT", counts.get("Straight", 0)) or 0)
            engines.append(
                RealizedEngineStrength(
                    engine_id="runner",
                    state=engine_state,
                    current_strength=chips,
                    growth_rate=min(1.0, straight_plays / max(1.0, float(ante * 2))),
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"public Runner chips=+{chips:.0f}",
                        f"Straight play history={straight_plays}",
                    ),
                )
            )

        red_card = find("redcard", "redcardjoker")
        if red_card is not None:
            mult = max(0.0, _public_number(red_card, "mult", 0.0))
            target_mult = max(3.0, float(max(1, ante - 1) * 3))
            engine_state = _progress_state(mult / target_mult)
            engines.append(
                RealizedEngineStrength(
                    engine_id="red_card",
                    state=engine_state,
                    current_strength=mult,
                    growth_rate=0.50,
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"public Red Card Mult=+{mult:.0f}",
                        f"realized Ante {ante} target=+{target_mult:.0f} Mult",
                    ),
                )
            )

        burnt = find("burntjoker", "burnt")
        if burnt is not None:
            levels = getattr(state, "hand_levels", {}) or {}
            max_level = max((int(value or 1) for value in levels.values()), default=1)
            progress_levels = max(0, max_level - 1)
            target_levels = max(1, ante - 1)
            engine_state = _progress_state(progress_levels / target_levels)
            engines.append(
                RealizedEngineStrength(
                    engine_id="burnt_joker",
                    state=engine_state,
                    current_strength=float(max_level),
                    growth_rate=1.0 if int(getattr(state, "discards_remaining", 0) or 0) > 0 else 0.50,
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"highest public hand level={max_level}",
                        f"realized Burnt target by Ante {ante}=level {target_levels + 1}",
                    ),
                )
            )

        bull = find("bull", "bulljoker")
        bootstraps = find("bootstraps", "bootstrapsjoker")
        if bull is not None or bootstraps is not None:
            money = max(0, int(getattr(state, "money", 0) or 0))
            target_cash = max(10.0, float(ante * 5))
            engine_state = _progress_state(money / target_cash)
            contribution = 0.0
            if bull is not None:
                contribution += money * 2.0
            if bootstraps is not None:
                contribution += (money // 5) * 2.0
            engines.append(
                RealizedEngineStrength(
                    engine_id="cash_scoring",
                    state=engine_state,
                    current_strength=contribution,
                    growth_rate=0.75 if money >= 5 else 0.25,
                    runway_need=_runway_need(engine_state, ante),
                    rationale=(
                        f"cash=${money}; realized Ante {ante} cash target=${target_cash:.0f}",
                        f"Bull owned={'yes' if bull is not None else 'no'}; Bootstraps owned={'yes' if bootstraps is not None else 'no'}",
                    ),
                )
            )

        return tuple(engines)


class RuntimeBuildHealthEvaluator:
    """Evaluate Build Health from current public state and optional strategy tracker."""

    _ENGINE_SCORE = {
        EngineState.NOT_OWNED: 0.0,
        EngineState.OWNED_INACTIVE: 0.10,
        EngineState.ACTIVATED_WEAK: 0.35,
        EngineState.ACTIVATED_HEALTHY: 0.70,
        EngineState.MATURE: 1.0,
    }

    def __init__(
        self,
        *,
        scorer: BalatroScorer | None = None,
        engine_analyzer: RealizedEngineAnalyzer | None = None,
        health_evaluator: BuildHealthEvaluator | None = None,
    ) -> None:
        self.scorer = scorer or BalatroScorer()
        self.engine_analyzer = engine_analyzer or RealizedEngineAnalyzer()
        self.health_evaluator = health_evaluator or BuildHealthEvaluator()

    def _representative_best_score(self, state) -> float:
        scores: list[float] = []
        for hand, template_cards in JokerBuildValueEvaluator.PROBES:
            probe_state = deepcopy(state)
            cards = deepcopy(list(template_cards))
            probe_state.hand = deepcopy(cards)
            try:
                score = self.scorer.score(
                    hand,
                    state=probe_state,
                    cards=cards,
                    resolve_random_effects=False,
                ).total
            except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
                continue
            scores.append(max(0.0, float(score)))
        return max(scores, default=0.0)

    def _survival_and_immediate(self, state) -> tuple[float, float]:
        target = _blind_target(state)
        if target <= 0:
            return 0.50, 0.50
        hands = _hands_budget(state)
        best = self._representative_best_score(state)
        pace = target / max(1, hands)
        immediate = min(1.0, best / max(pace, 1.0))
        capacity = best * hands
        survival = min(1.0, capacity / target)
        return survival, immediate

    def _scaling(self, state, engines: tuple[RealizedEngineStrength, ...]) -> float:
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if not engines:
            # Lack of a scaler is not a crisis during Foundation, but it is a real
            # midgame warning once blind growth begins to outrun static filler.
            return 0.65 if ante <= 2 else 0.25
        values = sorted(
            (
                min(1.0, self._ENGINE_SCORE[engine.state] + 0.15 * max(0.0, min(1.0, engine.growth_rate)))
                for engine in engines
            ),
            reverse=True,
        )
        if len(values) == 1:
            return values[0]
        return min(1.0, values[0] * 0.70 + values[1] * 0.30)

    def _coherence(self, state, tracker) -> float:
        if tracker is None:
            return 0.50
        try:
            resolution = tracker.observe(state)
        except (AttributeError, KeyError, TypeError, ValueError):
            return 0.50
        dominant_id = getattr(resolution, "dominant_strategy_id", None)
        if dominant_id is None:
            return 0.35
        getter = getattr(tracker, "primary_strategy_id", None)
        if callable(getter):
            dominant_id = getter(resolution) or dominant_id
        assessment = resolution.assessment(dominant_id)
        score = max(0.0, float(getattr(assessment, "score", 0.0) or 0.0)) if assessment is not None else 0.0
        score_ratio = min(1.0, score / 9.0)

        jokers = tuple(getattr(state, "jokers", ()) or ())
        if not jokers:
            aligned_ratio = 0.0
        else:
            aligned = 0
            for joker in jokers:
                try:
                    relation = tracker.evaluate_item(state, joker, kind="JOKER")
                except (AttributeError, KeyError, TypeError, ValueError):
                    continue
                if (
                    bool(getattr(relation, "active_alignment", False))
                    and getattr(relation, "strategy_id", None) == dominant_id
                    and getattr(relation, "tier", None) in _POSITIVE_TIERS
                ):
                    aligned += 1
            aligned_ratio = aligned / len(jokers)
        return min(1.0, score_ratio * 0.60 + aligned_ratio * 0.40)

    @staticmethod
    def _runway(state, engines: tuple[RealizedEngineStrength, ...]) -> float:
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        horizon = max(0.0, min(1.0, (9.0 - ante) / 8.0))
        if not engines:
            return max(0.20, horizon)
        need = max((max(0.0, min(1.0, engine.runway_need)) for engine in engines), default=0.0)
        if need <= 0.0:
            return 1.0
        if horizon >= need:
            return 1.0
        return max(0.0, min(1.0, horizon / need))

    def inputs(self, state, *, strategy_tracker=None) -> BuildHealthInputs:
        engines = self.engine_analyzer.analyze(state)
        survival, immediate = self._survival_and_immediate(state)
        return BuildHealthInputs(
            survival_probability=survival,
            immediate_score_ratio=immediate,
            scaling_ratio=self._scaling(state, engines),
            coherence_ratio=self._coherence(state, strategy_tracker),
            runway_ratio=self._runway(state, engines),
            engines=engines,
        )

    def evaluate(self, state, *, strategy_tracker=None) -> BuildHealth:
        return self.health_evaluator.evaluate(
            self.inputs(state, strategy_tracker=strategy_tracker)
        )


def projected_state_with_jokers(state, jokers: Iterable[object]):
    """Copy a state and replace only its Joker roster for side-effect-free probes."""
    copier = getattr(state, "copy", None)
    projected = copier() if callable(copier) else deepcopy(state)
    projected.jokers = list(jokers)
    return projected
