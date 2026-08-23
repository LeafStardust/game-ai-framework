from __future__ import annotations

"""Feed proven strategy coherence back into Bond development.

Raw Bond evaluators deliberately score local evidence only.  The composition layer
can discover that several locally weak Bonds form one coherent engine; without a
second pass that coherence never affects rank authority.  This module supplies a
bounded, non-circular reinforcement pass after raw composition.

Rules:
- only the currently pinned strategy may reinforce development;
- ambient profile features (``feature:...``) never count as concrete support;
- the Bond itself must participate in a semantic link through a concrete source;
- coherence may advance at most one rank beyond raw development;
- PINNED may support at most R2, ESTABLISHED at most R3, DOMINANT at most R4;
- R5 always requires direct catalogue evidence and can never be manufactured by
  composition coherence alone.
"""

from dataclasses import replace

from games.balatro.bonds.model import BondContribution, BondDevelopment, BondRank, MechanicalRole
from games.balatro.bonds.rank_progression import canonical_rank_thresholds
from games.balatro.bonds.strategy_semantics import StrategyCandidate, StrategyCommitment


def _is_concrete_source(source: str) -> bool:
    return bool(str(source).strip()) and not str(source).startswith("feature:")


def _rank_for(total: float, thresholds: dict[BondRank, float] | object) -> tuple[BondRank, float | None]:
    table = thresholds  # Mapping-like object from the canonical registry.
    rank = BondRank.R0
    for candidate in (BondRank.R1, BondRank.R2, BondRank.R3, BondRank.R4, BondRank.R5):
        threshold = float(table[candidate])  # type: ignore[index]
        if total >= threshold:
            rank = candidate
            continue
        return rank, threshold
    return BondRank.R5, None


def _commitment_cap(commitment: StrategyCommitment) -> BondRank:
    if commitment >= StrategyCommitment.DOMINANT:
        return BondRank.R4
    if commitment >= StrategyCommitment.ESTABLISHED:
        return BondRank.R3
    if commitment >= StrategyCommitment.PINNED:
        return BondRank.R2
    return BondRank.R0


def _concrete_link_count(candidate: StrategyCandidate, bond_id: str) -> int:
    links = {
        (
            link.left_bond,
            link.left_source,
            link.right_bond,
            link.right_source,
            link.relation,
        )
        for link in candidate.links
        if (
            link.left_bond == bond_id
            and _is_concrete_source(link.left_source)
            and _is_concrete_source(link.right_source)
        )
        or (
            link.right_bond == bond_id
            and _is_concrete_source(link.right_source)
            and _is_concrete_source(link.left_source)
        )
    }
    return len(links)


def reinforce_developments(
    developments: tuple[BondDevelopment, ...],
    candidate: StrategyCandidate | None,
) -> tuple[BondDevelopment, ...]:
    """Return developments with bounded one-rank strategy coherence support."""
    if candidate is None or candidate.commitment < StrategyCommitment.PINNED:
        return developments

    thresholds_by_bond = canonical_rank_thresholds()
    cap = _commitment_cap(candidate.commitment)
    result: list[BondDevelopment] = []

    for dev in developments:
        if dev.bond_id not in candidate.bond_ids or dev.rank < BondRank.R0:
            result.append(dev)
            continue
        concrete_links = _concrete_link_count(candidate, dev.bond_id)
        if concrete_links <= 0:
            result.append(dev)
            continue

        raw_rank = dev.rank
        one_step = BondRank(min(int(BondRank.R5), int(raw_rank) + 1))
        target_rank = BondRank(min(int(cap), int(one_step)))
        if target_rank <= raw_rank:
            result.append(dev)
            continue

        thresholds = thresholds_by_bond[dev.bond_id]
        required = float(thresholds[target_rank])
        bonus = max(0.0, required - float(dev.contribution))
        if bonus <= 0.0:
            result.append(dev)
            continue

        parts = (*dev.contributions, BondContribution(
            source=f"Pinned strategy coherence: {candidate.strategy_id}",
            value=bonus,
            roles=(MechanicalRole.SUPPORT,),
            targets=(dev.target,) if dev.target else (),
            conditions=(
                f"commitment={candidate.commitment.name}",
                f"concrete_links={concrete_links}",
                "one_rank_maximum",
            ),
        ))
        total = float(dev.contribution) + bonus
        rank, next_threshold = _rank_for(total, thresholds)
        result.append(replace(
            dev,
            contribution=total,
            rank=rank,
            next_rank_threshold=next_threshold,
            contributions=parts,
        ))

    return tuple(result)
