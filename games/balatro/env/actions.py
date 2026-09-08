"""Typed RL actions backed by the frozen production action contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from games.balatro.env_contract import CapabilityStatus, contract_for


@dataclass(frozen=True)
class EnvAction:
    """One canonical strategic action plus immutable parameters.

    ``alias`` is the stable RL-facing name from ``env_contract``. Parameters are
    represented as sorted key/value pairs so actions remain comparable and safe
    to use in masks/replay logs without inventing a second action identifier.
    """

    alias: str
    params: tuple[tuple[str, Any], ...] = ()

    @classmethod
    def from_alias(cls, alias: str, params: Mapping[str, Any] | None = None) -> "EnvAction":
        contract = contract_for(alias)
        if contract.status is not CapabilityStatus.SUPPORTED:
            raise ValueError(f"action {contract.alias} is not training-exposed")
        normalized_params = tuple(sorted((str(key), value) for key, value in (params or {}).items()))
        return cls(alias=contract.alias, params=normalized_params)

    @property
    def action_id(self) -> str:
        contract = contract_for(self.alias)
        if contract.status is not CapabilityStatus.SUPPORTED or contract.action_id is None:
            raise ValueError(f"action {self.alias} is not training-exposed")
        return contract.action_id

    def payload(self) -> dict[str, Any]:
        return dict(self.params)


def validate_training_action(action: EnvAction) -> None:
    """Fail closed if a backend exposes anything outside the frozen L3 mask."""

    contract = contract_for(action.alias)
    if contract.status is not CapabilityStatus.SUPPORTED:
        raise ValueError(f"backend exposed non-training action {contract.alias}")
    if contract.action_id is None or contract.legality_owner is None or contract.execution_owner is None:
        raise ValueError(f"backend exposed incompletely-owned action {contract.alias}")
