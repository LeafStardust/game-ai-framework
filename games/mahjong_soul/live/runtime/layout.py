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
