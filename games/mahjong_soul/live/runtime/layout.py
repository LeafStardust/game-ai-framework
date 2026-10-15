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
        if profile.get("hand_count") != len(state.get("hand", [])) or profile.get("trigger") != trigger:
            continue
        try:
            matches.append(profile_for_size(profile, client_size))
        except ValueError:
            continue
    if len(matches) != 1:
        raise ValueError("No unique calibrated discard layout for this hand, trigger and client size")
    return matches[0]
