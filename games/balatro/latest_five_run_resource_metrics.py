from __future__ import annotations

"""Telemetry-backed D8 resource-demand calibration for Red/White.

The latest five-run batch repeatedly reached Ante 5/6 with 12-16 plays of one hand
while that hand remained level 1, yet still spent heavily on Standard/Arcana packs.
The base Celestial need metric was lowest in exactly that state because it rewarded
*existing* hand-level investment. Standard need also received a positive modifier-
density term even when no specific card-feature gap remained.

This layer corrects those metrics without inspecting unopened pack contents.
"""

from games.balatro.shop_booster_policy import BuildAwareShopBoosterPolicy


def _normalized_hand_levels(profile) -> dict[str, int]:
    result: dict[str, int] = {}
    for key, value in getattr(profile, "hand_levels", ()) or ():
        result[str(key).upper()] = max(1, int(value or 1))
    return result


def _normalized_play_counts(state) -> dict[str, int]:
    return {
        str(key).upper(): max(0, int(value or 0))
        for key, value in (getattr(state, "hand_play_counts", {}) or {}).items()
    }


def _celestial_need(state, profile) -> tuple[float, tuple[str, ...]]:
    counts = _normalized_play_counts(state)
    if not counts:
        return 0.0, (
            "no observed poker-hand history; Celestial specialization demand=0",
        )

    hand, top_plays = max(counts.items(), key=lambda item: (item[1], item[0]))
    total_plays = sum(counts.values())
    concentration = top_plays / max(1, total_plays)
    repetition = min(1.0, top_plays / 8.0)
    levels = _normalized_hand_levels(profile)
    level = max(1, int(levels.get(hand, 1)))
    underinvestment = 1.0 - min(1.0, max(0, level - 1) / 3.0)

    # No repeated hand history => no autonomous Celestial urgency. Once repeated
    # use is real, low level becomes positive unmet demand rather than a reason to
    # value the pack less. Eight public plays is the same strong-specialization
    # floor used by the latest empirical Planet-alignment layer.
    need = repetition * (
        0.55
        + 0.25 * concentration
        + 0.20 * underinvestment
    )
    need = max(0.0, min(1.0, need))
    return need, (
        f"most-played hand={hand} plays={top_plays}/{total_plays}",
        f"observed hand-play concentration={concentration:.3f}",
        f"current {hand} level={level}; underinvestment={underinvestment:.3f}",
        f"repetition demand={repetition:.3f}",
        f"telemetry-calibrated Celestial need={need:.3f}",
    )


def install_latest_five_run_resource_metrics() -> None:
    if getattr(BuildAwareShopBoosterPolicy, "_latest_five_run_resource_metrics_installed", False):
        return

    original_build_need = BuildAwareShopBoosterPolicy._build_need

    def _build_need(self, state, profile, *, family: str):
        family = str(family).upper()
        if family == "CELESTIAL":
            return _celestial_need(state, profile)

        need, notes = original_build_need(self, state, profile, family=family)
        if family != "STANDARD":
            return need, notes

        # The base Standard metric is 0.75*actual feature gap + 0.25*already-
        # modified density. Existing modifier density is evidence of progress, not
        # an unmet need by itself. Recover the actual gap term from the public base
        # rationale inputs: if no demanded feature is missing, Standard demand is 0.
        demanded: set[str] = set()
        for descriptor in profile.effects:
            demanded.update(descriptor.requires)
            demanded.update(descriptor.scales_with)
            demanded.update(descriptor.amplifies)

        prefixes = self.FAMILY_CARD_FEATURE_PREFIXES.get("STANDARD", ())
        exact = self.FAMILY_TRANSFORM_FEATURES.get("STANDARD", frozenset())
        relevant = {
            feature
            for feature in demanded
            if feature in exact
            or any(feature.startswith(prefix) for prefix in prefixes)
        }
        unmet = {
            feature
            for feature in relevant
            if profile.strength(feature) <= 0.0 and not profile.can_produce(feature)
        }
        gap_score = min(1.0, len(unmet) / 3.0)

        modified_cards = sum(count for _, count in profile.enhancement_counts)
        modified_cards += sum(count for _, count in profile.seal_counts)
        modified_cards += sum(count for _, count in profile.edition_counts)
        modified_density = (
            min(1.0, modified_cards / max(1, profile.deck_size) / 0.20)
            if profile.deck_size > 0
            else 0.0
        )
        # If an actual gap exists, low modifier density modestly raises the need;
        # density can never create demand from zero.
        calibrated = gap_score * (0.75 + 0.25 * (1.0 - modified_density))
        calibrated = max(0.0, min(1.0, calibrated))
        unmet_text = ", ".join(sorted(unmet)) if unmet else "none"
        return calibrated, (
            f"relevant unmet build features={unmet_text}",
            f"playing-card modifier density={modified_density:.3f}",
            "five-run calibration: modifier density cannot manufacture Standard-pack demand",
            f"telemetry-calibrated Standard need={calibrated:.3f}",
        )

    BuildAwareShopBoosterPolicy._build_need = _build_need
    BuildAwareShopBoosterPolicy._latest_five_run_resource_metrics_installed = True
