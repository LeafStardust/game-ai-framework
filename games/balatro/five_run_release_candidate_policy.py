from __future__ import annotations

"""Current-HEAD calibrations derived from repeated five-run Red/White batches."""

from dataclasses import replace

from games.balatro.actions import END_SHOP, REFRESH_SHOP, BalatroAction
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


def _shop_signature(state) -> tuple[int, int]:
    return (
        max(1, int(getattr(state, "ante", 1) or 1)),
        max(0, int(getattr(state, "round_num", 0) or 0)),
    )


def install_five_run_release_candidate_policy() -> None:
    if getattr(BuildAwareShopArbiter, "_release_candidate_policy_installed", False):
        return

    original_booster_recommend = BuildAwareShopBoosterPolicy.recommend

    def booster_recommend(self, state, action):
        result = original_booster_recommend(self, state, action)
        if not result.should_buy:
            return result
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        pressure = roster_upgrade_pressure(state)
        if ante < 4 or pressure < 2.0:
            return result

        price = self._price(action.target)
        money_after = max(0, int(getattr(state, "money", 0) or 0)) - price
        # Once a full board is visibly weak, keep enough liquid cash to reroll and
        # buy a real Joker upgrade. Repeated speculative packs must not repeatedly
        # drain the run to $0-$4 while every Joker slot is occupied by filler.
        reserve = 10
        if money_after >= reserve:
            return result
        return replace(
            result,
            decision=HOLD,
            total=float(self.parent_hold_baseline),
            rationale=(
                *result.rationale,
                "release-candidate calibration: weak full roster reserves cash for Joker search instead of another speculative booster",
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
        # A four-of-five midgame board is not 'done'. If the ordinary arbiter found
        # nothing worth buying, one affordable search roll is preferable to carrying
        # a vacant scoring slot into the next blind while cash sits unused.
        open_slot_search = (
            ante >= 4
            and slots >= 5
            and len(jokers) >= 4
            and len(jokers) < slots
        )
        if ante < 4 or not (full_roster or open_slot_search):
            return result

        cost = int(reroll_cost)
        if cost <= 0 or cost > 8:
            return result

        pressure = (
            roster_upgrade_pressure(state)
            if full_roster
            else sum(_joker_upgrade_weakness(joker) for joker in jokers)
        )
        money = max(0, int(getattr(state, "money", 0) or 0))
        remaining = money - cost
        high_cash_search = full_roster and ante >= 5 and remaining >= 30
        pressure_search = (
            full_roster
            and pressure >= 1.5
            and remaining >= _reroll_reserve_floor(pressure)
        )
        vacant_slot_search = open_slot_search and remaining >= 20
        if not (high_cash_search or pressure_search or vacant_slot_search):
            return result

        signature = _shop_signature(state)
        if getattr(self, "_release_candidate_reroll_signature", None) == signature:
            return result
        self._release_candidate_reroll_signature = signature

        return replace(
            result,
            action=BalatroAction(REFRESH_SHOP),
            source="RELEASE_CANDIDATE_ROSTER_REROLL",
            normalized_gain=max(0.001, float(result.normalized_gain)),
            rationale=(
                "release-candidate calibration: roster has enough cash to search once for a Joker upgrade before leaving shop",
                f"ante={ante}; joker slots={len(jokers)}/{slots}; roster upgrade pressure={pressure:.2f}; reroll=${cost}; cash after reroll=${remaining}",
                "full weak boards and four-of-five midgame boards may each spend one bounded search roll while preserving reserve",
                *result.rationale,
            ),
        )

    BuildAwareShopArbiter.decide = shop_decide
    BuildAwareShopArbiter._release_candidate_policy_installed = True
