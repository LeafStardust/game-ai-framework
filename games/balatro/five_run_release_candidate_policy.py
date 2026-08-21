from __future__ import annotations

"""Current-HEAD calibrations derived from repeated five-run Red/White batches."""

from dataclasses import replace

from games.balatro.actions import END_SHOP, REFRESH_SHOP, BalatroAction
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_booster_policy import (
    HOLD,
    BuildAwareShopBoosterPolicy,
)


_STATIC_WEAKNESS = {
    # Generic/static filler. Useful for surviving early antes, but a full mid/late
    # board made mostly from these should keep searching for an actual engine.
    "abstractjoker": 1.00,
    "jollyjoker": 0.65,
    "slyjoker": 0.75,
    "lustyjoker": 0.60,
    "craftyjoker": 0.60,
    "zanyjoker": 0.75,
    "madjoker": 0.50,
    "oddtoddjoker": 0.60,
    "bluejoker": 0.60,
    "creditcardjoker": 0.75,
    "goldenjoker": 1.00,
    "bannerjoker": 1.00,
    "todolistjoker": 1.00,
    "jokerstencil": 1.00,
    "jokerstenciljoker": 1.00,
    "raisedfist": 0.50,
    "raisedfistjoker": 0.50,
    # These are legitimate support pieces, but without the defining engine they
    # should not make a full board look finished.
    "evenstevenjoker": 0.45,
    "fibonaccijoker": 0.35,
}

# White-stake Small Blind requirements. SHOP snapshots can legitimately have no
# active Blind object, which used to make Build Health return a neutral 50/50
# survival score exactly when the shop needed to decide whether to keep searching.
# The floor is deliberately the least demanding next selectable blind; D1 remains
# authoritative once the actual blind begins.
_WHITE_SMALL_BLIND_FLOORS = {
    1: 300,
    2: 800,
    3: 2_000,
    4: 5_000,
    5: 11_000,
    6: 20_000,
    7: 35_000,
    8: 50_000,
}

_RELEASE_HEALTH = RuntimeBuildHealthEvaluator()


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    return _normalize(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )


def _public_number(joker: object, key: str, default: float = 0.0) -> float:
    public = getattr(joker, "public_state", None)
    if isinstance(public, dict):
        value = public.get(key, default)
    else:
        value = getattr(public, key, default) if public is not None else default
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _full_roster(state) -> bool:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    return slots > 0 and len(jokers) >= slots


def _joker_upgrade_weakness(joker: object) -> float:
    token = _joker_token(joker)
    if token in {"popcornjoker"}:
        mult = _public_number(joker, "mult", 0.0)
        return 0.90 if mult <= 10.0 else 0.45 if mult <= 20.0 else 0.20
    if token in {"icecreamjoker"}:
        chips = max(
            _public_number(joker, "chips", 0.0),
            _public_number(joker, "chip_mod", 0.0),
        )
        return 1.00 if chips <= 30.0 else 0.50 if chips <= 60.0 else 0.20
    if token in {"ramenjoker"}:
        x_mult = _public_number(joker, "x_mult", 0.0)
        return 0.80 if x_mult < 1.50 else 0.35 if x_mult < 1.80 else 0.0
    if token in {"redcardjoker"}:
        mult = _public_number(joker, "mult", 0.0)
        return 1.00 if mult <= 0.0 else 0.50 if mult < 10.0 else 0.0
    if token in {"greenjoker"}:
        mult = _public_number(joker, "mult", 0.0)
        return 0.75 if mult < 8.0 else 0.35 if mult < 16.0 else 0.0
    return float(_STATIC_WEAKNESS.get(token, 0.0))


def roster_upgrade_pressure(state) -> float:
    """Public-state pressure to replace filler in a completely occupied board."""
    if not _full_roster(state):
        return 0.0
    return sum(_joker_upgrade_weakness(joker) for joker in getattr(state, "jokers", ()) or ())


def _reroll_reserve_floor(pressure: float) -> int:
    # A clearly weak board may spend deeper because preserving a bad five-Joker
    # roster is itself a survival risk. Milder boards retain the established $20.
    return 15 if pressure >= 3.0 else 20


