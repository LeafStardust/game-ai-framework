"""Resolve explicitly calibrated client-size variants without guessing scaling."""

from copy import deepcopy

POINT_FIELDS = {"slots", "choice_points", "chi", "pon", "skip", "kan", "riichi", "tsumo", "ron"}


def profile_for_size(profile, client_size):
    size = list(client_size)
    if len(size) != 2 or any(type(value) is not int or value <= 1 for value in size):
        raise ValueError("Invalid client size")
    if profile.get("verified") is not True:
        raise ValueError("Base profile is not verified")
    result = deepcopy(profile)
    variants = result.pop("size_variants", [])
    if result.get("client_size") == size:
        return result
    matches = [variant for variant in variants if variant.get("client_size") == size]
    if len(matches) != 1 or matches[0].get("verified") is not True:
        raise ValueError("Client size is not uniquely calibrated; input remains blocked")
    variant = matches[0]
    # Every coordinate must be reverified, even when normalized values coincide.
    required = POINT_FIELDS.intersection(result)
    if not required or not required.issubset(variant):
        raise ValueError("Size variant is missing calibrated coordinates")
    result["client_size"] = size
    for field in required:
        result[field] = deepcopy(variant[field])
    return result


def discard_profile(report, client_size, directory=None):
    """Select a unique bundled calibration for size, hand count and trigger."""
    import json
    from pathlib import Path
    state = report.get("state") or {}
    if not report.get("state_ready"):
        raise ValueError("Reader is not ready")
    trigger = (report.get("last_event") or {}).get("name")
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parents[1] / "layouts"
    matches = []
    for path in directory.glob("*.json"):
        profile = json.loads(path.read_text(encoding="utf-8"))
        # Operation-specific layouts (for example Riichi) also contain hand
        # slots, but must never compete with generic discard calibrations.
        if "operation_types" in profile:
            continue
        if profile.get("hand_count") != len(state.get("hand", [])) or profile.get("trigger") != trigger:
            continue
        try:
            matches.append(profile_for_size(profile, client_size))
        except ValueError:
            continue
    if len(matches) != 1:
        raise ValueError("No unique calibrated discard layout for this hand, trigger and client size")
    return matches[0]


def profile_for_viewport(profile, client_size, viewport):
    """Build an unverified candidate by fitting calibrated points to a viewport.

    viewport is (left, top, width, height) in target-client physical pixels.
    The caller must inspect the actual game viewport; no aspect ratio or bars
    are inferred from the client dimensions. The result cannot enable input
    until its points have been visually validated.
    """
    from math import isfinite
    size = list(client_size)
    if len(size) != 2 or any(type(v) is not int or v <= 1 for v in size):
        raise ValueError("Invalid client size")
    if (len(viewport) != 4 or any(type(v) is not int for v in viewport)):
        raise ValueError("Viewport must contain four integer pixel dimensions")
    left, top, width, height = viewport
    if left < 0 or top < 0 or width <= 1 or height <= 1 or left + width > size[0] or top + height > size[1]:
        raise ValueError("Viewport lies outside the target client")
    source_size = profile.get("client_size", [])
    source = profile_for_size(profile, source_size)
    fields = POINT_FIELDS.intersection(source)
    if not fields:
        raise ValueError("Profile has no calibrated points")

    def point(value):
        if (not isinstance(value, (list, tuple)) or len(value) != 2
                or any(type(v) not in (int, float) or not isfinite(v) or not 0 < v < 1 for v in value)):
            raise ValueError("Invalid calibrated point")
        x, y = value
        return [(left + x * (width - 1)) / (size[0] - 1),
                (top + y * (height - 1)) / (size[1] - 1)]

    result = deepcopy(source)
    for field in fields:
        value = source[field]
        result[field] = [point(p) for p in value] if field in {"slots", "choice_points"} else point(value)
    result.update(client_size=size, verified=False,
                  calibration_source={"client_size": source_size, "viewport": list(viewport)})
    return result
