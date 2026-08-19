from __future__ import annotations

"""Primary-win-condition plus compatible-engine strategy orchestration.

The universal strategy catalogue contains both actual win conditions and useful
engines.  Treating every positive node as a mutually-exclusive build causes support
engines to hijack the run, especially after the old Ante-6 convergence boundary.
This layer keeps one primary scoring direction while allowing compatible secondary
and support engines to remain prescriptive.
"""

from games.balatro.strategy import BANNED, AVAILABLE, BalatroStrategyTracker

PRIMARY = "PRIMARY"
SECONDARY = "SECONDARY"
SUPPORT = "SUPPORT"

# These nodes improve a build but normally do not specify enough scoring structure
# to be the sole strategic destination. SECONDARY nodes may become the fallback
# primary when no true primary has positive evidence, but otherwise ride alongside
# the primary route. SUPPORT nodes never displace a positive primary/secondary.
SECONDARY_STRATEGIES = frozenset({
    "drivers_license",
    "blue_seal",
    "gold_seal",
    "red_seal",
    "purple_seal",
    "hiker_training",
    "planet_engine",
    "planet_constellation",
    "planet_satellite",
    "planet_constellation_satellite",
    "tarot_engine",
    "tarot_cartomancer",
    "tarot_hallucination",
    "tarot_eight_ball",
    "cash_hoard",
    "cash_growth",
    "cash_cloud_nine",
    "discard_utilization",
    "discard_castle",
    "discard_mail_rebate",
    "no_discard",
    "no_discard_reserve",
    "no_discard_ramen",
    "loyalty_cycle",
})

SUPPORT_STRATEGIES = frozenset({
    "face_held_economy",
    "face_business_card",
    "faceless_discard_economy",
    "deck_thinning",
    "thinning_trading",
    "thinning_erosion",
    "thinning_trading_erosion",
    "abstract_joker",
    "swashbuckler",
    "raised_fist",
    "flower_pot",
    "last_hand_burst",
    "last_hand_acrobat",
})


def strategy_role(strategy_id: str | None) -> str:
    if strategy_id in SUPPORT_STRATEGIES:
        return SUPPORT
    if strategy_id in SECONDARY_STRATEGIES:
        return SECONDARY
    return PRIMARY


def _positive_tokens(definition) -> frozenset[str]:
    return frozenset(
        set(getattr(definition, "gold_jokers", ()))
        | set(getattr(definition, "silver_jokers", ()))
        | set(getattr(definition, "bronze_jokers", ()))
    )


def _compatible(tracker: BalatroStrategyTracker, primary_id: str, other_id: str) -> bool:
    """Reject explicit catalogue conflicts and competing poker-hand prescriptions."""
    if primary_id == other_id:
        return True
    primary_defs = tuple(tracker.definitions_for_path(primary_id))
    other_defs = tuple(tracker.definitions_for_path(other_id))
    if not primary_defs or not other_defs:
        return True

    primary_positive = frozenset().union(*(_positive_tokens(d) for d in primary_defs))
    other_positive = frozenset().union(*(_positive_tokens(d) for d in other_defs))
    primary_bans = frozenset().union(*(getattr(d, "banned_jokers", frozenset()) for d in primary_defs))
    other_bans = frozenset().union(*(getattr(d, "banned_jokers", frozenset()) for d in other_defs))
    if primary_bans & other_positive or other_bans & primary_positive:
        return False

    primary_hands = set(tracker.primary_hands_for(primary_id))
    other_hands = set(tracker.primary_hands_for(other_id))
    if primary_hands and other_hands and primary_hands.isdisjoint(other_hands):
        # Two distinct hand prescriptions compete for hand/deck shaping. They may
        # coexist as diagnostics before a pivot, but not as simultaneous engines.
        return False
    return True


def primary_strategy_id(tracker: BalatroStrategyTracker, resolution) -> str | None:
    positive = [a for a in resolution.assessments if float(a.score) > 0.0]
    true_primary = next((a for a in positive if strategy_role(a.strategy_id) == PRIMARY), None)
    if true_primary is not None:
        return true_primary.strategy_id
    secondary = next((a for a in positive if strategy_role(a.strategy_id) == SECONDARY), None)
    if secondary is not None:
        return secondary.strategy_id
    return positive[0].strategy_id if positive else None


