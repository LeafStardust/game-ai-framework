from __future__ import annotations

from dataclasses import dataclass

from games.balatro.actions import SELECT_BLIND, SKIP_BLIND


DEFAULT_BLIND_SKIP_THRESHOLD = 2.0
DEFAULT_FALLBACK_TAG_VALUE = 4.0


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

    @property
    def notes(self) -> tuple[str, ...]:
        decision = "SKIP" if self.action_name == SKIP_BLIND else "PLAY"
        return (
            f"blind_decision={decision}",
            f"blind_type={self.blind_type}",
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


def decide_blind_play_or_skip(
    snapshot,
    *,
    threshold: float = DEFAULT_BLIND_SKIP_THRESHOLD,
    fallback_tag_value: float = DEFAULT_FALLBACK_TAG_VALUE,
) -> BlindSkipDecision:
    """Score playing the visible blind against skipping for its unknown live tag.

    Process-memory observation currently exposes the blind tier but not the selected
    blind's tag identity. Until that public field is surfaced, tag EV is explicitly a
    configurable fallback rather than a fabricated tag-specific value.
    """
    payload = snapshot.payload if isinstance(snapshot.payload, dict) else {}
    blind = payload.get("blind")
    blind = blind if isinstance(blind, dict) else {}
    blind_type = str(blind.get("type") or "UNKNOWN").upper()

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
    tag_ev = max(0.0, float(fallback_tag_value))
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
        tag_value_source="fallback_unidentified_live_tag",
    )
