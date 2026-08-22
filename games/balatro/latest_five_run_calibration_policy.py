from __future__ import annotations

"""Targeted corrections from repeated Red/White five-run calibration batches.

This module remains intentionally public-state-only.  The 2026-08-22 batch added
three important lessons on top of the earlier pack/Mouth corrections:

* generator-only deck growth is not a realized scoring engine;
* a small Green Joker value must not make a failing board look 85% scaled;
* full boards made from several static conditional Common Jokers must keep upgrade
  pressure instead of being mistaken for a finished build.
"""

from dataclasses import replace

from games.balatro.actions import BUY_JOKER, BUY_VOUCHER, DISCARD_CARDS, PLAY_CARDS, SKIP_BOOSTER
from games.balatro.build_health import EngineState, RealizedEngineStrength
from games.balatro.build_health_runtime import RealizedEngineAnalyzer
from games.balatro import five_run_release_candidate_policy as release_candidate
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.mouth_hand_policy import _hand_type, _replace_with_play
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.shop_arbiter import BuildAwareShopArbiter


_NO_DISCARD_SUPPORT = frozenset(
    {
        "delayedgratificationjoker",
        "burglarjoker",
        "ramenjoker",
        "greenjoker",
    }
)

# Static/conditional pieces observed occupying essentially an entire board in the
# 2026-08-22 losses.  They can be useful early, but none should suppress search for
# an actual scaling or multiplicative engine on a full formation-stage roster.
_20260822_STATIC_WEAKNESS = {
    "drolljoker": 0.70,
    "wilyjoker": 0.65,
    "mysticsummitjoker": 0.75,
    "cloud9joker": 0.80,
    "swashbucklerjoker": 0.50,
    "smileyfacejoker": 0.45,
}


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _label(item: object) -> str:
    return str(
        getattr(item, "label", None)
        or getattr(item, "name", None)
        or getattr(item, "ability_name", None)
        or getattr(item, "center", None)
        or type(item).__name__
    )


def _joker_token(joker: object) -> str:
    token = _normalize(_label(joker))
    return token if token.endswith("joker") else token + "joker"


def _owned_tokens(state) -> frozenset[str]:
    return frozenset(_joker_token(joker) for joker in getattr(state, "jokers", ()) or ())


def sock_scary_face_synergy(state, label: str) -> bool:
    """Return whether a visible face scorer directly feeds owned Sock retriggers."""
    if _normalize(label) not in {"scaryface", "smileyface"}:
        return False
    return "sockandbuskinjoker" in _owned_tokens(state)


def stencil_would_be_dead(state, candidate: object) -> bool:
    """True when acquiring this ordinary Stencil can produce only x1 Mult."""
    if _joker_token(candidate) != "jokerstenciljoker":
        return False
    if _normalize(getattr(candidate, "edition", "")) == "negative":
        return False
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    if slots <= 0:
        return False
    non_stencil = sum(
        _joker_token(joker) != "jokerstenciljoker"
        for joker in getattr(state, "jokers", ()) or ()
    )
    return non_stencil >= slots - 1


def hieroglyph_blocked(state, candidate: object) -> bool:
    """Block mid/late Hieroglyph on the Red/White calibration target."""
    if _normalize(_label(candidate)) != "hieroglyph":
        return False
    deck = _normalize(getattr(state, "deck_name", "RED") or "RED")
    stake = _normalize(getattr(state, "stake_name", "WHITE") or "WHITE")
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    return deck in {"", "red"} and stake in {"", "white"} and ante >= 3


def _pack_choice_label(result: PackActionScore) -> str:
    target = getattr(result.action, "target", None)
    return str(getattr(target, "label", "") or "")


def _pack_choice_edition(result: PackActionScore) -> str:
    target = getattr(result.action, "target", None)
    data = getattr(target, "data", {}) or {}
    return str(data.get("edition") or "")


def _stencil_pack_dead(state, result: PackActionScore) -> bool:
    if _normalize(_pack_choice_label(result)) != "jokerstencil":
        return False
    if _normalize(_pack_choice_edition(result)) == "negative":
        return False
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    non_stencil = sum(
        _joker_token(joker) != "jokerstenciljoker"
        for joker in getattr(state, "jokers", ()) or ()
    )
    return slots > 0 and non_stencil >= slots - 1