def active_engine_ids(tracker: BalatroStrategyTracker, resolution) -> tuple[str, ...]:
    primary_id = primary_strategy_id(tracker, resolution)
    if primary_id is None:
        return ()
    config = tracker._config(None) if False else None  # keep policy config-free by default
    engines: list[str] = []
    for assessment in resolution.assessments:
        strategy_id = assessment.strategy_id
        if strategy_id == primary_id or float(assessment.score) <= 0.0:
            continue
        if strategy_role(strategy_id) == PRIMARY:
            continue
        if assessment.status == AVAILABLE and float(assessment.score) < 1.0:
            continue
        if not _compatible(tracker, primary_id, strategy_id):
            continue
        engines.append(strategy_id)
        if len(engines) >= 3:
            break
    return tuple(engines)


def prescriptive_strategy_ids(tracker: BalatroStrategyTracker, resolution) -> tuple[str, ...]:
    primary_id = primary_strategy_id(tracker, resolution)
    if primary_id is None:
        return ()
    return (primary_id, *active_engine_ids(tracker, resolution))


def install_multi_engine_strategy_policy() -> None:
    """Teach existing consumers to keep compatible engines alive after Ante 6.

    This is deliberately additive/backward-compatible: StrategyResolution keeps its
    existing public fields for monitor/tests, while the tracker gains explicit
    primary/engine helpers and its scope/hand-fit behavior uses them.
    """
    if getattr(BalatroStrategyTracker, "_multi_engine_policy_installed", False):
        return

    BalatroStrategyTracker.strategy_role = lambda self, strategy_id: strategy_role(strategy_id)
    BalatroStrategyTracker.primary_strategy_id = lambda self, resolution: primary_strategy_id(self, resolution)
    BalatroStrategyTracker.active_engine_ids = lambda self, resolution: active_engine_ids(self, resolution)
    BalatroStrategyTracker.prescriptive_strategy_ids = lambda self, resolution: prescriptive_strategy_ids(self, resolution)

    original_scope_factor = BalatroStrategyTracker._scope_factor
    original_hand_fit = BalatroStrategyTracker.hand_fit

    def _scope_factor(self, state, strategy_id, rank, resolution):
        ante = max(1, int(getattr(state, "ante", 1) or 1))
        if ante < 6:
            return original_scope_factor(self, state, strategy_id, rank, resolution)
        prescriptive = self.prescriptive_strategy_ids(resolution)
        if strategy_id not in prescriptive:
            return 0.0
        if strategy_id == self.primary_strategy_id(resolution):
            return 1.0
        # Compatible engines remain meaningful but cannot outweigh the primary
        # scoring route merely because they have a large raw evidence score.
        role = self.strategy_role(strategy_id)
        return 0.65 if role == SECONDARY else 0.40

    def hand_fit(self, state, hand_type):
        resolution = self.observe(state)
        primary_id = self.primary_strategy_id(resolution)
        if primary_id is None:
            return 0.0, ("no positive universal strategy evidence",)

        hand_type = str(hand_type).upper()
        pressure = self.strategy_pressure(state)
        prescriptive = self.prescriptive_strategy_ids(resolution)
        mapped = False
        for index, strategy_id in enumerate(prescriptive):
            hands = tuple(self.primary_hands_for(strategy_id))
            if not hands:
                continue
            mapped = True
            if hand_type in hands:
                strength = 1.0 if index == 0 else 0.45
                definition = self.definitions.get(strategy_id)
                name = definition.name if definition is not None else strategy_id
                return strength * pressure * self.effectiveness(state, strategy_id), (
                    f"{hand_type} reinforces {'primary' if index == 0 else 'compatible engine'} strategy {name}",
                )
        if not mapped:
            return 0.0, ("active primary/engine strategies do not prescribe a poker-hand type",)
        return -0.25 * pressure, (
            f"{hand_type} does not reinforce the active primary scoring route",
        )

    BalatroStrategyTracker._scope_factor = _scope_factor
    BalatroStrategyTracker.hand_fit = hand_fit
    BalatroStrategyTracker._multi_engine_policy_installed = True
