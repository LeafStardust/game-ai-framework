from __future__ import annotations

from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.joker_state_contract import (
    JokerPublicFieldSpec,
    public_joker_state_specs,
)


_FACTORY = LiveJokerFactory()


def declared_joker_state_specs(
    *,
    center: str | None,
    label: str | None,
    ability_name: str | None = None,
) -> tuple[JokerPublicFieldSpec, ...]:
    """Resolve the narrow public-state contract for one observed Joker item."""
    joker_class = _FACTORY.resolve_class(
        {
            "center": center,
            "label": label,
            "ability_name": ability_name,
        }
    )
    if joker_class is None:
        return ()
    return public_joker_state_specs(joker_class.__name__)
