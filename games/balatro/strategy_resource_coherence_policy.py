from __future__ import annotations

"""Resource-policy coherence for the canonical Bond strategy machine.

Live validation exposed two forms of resource drift:

* D8 treated requirements from every owned effect as one giant build wishlist,
  making Standard Packs appear to satisfy nearly every rank simultaneously.
* D3 could buy a zero-compatibility Voucher through the basic cash reserve because
  the Red/White cartridge intentionally allowed ``minimum_money_after=0``.

This layer keeps child-policy authority intact while making their build evidence come
from the strongest currently committed semantic strategy when one exists.
"""

from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.shop_voucher_policy import BUY, HOLD, VoucherAcquisitionPolicy


_BASIC_CASH_RESERVE = 5


def _strategy_priority(candidate) -> tuple[int, float, float]:
    commitment = getattr(candidate, "commitment", 0)
    try:
        commitment_value = int(commitment)
    except (TypeError, ValueError):
        commitment_value = 0
    return (
        commitment_value,
        float(getattr(candidate, "confidence", 0.0) or 0.0),
        float(getattr(candidate, "strength", 0.0) or 0.0),
    )


def _strategy_features(state) -> tuple[str, ...]:
    try:
        _developments, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return ()
    candidates = tuple(getattr(composition, "strategy_candidates", ()) or ())
    if not candidates:
        return ()

    # Do not trust container ordering: the resource layer must follow the strongest
    # actual commitment, not whichever exploratory candidate happened to be first.
    candidate = max(candidates, key=_strategy_priority)
    values: list[str] = []
    for prescription in getattr(candidate, "prescriptions", ()) or ():
        text = str(prescription)
        if text.startswith("seek_feature:"):
            feature = text.split(":", 1)[1].strip()
            if feature:
                values.append(feature)
    return tuple(dict.fromkeys(values))


def _strategy_card_need(policy, state, profile, family: str):
    features = _strategy_features(state)
    if not features:
        return None
    prefixes = policy.FAMILY_CARD_FEATURE_PREFIXES.get(family, ())
    exact = policy.FAMILY_TRANSFORM_FEATURES.get(family, frozenset())
    relevant = {
        feature
        for feature in features
        if feature in exact or any(feature.startswith(prefix) for prefix in prefixes)
    }
    unmet = {
        feature
        for feature in relevant
        if profile.strength(feature) <= 0.0 and not profile.can_produce(feature)
    }
    gap_score = min(1.0, len(unmet) / 3.0)

    modified_cards = sum(count for _, count in profile.enhancement_counts)
    modified_cards += sum(count for _, count in profile.seal_counts)
    modified_cards += sum(count for _, count in profile.edition_counts)
    modified_density = (
        min(1.0, modified_cards / max(1, profile.deck_size) / 0.20)
        if profile.deck_size > 0
        else 0.0
    )
    need = (
        min(1.0, gap_score * 0.75 + modified_density * 0.25)
        if family == "STANDARD"
        else gap_score
    )
    unmet_text = ", ".join(sorted(unmet)) if unmet else "none"
    return need, (
        "D8 strategy-scoped demand replaces aggregate owned-effect wishlist",
        f"strategy relevant unmet build features={unmet_text}",
        f"playing-card modifier density={modified_density:.3f}",
    )


def install_strategy_resource_coherence_policy() -> None:
    if getattr(BuildAwareShopBoosterPolicy, "_strategy_resource_coherence_installed", False):
        return

    original_build_need = BuildAwareShopBoosterPolicy._build_need

    def _build_need(self, state, profile, *, family: str):
        if family in {"STANDARD", "ARCANA", "SPECTRAL"}:
            scoped = _strategy_card_need(self, state, profile, family)
            if scoped is not None:
                return scoped
        return original_build_need(self, state, profile, family=family)

    BuildAwareShopBoosterPolicy._build_need = _build_need
    BuildAwareShopBoosterPolicy._strategy_resource_coherence_installed = True

    original_voucher_decide = VoucherAcquisitionPolicy.decide

    def voucher_decide(self, state, candidate):
        decision = original_voucher_decide(self, state, candidate)
        if (
            decision.action == BUY
            and float(decision.build_compatibility) <= 0.0
            and int(decision.money_after) < _BASIC_CASH_RESERVE
        ):
            return replace(
                decision,
                action=HOLD,
                executable_action=None,
                rationale=(
                    *decision.rationale,
                    f"D3 strategy/resource veto: zero-compatibility Voucher may not breach ${_BASIC_CASH_RESERVE} basic reserve",
                ),
            )
        return decision

    VoucherAcquisitionPolicy.decide = voucher_decide
    VoucherAcquisitionPolicy._strategy_resource_coherence_installed = True
