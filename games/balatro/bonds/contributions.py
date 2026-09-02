from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable, Mapping

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, BondRealization


RANK_ORDER = (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5)


def component_source_id(component: Any, *, collection: str, index: int) -> str:
    """Return a stable-enough public source key for one component in a state.

    Runtime/public objects may expose a durable instance identifier. Snapshot and
    lightweight objects often do not, so their collection slot is the canonical
    fallback for one evaluation. The ledger is stateless, so current and projected
    states are evaluated by the same rule.
    """
    for attr in ("instance_id", "uid", "uuid", "id"):
        value = getattr(component, attr, None)
        if value is not None and not callable(value):
            return f"{collection}:{attr}:{value}"
    return f"{collection}:slot:{index}"


def component_contribution(
    component: Any,
    *,
    collection: str,
    index: int,
    label: str,
    value: float,
    mechanic: str,
) -> BondContribution:
    return BondContribution(
        source=label,
        value=float(value),
        source_id=component_source_id(component, collection=collection, index=index),
        mechanic=mechanic,
    )


def state_contribution(
    source_id: str,
    label: str,
    value: float,
    *,
    mechanic: str,
) -> BondContribution:
    return BondContribution(
        source=label,
        value=float(value),
        source_id=f"state:{source_id}",
        mechanic=mechanic,
    )


def normalize_contributions(
    contributions: Iterable[BondContribution],
) -> tuple[BondContribution, ...]:
    """Canonical same-Bond source normalization.

    Contributions without a Phase C source_id remain untouched during migration.
    For canonical evidence, one underlying source may contribute at most once to
    one Bond. If overlapping descriptors emit several entries for the same source,
    the strongest supported contribution wins and its diagnostic mechanic list is
    retained in conditions. The same source may independently contribute to other
    Bonds because normalization is local to one Bond development.
    """
    legacy: list[BondContribution] = []
    keyed: dict[str, list[BondContribution]] = {}
    order: list[str] = []

    for contribution in contributions:
        if contribution.source_id is None:
            legacy.append(contribution)
            continue
        if contribution.source_id not in keyed:
            keyed[contribution.source_id] = []
            order.append(contribution.source_id)
        keyed[contribution.source_id].append(contribution)

    normalized: list[BondContribution] = list(legacy)
    for source_id in order:
        group = keyed[source_id]
        strongest = max(group, key=lambda item: item.value)
        mechanics = tuple(dict.fromkeys(
            item.mechanic for item in group if item.mechanic
        ))
        if len(mechanics) > 1:
            strongest = replace(
                strongest,
                conditions=tuple(dict.fromkeys((*strongest.conditions, *(f"mechanic:{m}" for m in mechanics)))),
            )
        normalized.append(strongest)
    return tuple(normalized)


def rank_for_total(
    total: float,
    thresholds: Mapping[BondRank, float],
) -> tuple[BondRank, float | None]:
    rank = BondRank.R0
    for candidate in RANK_ORDER:
        threshold = float(thresholds[candidate])
        if total < threshold:
            return rank, threshold
        rank = candidate
    return BondRank.R5, None


def finalize_development(
    bond_id: str,
    contributions: Iterable[BondContribution],
    thresholds: Mapping[BondRank, float],
    *,
    unlocked: bool = True,
    target: str | None = None,
) -> BondDevelopment:
    normalized = normalize_contributions(contributions)
    total = sum(item.value for item in normalized)
    rank, next_threshold = rank_for_total(total, thresholds)
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=unlocked,
        contribution=total,
        rank=rank,
        next_rank_threshold=next_threshold,
        contributions=normalized,
        target=target,
        realization=BondRealization.DORMANT if rank == BondRank.R0 else BondRealization.PARTIAL,
    )
