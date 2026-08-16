from __future__ import annotations

from pathlib import Path
from typing import Literal

from .production_observer import ProductionBalatroObserver
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


ObservationSource = Literal["memory", "save"]


def create_balatro_state_observer(
    source: ObservationSource = "memory",
    *,
    save_path: str | Path | None = None,
    profile: str = "1",
):
    """Create the state observer used by production live control.

    Direct read-only process memory is the production default. ``save.jkr`` is
    retained only as an explicit fallback/debug/recovery source.
    """

    source = str(source).lower()
    if source == "memory":
        if save_path is not None:
            raise ValueError("save_path is only valid with observation source 'save'")
        return ProductionBalatroObserver()
    if source == "save":
        return SaveBalatroObserver(
            BalatroSaveReader(save_path, profile=profile)
        )
    raise ValueError(
        f"unsupported Balatro observation source {source!r}; expected 'memory' or 'save'"
    )