def shop_next_blind_floor(state) -> float:
    """Conservative public next-blind target for Red/White SHOP diagnostics."""
    if str(getattr(state, "phase", "")).upper() != "SHOP":
        return 0.0
    stake = _normalize(getattr(state, "stake_name", "WHITE") or "WHITE")
    if stake not in {"", "white"}:
        return 0.0
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    if ante in _WHITE_SMALL_BLIND_FLOORS:
        return float(_WHITE_SMALL_BLIND_FLOORS[ante])
    # Endless is not the calibration target. Extrapolate only enough to avoid
    # silently reverting to a neutral 50/50 diagnostic if the run is continued.
    return float(_WHITE_SMALL_BLIND_FLOORS[8] * (1.6 ** max(0, ante - 8)))


def _release_candidate_reroll_limit(*, pressure: float, survival: float) -> int:
    """Bounded search depth for a weak roster in one shop checkpoint."""
    return 2 if pressure >= 3.0 or survival < 65.0 else 1


def _shop_signature(state) -> tuple[int, int]:
    return (
        max(1, int(getattr(state, "ante", 1) or 1)),
        max(0, int(getattr(state, "round_num", 0) or 0)),
    )


def _install_shop_survival_floor() -> None:
    if getattr(RuntimeBuildHealthEvaluator, "_release_candidate_shop_survival_installed", False):
        return

    original = RuntimeBuildHealthEvaluator._survival_and_immediate

    def survival_and_immediate(self, state):
        survival, immediate = original(self, state)
        if str(getattr(state, "phase", "")).upper() != "SHOP":
            return survival, immediate
        # A real observed target remains authoritative. Only repair the no-target
        # SHOP case that previously collapsed to the evaluator's neutral 50/50.
        observed_target = 0.0
        for value in (
            getattr(state, "blind_score", 0),
            getattr(state, "blind_requirement", 0),
        ):
            try:
                observed_target = max(observed_target, float(value or 0))
            except (TypeError, ValueError):
                pass
        if observed_target > 0:
            return survival, immediate

        target = shop_next_blind_floor(state)
        if target <= 0:
            return survival, immediate
        hands = 4
        best = max(0.0, float(self._representative_best_score(state)))
        pace = target / hands
        immediate = min(1.0, best / max(pace, 1.0))
        survival = min(1.0, (best * hands) / target)
        return survival, immediate

    RuntimeBuildHealthEvaluator._survival_and_immediate = survival_and_immediate
    RuntimeBuildHealthEvaluator._release_candidate_shop_survival_installed = True