def _banner_pack_replacement_is_speculative(state, result: PackActionScore) -> bool:
    if _normalize(_pack_choice_label(result)) != "banner":
        return False
    if _normalize(_pack_choice_edition(result)) == "negative":
        return False
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    jokers = tuple(getattr(state, "jokers", ()) or ())
    if ante < 3 or slots <= 0 or len(jokers) < slots:
        return False
    return not bool(_owned_tokens(state) & _NO_DISCARD_SUPPORT)


def _enforce_latest_pack_calibration(state, ranked):
    ranked = list(ranked)
    if not ranked:
        return ranked

    skip_total = max(
        (float(item.total) for item in ranked if item.action.name == SKIP_BOOSTER),
        default=0.35,
    )
    rewritten: list[PackActionScore] = []
    for item in ranked:
        label = _pack_choice_label(item)
        if _stencil_pack_dead(state, item):
            rewritten.append(
                replace(
                    item,
                    total=-1.0,
                    notes=(
                        *item.notes,
                        "latest five-run calibration: ordinary Joker Stencil would be x1 after acquisition, so it is not a scoring upgrade",
                    ),
                )
            )
            continue
        if _banner_pack_replacement_is_speculative(state, item):
            rewritten.append(
                replace(
                    item,
                    total=-1.0,
                    notes=(
                        *item.notes,
                        "latest five-run calibration: ordinary Banner cannot replace a full formation-stage roster without realized no-discard support",
                    ),
                )
            )
            continue
        if sock_scary_face_synergy(state, label):
            floor = skip_total + 1.25
            rewritten.append(
                replace(
                    item,
                    total=max(float(item.total), floor),
                    notes=(
                        *item.notes,
                        "latest five-run calibration: owned Sock and Buskin retriggers every scored face card, so visible face-scoring support is an immediate engine upgrade",
                    ),
                )
            )
            continue
        rewritten.append(item)

    return sorted(
        rewritten,
        key=lambda item: (float(item.total), item.action.name != SKIP_BOOSTER),
        reverse=True,
    )


def _matching_mouth_plays(policy, state, plans):
    locked = str(getattr(state, "boss_blind_only_hand", "") or "").upper()
    if not locked:
        return ()
    return tuple(
        plan
        for plan in plans
        if plan.action.name == PLAY_CARDS and _hand_type(policy, plan) == locked
    )


def _recalibrate_realized_engines(state, engines):
    """Correct two optimistic Build Health diagnoses exposed by live telemetry."""

    ante = max(1, int(getattr(state, "ante", 1) or 1))
    jokers = tuple(getattr(state, "jokers", ()) or ())
    tokens = {_joker_token(joker) for joker in jokers}
    rewritten: list[RealizedEngineStrength] = []

    for engine in engines:
        if engine.engine_id != "green_joker":
            rewritten.append(engine)
            continue

        # +7 Mult at Ante 4 was previously classified ACTIVATED_HEALTHY and gave
        # Scaling=85 despite the run dying at 5,134/7,500.  A linear +1/hand
        # scaler needs materially more realized Mult by formation/commitment.
        target_mult = max(8.0, float(ante * 4))
        strength = max(0.0, float(engine.current_strength))
        ratio = strength / target_mult
        if ratio <= 0.0:
            state_name = EngineState.OWNED_INACTIVE
        elif ratio < 0.50:
            state_name = EngineState.ACTIVATED_WEAK
        elif ratio < 1.50:
            state_name = EngineState.ACTIVATED_HEALTHY
        else:
            state_name = EngineState.MATURE
        runway = 0.50 if state_name == EngineState.ACTIVATED_WEAK else engine.runway_need
        rewritten.append(
            replace(
                engine,
                state=state_name,
                growth_rate=0.75,
                runway_need=runway,
                rationale=(
                    *engine.rationale,
                    f"2026-08-22 calibration target=+{target_mult:.0f} Mult by Ante {ante}; linear Green growth cannot stand in for a multiplicative engine",
                ),
            )
        )

    generator_owned = bool(tokens & {"marblejoker", "certificatejoker"})
    generator_payoff = bool(
        tokens
        & {
            "hologramjoker",
            "bluejoker",
            "stonejoker",
        }
    )
    if generator_owned and not generator_payoff:
        rewritten.append(
            RealizedEngineStrength(
                engine_id="orphan_deck_growth",
                state=EngineState.OWNED_INACTIVE,
                current_strength=0.0,
                growth_rate=0.0,
                runway_need=0.75,
                rationale=(
                    "Marble/Certificate is generating cards without Hologram, Blue Joker, or Stone Joker payoff",
                    "deck growth alone is not realized scoring strength and should not suppress shop upgrade pressure",
                ),
            )
        )

    return tuple(rewritten)


