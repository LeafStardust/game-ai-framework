"""Seeded center selection shared by exact consumable generation boundaries."""

from collections.abc import Collection

from games.balatro.env.consumable_centers import current_consumable_pool_from_eligible_keys
from games.balatro.env.rng import BalatroRNG


def poll_consumable_center(
    rng: BalatroRNG,
    pool: tuple[str, ...],
    pool_key: str,
) -> tuple[str, int]:
    """Advance vanilla's base node and successive unavailable-position retries."""
    center = pool[rng.pseudorandom_element_index(len(pool), pool_key)]
    resamples = 0
    while center == "UNAVAILABLE":
        resamples += 1
        retry_key = f"{pool_key}_resample{resamples + 1}"
        center = pool[rng.pseudorandom_element_index(len(pool), retry_key)]
    return center, resamples


def poll_held_spectral_center(
    rng: BalatroRNG,
    ante: int,
    eligible_keys: Collection[str],
    *,
    key_append: str = "sea",
) -> tuple[str, int]:
    """Poll a held non-soulable Spectral from authoritative eligibility."""
    if type(ante) is not int:
        raise TypeError("held Spectral generation requires an exact integer Ante")
    if key_append not in ("sea", "sixth"):
        raise ValueError("unsupported held Spectral RNG domain")
    pool = current_consumable_pool_from_eligible_keys("Spectral", eligible_keys)
    return poll_consumable_center(rng, pool, f"Spectral{key_append}{ante}")