def install_five_run_release_candidate_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_release_candidate_policy_installed", False):
        return

    _install_shop_survival_floor()

    original_booster_recommend = BuildAwareShopBoosterPolicy.recommend

    def booster_recommend(self, state, action):
        result = original_booster_recommend(self, state, action)
        if not result.should_buy:
            return result
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        pressure = roster_upgrade_pressure(state)
        if ante < 3 or pressure < 1.5:
            return result

        health = _RELEASE_HEALTH.evaluate(state)
        family = str(getattr(result, "family", "") or "").upper()
        hit_probability = float(getattr(result, "at_least_one_hit_probability", 0.0) or 0.0)
        weak_now = health.survival < 75.0 or bool(health.scaling_deficit)
        speculative_family = family in {"STANDARD", "ARCANA", "CELESTIAL"}

        # When the scoring board is already weak, direct Joker search outranks a
        # speculative non-Joker pack unless that pack has an unusually concrete
        # modeled hit. Buffoon and Spectral remain eligible because they can supply
        # a direct engine or a run-changing transition.
        if weak_now and speculative_family and hit_probability < 0.80:
            return replace(
                result,
                decision=HOLD,
                total=float(self.parent_hold_baseline),
                rationale=(
                    *result.rationale,
                    "five-log calibration: weak realized scoring prioritizes direct Joker search over a speculative booster",
                    f"Build Health survival={health.survival:.1f}; scaling_deficit={health.scaling_deficit}; family={family}; modeled hit={hit_probability:.3f}",
                ),
            )

        price = self._price(action.target)
        money_after = max(0, int(getattr(state, "money", 0) or 0)) - price
        # Preserve enough liquid cash for at least a reroll plus a plausible Joker
        # purchase. The previous $10 floor was too low in repeated 0/5 calibration.
        reserve = 20 if weak_now else 15
        if money_after >= reserve:
            return result
        return replace(
            result,
            decision=HOLD,
            total=float(self.parent_hold_baseline),
            rationale=(
                *result.rationale,
                "five-log calibration: weak full roster reserves cash for Joker search instead of another speculative booster",
                f"roster upgrade pressure={pressure:.2f}; post-pack cash=${money_after}; required upgrade reserve=${reserve}",
            ),
        )

    BuildAwareShopBoosterPolicy.recommend = booster_recommend

    original_shop_decide = BuildAwareShopArbiter.decide

    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        result = original_shop_decide(
            self,
            state,
            visible_actions,
            reroll_cost=reroll_cost,
        )
        if result.action.name != END_SHOP or reroll_cost is None:
            return result

        ante = max(1, int(getattr(state, "ante", 1) or 1))
        jokers = tuple(getattr(state, "jokers", ()) or ())
        slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
        full_roster = slots > 0 and len(jokers) >= slots
        # A four-of-five formation/commitment board is not "done". The previous
        # Ante-4 gate allowed an Ante-3 weak board to carry an empty scoring slot.
        open_slot_search = (
            ante >= 3
            and slots >= 5
            and len(jokers) >= 4
            and len(jokers) < slots
        )
        if ante < 3 or not (full_roster or open_slot_search):
            return result

        cost = int(reroll_cost)
        if cost <= 0 or cost > 8:
            return result

        pressure = (
            roster_upgrade_pressure(state)
            if full_roster
            else sum(_joker_upgrade_weakness(joker) for joker in jokers)
        )
        health = _RELEASE_HEALTH.evaluate(state)
        money = max(0, int(getattr(state, "money", 0) or 0))
        remaining = money - cost
        high_cash_search = full_roster and ante >= 4 and remaining >= 25
        pressure_search = (
            full_roster
            and pressure >= 1.25
            and remaining >= _reroll_reserve_floor(pressure)
        )
        vacant_slot_search = open_slot_search and remaining >= 15
        health_search = (
            (health.survival < 75.0 or bool(health.scaling_deficit))
            and remaining >= 15
        )
        if not (high_cash_search or pressure_search or vacant_slot_search or health_search):
            return result

        signature = _shop_signature(state)
        stored_signature = getattr(self, "_release_candidate_reroll_signature", None)
        if stored_signature != signature:
            self._release_candidate_reroll_signature = signature
            self._release_candidate_reroll_count = 0
        used = max(0, int(getattr(self, "_release_candidate_reroll_count", 0) or 0))
        limit = _release_candidate_reroll_limit(
            pressure=pressure,
            survival=health.survival,
        )
        if used >= limit:
            return result
        self._release_candidate_reroll_count = used + 1

        return replace(
            result,
            action=BalatroAction(REFRESH_SHOP),
            source="RELEASE_CANDIDATE_ROSTER_REROLL",
            normalized_gain=max(0.001, float(result.normalized_gain)),
            rationale=(
                "five-log calibration: weak or incomplete roster has enough cash to keep searching for a Joker upgrade before leaving shop",
                f"ante={ante}; joker slots={len(jokers)}/{slots}; roster upgrade pressure={pressure:.2f}; Build Health survival={health.survival:.1f}; scaling_deficit={health.scaling_deficit}",
                f"reroll=${cost}; cash after reroll=${remaining}; bounded search roll {used + 1}/{limit}",
                *result.rationale,
            ),
        )

    BuildAwareShopArbiter.decide = shop_decide
    BuildAwareShopArbiter._release_candidate_policy_installed = True
