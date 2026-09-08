from __future__ import annotations

"""Resource-policy coherence for public D8/D3 state.

Unopened booster contents are hidden, so D8 must derive pre-open demand only from
public mechanical state and its native BuildProfile expectation. Canonical
StrategyDelta applies later, once D9 has a visible exact persistent outcome to
project. Historical named-strategy commitments and ``seek_feature``/``seek_bond``
prescriptions therefore have no authority in unopened-pack admission.

Celestial demand keeps its separate observed-hand specialization signal because
repeated public hand usage is direct mechanical evidence rather than hidden-pack or
strategy-controller state. The independent D3 zero-fit Voucher cash floor is also
preserved.
"""

from dataclasses import replace

from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy
from games.balatro.shop_voucher_policy import BUY, HOLD, VoucherAcquisitionPolicy


_BASIC_CASH_RESERVE = 5


def _celestial_observed_need(state) -> tuple[float, tuple[str, ...]]:
    counts = {
        str(hand): max(0, int(value or 0))
        for hand, value in (getattr(state, "hand_play_counts", {}) or {}).items()
        if max(0, int(value or 0)) > 0
    }
    total = sum(counts.values())
    if total <= 0:
        return 0.0, (
            "Celestial demand requires observed hand specialization; permanent hand levels alone do not create demand",
        )

    hand, plays = max(counts.items(), key=lambda item: (item[1], item[0]))
    concentration = plays / total
    level = max(1, int((getattr(state, "hand_levels", {}) or {}).get(hand, 1) or 1))
    repetition = min(1.0, plays / 8.0)
    # Repeated use of an underleveled hand is a direct public signal that Celestial
    # development can support what the agent is actually playing. Existing levels
    # reduce urgency; they never manufacture demand without play history.
    underlevel = 1.0 / max(1.0, float(level))
    need = min(1.0, (0.60 * concentration + 0.40 * repetition) * underlevel)
    return need, (
        f"observed Celestial target hand={hand} plays={plays}/{total}",
        f"observed hand-play concentration={concentration:.3f}",
        f"current observed target level={level}",
    )


def install_strategy_resource_coherence_policy() -> None:
    if getattr(BuildAwareShopBoosterPolicy, "_strategy_resource_coherence_installed", False):
        return

    original_build_need = BuildAwareShopBoosterPolicy._build_need

    def _build_need(self, state, profile, *, family: str):
        if family == "CELESTIAL":
            return _celestial_observed_need(state)
        # STANDARD / ARCANA / SPECTRAL are unopened stochastic acquisitions. Their
        # pre-open demand remains the native D8 public BuildProfile expectation;
        # exact persistent outcomes receive canonical StrategyDelta after opening.
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
                    f"D3 resource veto: zero-compatibility Voucher may not breach ${_BASIC_CASH_RESERVE} basic reserve",
                ),
            )
        return decision

    VoucherAcquisitionPolicy.decide = voucher_decide
    VoucherAcquisitionPolicy._strategy_resource_coherence_installed = True
