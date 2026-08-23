from __future__ import annotations

"""Current-HEAD calibrations derived from repeated five-run Red/White batches."""

from dataclasses import replace

from games.balatro.actions import BUY_BOOSTER, BUY_CONSUMABLE, BUY_JOKER, BUY_VOUCHER, END_SHOP, REFRESH_SHOP, BalatroAction
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_booster_policy import HOLD, BuildAwareShopBoosterPolicy


_STATIC_WEAKNESS = {
    "abstractjoker": 1.00, "jollyjoker": 0.65, "slyjoker": 0.75,
    "lustyjoker": 0.60, "craftyjoker": 0.60, "zanyjoker": 0.75,
    "madjoker": 0.50, "oddtoddjoker": 0.60, "bluejoker": 0.60,
    "creditcardjoker": 0.75, "goldenjoker": 1.00, "bannerjoker": 1.00,
    "todolistjoker": 1.00, "jokerstencil": 1.00, "jokerstenciljoker": 1.00,
    "raisedfist": 0.50, "raisedfistjoker": 0.50,
    "evenstevenjoker": 0.45, "fibonaccijoker": 0.35,
}

_WHITE_SMALL_BLIND_FLOORS = {1: 300, 2: 800, 3: 2_000, 4: 5_000, 5: 11_000, 6: 20_000, 7: 35_000, 8: 50_000}
_RELEASE_HEALTH = RuntimeBuildHealthEvaluator()


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_token(joker: object) -> str:
    return _normalize(getattr(joker, "name", None) or getattr(joker, "label", None) or getattr(joker, "ability_name", None) or type(joker).__name__)


def _public_number(joker: object, key: str, default: float = 0.0) -> float:
    public = getattr(joker, "public_state", None)
    value = public.get(key, default) if isinstance(public, dict) else getattr(public, key, default) if public is not None else default
    try: return float(value)
    except (TypeError, ValueError): return float(default)


def _full_roster(state) -> bool:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    return slots > 0 and len(jokers) >= slots


def _critical_roster_gap(state) -> bool:
    """Formation-stage board is too thin to spend scarce cash on side development."""
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    count = len(getattr(state, "jokers", ()) or ())
    return ante >= 2 and slots >= 3 and count < min(3, slots)


def _joker_upgrade_weakness(joker: object) -> float:
    token = _joker_token(joker)
    if token == "popcornjoker":
        mult = _public_number(joker, "mult", 0.0); return 0.90 if mult <= 10 else 0.45 if mult <= 20 else 0.20
    if token == "icecreamjoker":
        chips = max(_public_number(joker, "chips", 0.0), _public_number(joker, "chip_mod", 0.0)); return 1.00 if chips <= 30 else 0.50 if chips <= 60 else 0.20
    if token == "ramenjoker":
        x = _public_number(joker, "x_mult", 0.0); return 0.80 if x < 1.50 else 0.35 if x < 1.80 else 0.0
    if token == "redcardjoker":
        m = _public_number(joker, "mult", 0.0); return 1.00 if m <= 0 else 0.50 if m < 10 else 0.0
    if token == "greenjoker":
        m = _public_number(joker, "mult", 0.0); return 0.75 if m < 8 else 0.35 if m < 16 else 0.0
    return float(_STATIC_WEAKNESS.get(token, 0.0))


def roster_upgrade_pressure(state) -> float:
    if not _full_roster(state): return 0.0
    return sum(_joker_upgrade_weakness(joker) for joker in getattr(state, "jokers", ()) or ())


def _reroll_reserve_floor(pressure: float) -> int:
    return 15 if pressure >= 3.0 else 20


def shop_next_blind_floor(state) -> float:
    if str(getattr(state, "phase", "")).upper() != "SHOP": return 0.0
    if _normalize(getattr(state, "stake_name", "WHITE") or "WHITE") not in {"", "white"}: return 0.0
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    if ante in _WHITE_SMALL_BLIND_FLOORS: return float(_WHITE_SMALL_BLIND_FLOORS[ante])
    return float(_WHITE_SMALL_BLIND_FLOORS[8] * (1.6 ** max(0, ante - 8)))


