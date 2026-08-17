from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping


@dataclass(frozen=True)
class StrategyNodeSpec:
    """Topology-only metadata for one Balatro strategy node.

    Component relationships remain strategy-owned catalogue data. This object only
    describes specialization structure while the legacy flat catalogue is migrated
    one subtree at a time.
    """

    strategy_id: str
    name: str
    parent_strategy_id: str | None = None
    is_fallback_leaf: bool = False


class StrategyTopology:
    """Validated forest of strategy specialization nodes.

    Parent -> child means "more specific realization", never natural poker-hand
    progression. Only leaves are actionable strategy candidates once consumers are
    migrated to the tree runtime.
    """

    def __init__(self, nodes: Iterable[StrategyNodeSpec]) -> None:
        by_id: dict[str, StrategyNodeSpec] = {}
        for node in nodes:
            strategy_id = str(node.strategy_id)
            if not strategy_id:
                raise ValueError("strategy node id must be non-empty")
            if strategy_id in by_id:
                raise ValueError(f"duplicate strategy node id: {strategy_id}")
            by_id[strategy_id] = node

        parent_by_id: dict[str, str | None] = {}
        children: dict[str, list[str]] = {strategy_id: [] for strategy_id in by_id}
        for strategy_id, node in by_id.items():
            parent_id = node.parent_strategy_id
            if parent_id is not None:
                parent_id = str(parent_id)
                if parent_id == strategy_id:
                    raise ValueError(f"strategy node cannot parent itself: {strategy_id}")
                if parent_id not in by_id:
                    raise ValueError(
                        f"strategy node {strategy_id} references missing parent {parent_id}"
                    )
                children[parent_id].append(strategy_id)
            parent_by_id[strategy_id] = parent_id

        self._validate_acyclic(parent_by_id)

        self.nodes: Mapping[str, StrategyNodeSpec] = MappingProxyType(by_id)
        self.parent_by_id: Mapping[str, str | None] = MappingProxyType(parent_by_id)
        self.children_by_id: Mapping[str, tuple[str, ...]] = MappingProxyType(
            {
                strategy_id: tuple(sorted(child_ids))
                for strategy_id, child_ids in children.items()
            }
        )
        self.roots: tuple[str, ...] = tuple(
            sorted(
                strategy_id
                for strategy_id, parent_id in parent_by_id.items()
                if parent_id is None
            )
        )
        self.leaves: tuple[str, ...] = tuple(
            sorted(
                strategy_id
                for strategy_id, child_ids in self.children_by_id.items()
                if not child_ids
            )
        )

    @staticmethod
    def _validate_acyclic(parent_by_id: Mapping[str, str | None]) -> None:
        for strategy_id in parent_by_id:
            seen: set[str] = set()
            current: str | None = strategy_id
            while current is not None:
                if current in seen:
                    cycle = " -> ".join((*sorted(seen), current))
                    raise ValueError(f"strategy topology cycle detected: {cycle}")
                seen.add(current)
                current = parent_by_id[current]

    def is_leaf(self, strategy_id: str) -> bool:
        if strategy_id not in self.nodes:
            raise KeyError(strategy_id)
        return not self.children_by_id[strategy_id]

    def ancestors(self, strategy_id: str) -> tuple[str, ...]:
        """Return nearest parent first, then continue outward to the root."""

        if strategy_id not in self.nodes:
            raise KeyError(strategy_id)
        values: list[str] = []
        current = self.parent_by_id[strategy_id]
        while current is not None:
            values.append(current)
            current = self.parent_by_id[current]
        return tuple(values)

    def path(self, strategy_id: str) -> tuple[str, ...]:
        """Return root -> ... -> strategy_id for diagnostics."""

        return (*reversed(self.ancestors(strategy_id)), strategy_id)


HIGH_CARD_STRATEGY_NODES: tuple[StrategyNodeSpec, ...] = (
    StrategyNodeSpec(
        strategy_id="high_card",
        name="High Card",
    ),
    StrategyNodeSpec(
        strategy_id="high_card_core",
        name="Core Repetition / Level High Card",
        parent_strategy_id="high_card",
        is_fallback_leaf=True,
    ),
    StrategyNodeSpec(
        strategy_id="high_card_stuntman",
        name="Stuntman / Small-Hand High Card",
        parent_strategy_id="high_card",
    ),
    StrategyNodeSpec(
        strategy_id="high_card_baron_mime",
        name="Baron-Mime Steel-King High Card",
        parent_strategy_id="high_card",
    ),
)

HIGH_CARD_STRATEGY_TOPOLOGY = StrategyTopology(HIGH_CARD_STRATEGY_NODES)
