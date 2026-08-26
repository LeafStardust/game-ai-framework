from __future__ import annotations

from math import inf, nextafter
from typing import Mapping


# Compatibility-only tiny positive cap for legacy callers that still need an
# additive tie-break rather than the preferred value-aware helper below.  The
# magnitude is derived from floating-point spacing (one ULP at 4.0), not from a
# gameplay utility constant.  New decision code should prefer
# ``bounded_discovery_tiebreak`` so the increment is relative to the compared value.
DISCOVERY_TIEBREAK_CAP = nextafter(4.0, inf) - 4.0


def discovery_status(item) -> bool | None:
    """Return explicit public collection-discovery state when it is available."""
    if item is None:
        return None

    if isinstance(item, Mapping):
        value = item.get("discovered")
    else:
        value = getattr(item, "discovered", None)
        if value is None:
            data = getattr(item, "data", None)
            value = data.get("discovered") if isinstance(data, Mapping) else None

    return value if isinstance(value, bool) else None


def is_undiscovered(item) -> bool:
    """True only for an explicitly observed undiscovered item."""
    return discovery_status(item) is False


def bounded_discovery_tiebreak(value: float, item) -> float:
    """Apply the smallest representable positive preference to an exact tie.

    Discovery preference is intentionally post-admission and threshold-free. It
    never turns a zero/negative strategic gain positive and can only separate
    floating-point-equal positive options by one ULP.
    """
    value = float(value)
    if value <= 0.0 or not is_undiscovered(item):
        return value
    return nextafter(value, inf)