def _release_candidate_reroll_limit(*, pressure: float, survival: float) -> int:
    return 2 if pressure >= 3.0 or survival < 65.0 else 1


def _shop_signature(state) -> tuple[int, int]:
    return (max(1, int(getattr(state, "ante", 1) or 1)), max(0, int(getattr(state, "round_num", 0) or 0)))


def _install_shop_survival_floor() -> None:
    if getattr(RuntimeBuildHealthEvaluator, "_release_candidate_shop_survival_installed", False): return
    original = RuntimeBuildHealthEvaluator._survival_and_immediate
    def survival_and_immediate(self, state):
        survival, immediate = original(self, state)
        if str(getattr(state, "phase", "")).upper() != "SHOP": return survival, immediate
        observed_target = 0.0
        for value in (getattr(state, "blind_score", 0), getattr(state, "blind_requirement", 0)):
            try: observed_target = max(observed_target, float(value or 0))
            except (TypeError, ValueError): pass
        if observed_target > 0: return survival, immediate
        target = shop_next_blind_floor(state)
        if target <= 0: return survival, immediate
        best = max(0.0, float(self._representative_best_score(state)))
        pace = target / 4
        return min(1.0, (best * 4) / target), min(1.0, best / max(pace, 1.0))
    RuntimeBuildHealthEvaluator._survival_and_immediate = survival_and_immediate
    RuntimeBuildHealthEvaluator._release_candidate_shop_survival_installed = True


