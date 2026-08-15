from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND


DEFAULT_BLIND_SKIP_THRESHOLD = 2.0
DEFAULT_FALLBACK_TAG_VALUE = 4.0

# Conservative v0.9 utility estimates for every normal skip tag. These values are
# deliberately coarse routing utilities, not claims that every tag is cash-equivalent.
# Dynamic tags with directly observable public-state dependence are refined below.
CONSERVATIVE_TAG_VALUES = {
    "tag_uncommon": 5.0,
    "tag_rare": 7.0,
    "tag_negative": 9.0,
    "tag_foil": 5.0,
    "tag_holo": 5.5,
    "tag_polychrome": 7.0,
    "tag_investment": 25.0,
    "tag_voucher": 5.0,
    "tag_boss": 2.0,
    "tag_standard": 5.0,
    "tag_charm": 6.0,
    "tag_meteor": 6.0,
    "tag_buffoon": 6.0,
    "tag_handy": 4.0,
    "tag_garbage": 4.0,
    "tag_ethereal": 6.0,
    "tag_coupon": 7.0,
    "tag_double": 4.0,
    "tag_juggle": 4.0,
    "tag_d_six": 4.0,
    "tag_top_up": 5.0,
    "tag_skip": 5.0,
    "tag_orbital": 6.0,
    "tag_economy": 0.0,
}


@dataclass(frozen=True)
class BlindSkipDecision:
    action_name: str
    blind_type: str
    play_ev: float
    tag_ev: float
    economy_opportunity_cost: float
    skip_ev: float
    margin: float
    threshold: float
    tag_value_source: str
    tag_key: str | None = None

    @property
    def notes(self) -> tuple[str, ...]:
        decision = "SKIP" if self.action_name == SKIP_BLIND else "PLAY"
        return (
            f"blind_decision={decision}",
            f"blind_type={self.blind_type}",
            f"tag_key={self.tag_key or 'NONE'}",
            f"play_ev={self.play_ev:.3f}",
            f"tag_ev={self.tag_ev:.3f}",
            f"tag_value_source={self.tag_value_source}",
            f"economy_opportunity_cost={self.economy_opportunity_cost:.3f}",
            f"skip_ev={self.skip_ev:.3f}",
            f"skip_margin={self.margin:.3f}",
            f"skip_threshold={self.threshold:.3f}",
        )


def _number(value, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return float(default)
    return float(value)


def _tag_key(value) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def _joker_open_slots(payload: dict) -> int | None:
    jokers = payload.get("jokers")
    if not isinstance(jokers, dict):
        return None
    count = jokers.get("count")
    limit = jokers.get("limit")
    if isinstance(count, bool) or not isinstance(count, (int, float)):
        return None
    if isinstance(limit, bool) or not isinstance(limit, (int, float)):
        return None
    return max(0, int(limit) - int(count))


def _observed_tag_value(tag_key: str, payload: dict) -> float | None:
    if tag_key not in CONSERVATIVE_TAG_VALUES:
        return None

    if tag_key == "tag_economy":
        # Economy is directly tied to current public cash and is capped by the tag.
        return min(40.0, max(0.0, _number(payload.get("money"), 0.0)))

    if tag_key == "tag_top_up":
        # Top-up cannot add more Jokers than the currently observable free capacity.
        open_slots = _joker_open_slots(payload)
        if open_slots is not None:
            return min(2, open_slots) * 2.5

    return float(CONSERVATIVE_TAG_VALUES[tag_key])


def decide_blind_play_or_skip(
    snapshot,
    *,
    threshold: float = DEFAULT_BLIND_SKIP_THRESHOLD,
    fallback_tag_value: float = DEFAULT_FALLBACK_TAG_VALUE,
) -> BlindSkipDecision:
    """Score playing the visible blind against skipping for its public live tag.

    When process-memory observation supplies a recognized public tag key, D13 uses
    its conservative tag-specific utility. Missing or future/unmodeled tags retain
    the explicit fallback rather than inventing a tag-specific value.
    """
    payload = snapshot.payload if isinstance(snapshot.payload, dict) else {}
    blind = payload.get("blind")
    blind = blind if isinstance(blind, dict) else {}
    blind_type = str(blind.get("type") or "UNKNOWN").upper()
    tag_key = _tag_key(blind.get("tag"))

    # These are conservative immediate-economy proxies, not claims that live reward
    # data was observed. Unknown/Boss tiers are deliberately biased toward playing.
    play_ev = {
        "SMALL": 3.0,
        "BIG": 4.0,
        "BOSS": 6.0,
    }.get(blind_type, 6.0)

    money = _number(payload.get("money"), 0.0)
    # Skipping while cash-poor has extra opportunity cost because it forfeits a
    # chance to rebuild shop liquidity. Cap the term so it remains subordinate to
    # the explicit tag estimate and tunable decision threshold.
    economy_opportunity_cost = min(2.0, max(0.0, 5.0 - money) * 0.25)

    observed_value = (
        _observed_tag_value(tag_key, payload)
        if tag_key is not None
        else None
    )
    if observed_value is not None:
        tag_ev = max(0.0, observed_value)
        tag_value_source = f"observed_live_tag:{tag_key}"
    else:
        tag_ev = max(0.0, float(fallback_tag_value))
        tag_value_source = (
            f"fallback_unmodeled_live_tag:{tag_key}"
            if tag_key is not None
            else "fallback_unidentified_live_tag"
        )

    skip_ev = tag_ev - economy_opportunity_cost
    margin = skip_ev - play_ev
    normalized_threshold = max(0.0, float(threshold))

    can_skip = blind_type in {"SMALL", "BIG"}
    action_name = (
        SKIP_BLIND
        if can_skip and margin >= normalized_threshold
        else SELECT_BLIND
    )

    return BlindSkipDecision(
        action_name=action_name,
        blind_type=blind_type,
        play_ev=play_ev,
        tag_ev=tag_ev,
        economy_opportunity_cost=economy_opportunity_cost,
        skip_ev=skip_ev,
        margin=margin,
        threshold=normalized_threshold,
        tag_value_source=tag_value_source,
        tag_key=tag_key,
    )