def _install_20260822_strength_calibration() -> None:
    release_candidate._STATIC_WEAKNESS.update(_20260822_STATIC_WEAKNESS)
    if getattr(RealizedEngineAnalyzer, "_five_run_20260822_installed", False):
        return
    original_analyze = RealizedEngineAnalyzer.analyze

    def analyze(self, state):
        return _recalibrate_realized_engines(state, original_analyze(self, state))

    RealizedEngineAnalyzer.analyze = analyze
    RealizedEngineAnalyzer._five_run_20260822_installed = True


def install_latest_five_run_calibration_policy() -> None:
    _install_20260822_strength_calibration()
    if getattr(BalatroPackPolicy, "_latest_five_run_calibration_installed", False):
        return

    original_rank_actions = BalatroPackPolicy.rank_actions

    def rank_actions(self, state, actions):
        return _enforce_latest_pack_calibration(
            state,
            original_rank_actions(self, state, actions),
        )

    BalatroPackPolicy.rank_actions = rank_actions

    original_shop_decide = BuildAwareShopArbiter.decide

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        filtered = []
        for action in visible_actions:
            if action.name == BUY_JOKER and stencil_would_be_dead(state, action.target):
                continue
            if action.name == BUY_VOUCHER and hieroglyph_blocked(state, action.target):
                continue
            filtered.append(action)
        return original_shop_decide(
            self,
            state,
            filtered,
            reroll_cost=reroll_cost,
        )

    BuildAwareShopArbiter.decide = shop_decide

    original_hand_decide = StrategyAwareLiveHandActionPolicy.decide

    def hand_decide(self, state, plans, **kwargs):
        decision = original_hand_decide(self, state, plans, **kwargs)
        if str(getattr(state, "boss_name", "") or "") != "The Mouth":
            return decision
        locked = str(getattr(state, "boss_blind_only_hand", "") or "").upper()
        if not locked:
            return decision
        selected = getattr(decision, "selected_plan", None)
        if (
            decision.action.name == PLAY_CARDS
            and selected is not None
            and _hand_type(self, selected) == locked
        ):
            return decision

        matching = _matching_mouth_plays(self, state, plans)
        if matching:
            plan = max(
                matching,
                key=lambda candidate: (
                    float(self.evaluator.project_play(state, candidate.action).expected_hand_score),
                    self._strategy_fit(state, candidate.action)[0],
                    self._within_type_key(candidate),
                ),
            )
            return _replace_with_play(
                self,
                state,
                decision,
                plan,
                rationale=(
                    f"The Mouth is already locked to {locked}; reject a different poker-hand type that would score zero",
                    "use the highest projected currently playable locked hand instead",
                ),
            )

        if int(getattr(state, "discards_remaining", 0) or 0) > 0:
            discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
            if discards:
                plan = max(
                    discards,
                    key=lambda candidate: (
                        float(self.evaluator.evaluate(state, candidate.action)),
                        self._within_type_key(candidate),
                    ),
                )
                value = float(self.evaluator.evaluate(state, plan.action))
                return replace(
                    decision,
                    mode=PACE_RECOVERY,
                    action=plan.action,
                    selected_plan=plan,
                    selected_immediate_score=None,
                    selected_pace_ratio=None,
                    selected_fallback_value=value,
                    rationale=(
                        f"The Mouth is locked to {locked} and no locked hand is currently playable",
                        "discard rather than spend a hand on a boss-invalid zero-score hand",
                        *decision.rationale,
                    ),
                )
        return decision

    StrategyAwareLiveHandActionPolicy.decide = hand_decide

    BalatroPackPolicy._latest_five_run_calibration_installed = True
    BuildAwareShopArbiter._latest_five_run_calibration_installed = True
    StrategyAwareLiveHandActionPolicy._latest_five_run_calibration_installed = True