def install_five_run_release_candidate_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_release_candidate_policy_installed", False): return
    _install_shop_survival_floor()

    original_booster_recommend = BuildAwareShopBoosterPolicy.recommend
    def booster_recommend(self, state, action):
        result = original_booster_recommend(self, state, action)
        if not result.should_buy: return result
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        family = str(getattr(result, "family", "") or "").upper()
        # 2026-08-23 0/5 batch: one run reached Ante 3 with zero Jokers after
        # repeatedly funding Celestial development. Buffoon remains eligible because
        # it is itself a direct Joker-acquisition route; side-development packs do not.
        if _critical_roster_gap(state) and family != "BUFFOON":
            return replace(result, decision=HOLD, total=float(self.parent_hold_baseline), rationale=(
                *result.rationale,
                "2026-08-23 formation guard: fewer than three Jokers by Ante 2+; direct Joker acquisition/search outranks side-development packs",
                f"current Joker roster={len(getattr(state, 'jokers', ()) or ())}/{int(getattr(state, 'joker_slots', 0) or 0)}; booster family={family}",
            ))
        pressure = roster_upgrade_pressure(state)
        if ante < 3 or pressure < 1.5: return result
        health = _RELEASE_HEALTH.evaluate(state)
        hit = float(getattr(result, "at_least_one_hit_probability", 0.0) or 0.0)
        weak_now = health.survival < 75.0 or bool(health.scaling_deficit)
        if weak_now and family in {"STANDARD", "ARCANA", "CELESTIAL"} and hit < 0.80:
            return replace(result, decision=HOLD, total=float(self.parent_hold_baseline), rationale=(
                *result.rationale, "five-log calibration: weak realized scoring prioritizes direct Joker search over a speculative booster",
                f"Build Health survival={health.survival:.1f}; scaling_deficit={health.scaling_deficit}; family={family}; modeled hit={hit:.3f}"))
        price = self._price(action.target); money_after = max(0, int(getattr(state, "money", 0) or 0)) - price
        reserve = 20 if weak_now else 15
        if money_after >= reserve: return result
        return replace(result, decision=HOLD, total=float(self.parent_hold_baseline), rationale=(
            *result.rationale, "five-log calibration: weak full roster reserves cash for Joker search instead of another speculative booster",
            f"roster upgrade pressure={pressure:.2f}; post-pack cash=${money_after}; required upgrade reserve=${reserve}"))
    BuildAwareShopBoosterPolicy.recommend = booster_recommend

    original_shop_decide = BuildAwareShopArbiter.decide
    def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
        critical_gap = _critical_roster_gap(state)
        filtered = list(visible_actions)
        if critical_gap:
            money = max(0, int(getattr(state, "money", 0) or 0))
            # Do not let vouchers/loose consumables consume formation cash while the
            # board has fewer than three Jokers. An unusually rich board may still
            # buy them while retaining a $20 direct-search reserve.
            filtered = [a for a in filtered if a.name not in {BUY_VOUCHER, BUY_CONSUMABLE} or money - int(getattr(a.target, "price", getattr(a.target, "cost", 0)) or 0) >= 20]
        result = original_shop_decide(self, state, filtered, reroll_cost=reroll_cost)
        if result.action.name != END_SHOP or reroll_cost is None: return result

        ante = max(1, int(getattr(state, "ante", 1) or 1)); jokers = tuple(getattr(state, "jokers", ()) or ())
        slots = max(0, int(getattr(state, "joker_slots", 0) or 0)); full_roster = slots > 0 and len(jokers) >= slots
        open_slot_search = ante >= 3 and slots >= 5 and len(jokers) >= 4 and len(jokers) < slots
        critical_gap = _critical_roster_gap(state)
        if ante < 2 or not (full_roster or open_slot_search or critical_gap): return result
        cost = int(reroll_cost)
        if cost <= 0 or cost > 8: return result
        pressure = roster_upgrade_pressure(state) if full_roster else sum(_joker_upgrade_weakness(j) for j in jokers)
        health = _RELEASE_HEALTH.evaluate(state); money = max(0, int(getattr(state, "money", 0) or 0)); remaining = money - cost
        high_cash_search = full_roster and ante >= 4 and remaining >= 25
        pressure_search = full_roster and pressure >= 1.25 and remaining >= _reroll_reserve_floor(pressure)
        vacant_slot_search = open_slot_search and remaining >= 15
        health_search = (health.survival < 75.0 or bool(health.scaling_deficit)) and remaining >= 15
        # Formation emergency can search more aggressively because leaving Ante 2+
        # with 0-2 Jokers repeatedly proved more dangerous than preserving interest.
        formation_search = critical_gap and remaining >= 8
        if not (high_cash_search or pressure_search or vacant_slot_search or health_search or formation_search): return result
        signature = _shop_signature(state)
        if getattr(self, "_release_candidate_reroll_signature", None) != signature:
            self._release_candidate_reroll_signature = signature; self._release_candidate_reroll_count = 0
        used = max(0, int(getattr(self, "_release_candidate_reroll_count", 0) or 0))
        limit = 2 if critical_gap else _release_candidate_reroll_limit(pressure=pressure, survival=health.survival)
        if used >= limit: return result
        self._release_candidate_reroll_count = used + 1
        return replace(result, action=BalatroAction(REFRESH_SHOP), source="RELEASE_CANDIDATE_ROSTER_REROLL", normalized_gain=max(0.001, float(result.normalized_gain)), rationale=(
            "2026-08-23 calibration: weak or incomplete roster has enough cash to keep searching for a Joker upgrade before leaving shop",
            f"ante={ante}; joker slots={len(jokers)}/{slots}; critical formation gap={critical_gap}; roster pressure={pressure:.2f}; survival={health.survival:.1f}; scaling_deficit={health.scaling_deficit}",
            f"reroll=${cost}; cash after reroll=${remaining}; bounded search roll {used + 1}/{limit}", *result.rationale))
    BuildAwareShopArbiter.decide = shop_decide
    BuildAwareShopArbiter._release_candidate_policy_installed = True
