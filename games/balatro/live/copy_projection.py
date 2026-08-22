from __future__ import annotations


COPY_JOKER_CLASS_NAMES = frozenset(
    {
        "BlueprintJoker",
        "BrainstormJoker",
    }
)

# Validated copier targets whose score projection is side-effect safe.  The
# original list only covered Jokers that resolve through the generic HAND_SCORED
# path.  That made Blueprint/Brainstorm look inert when copying card-scored or
# held-card payoffs such as Photograph, even though the live scorer models those
# effects explicitly.  Keep this list conservative, but include every pure
# CARD_SCORED / HELD_CARD payoff currently owned by BalatroScorer. Random or
# otherwise not independently validated targets must remain excluded so copy
# projection fails closed rather than silently claiming exactness.
INDEPENDENT_COPY_TARGET_CLASS_NAMES = frozenset(
    {
        "AbstractJoker",
        "AncientJoker",
        "ArrowheadJoker",
        "BaronJoker",
        "BurntJoker",
        "CavendishJoker",
        "EightBallJoker",
        "EvenStevenJoker",
        "FibonacciJoker",
        "FlatMultJoker",
        "GlassJoker",
        "GluttonousJoker",
        "GreedyJoker",
        "JollyJoker",
        "LustyJoker",
        "MatadorJoker",
        "MisprintJoker",
        "OddToddJoker",
        "OnyxAgateJoker",
        "PhotographJoker",
        "RaisedFistJoker",
        "ScaryFaceJoker",
        "ScholarJoker",
        "SeanceJoker",
        "ShootTheMoonJoker",
        "SmileyFaceJoker",
        "StuntmanJoker",
        "SuperpositionJoker",
        "TheIdolJoker",
        "ToDoListJoker",
        "TribouletJoker",
        "VagabondJoker",
        "WalkieTalkieJoker",
        "WeeJoker",
        "WrathfulJoker",
    }
)

_COPY_METADATA_FIELDS = (
    "live_id",
    "area_index",
    "center",
    "label",
    "rarity",
    "edition",
    "cost",
    "sell_cost",
)


class ProjectedIndependentCopyJoker:
    """Delegate one copied effect while retaining the copier's metadata."""

    def __init__(self, copier, target):
        self._target = target
        for field in _COPY_METADATA_FIELDS:
            if hasattr(copier, field):
                setattr(self, field, getattr(copier, field))

    def apply(self, context):
        return self._target.apply(context)


_PROJECTED_PROXY_TYPES: dict[str, type] = {}


def _projected_copy_proxy(copier, target):
    """Return a proxy dispatched through the target's scorer trigger family.

    BalatroScorer intentionally dispatches CARD_SCORED and HELD_CARD effects by
    Joker class name.  A generic proxy therefore suppresses copied Photograph,
    Baron, Odd Todd, etc.  The ephemeral proxy keeps the *target* class name for
    trigger dispatch while retaining Blueprint/Brainstorm metadata and delegating
    only the target ability through ``apply``.
    """

    class_name = type(target).__name__
    proxy_type = _PROJECTED_PROXY_TYPES.get(class_name)
    if proxy_type is None:
        proxy_type = type(class_name, (ProjectedIndependentCopyJoker,), {})
        _PROJECTED_PROXY_TYPES[class_name] = proxy_type
    return proxy_type(copier, target)


def resolve_copy_target(joker, state) -> tuple[object | None, bool]:
    """Resolve Blueprint/Brainstorm chains from current Joker order.

    Returns ``(None, True)`` when the copier legitimately has no effect (for
    example a rightmost Blueprint or leftmost Brainstorm). Cycles return
    ``(None, False)`` so projection fails closed rather than guessing. A Joker
    currently disabled by Crimson Heart has no active ability to copy.
    """

    if bool(getattr(joker, "debuffed", False)):
        return None, True
    return _resolve_copy_target(joker, state, seen=set())


def _resolve_copy_target(joker, state, *, seen: set[int]):
    marker = id(joker)
    if marker in seen:
        return None, False

    seen = set(seen)
    seen.add(marker)
    jokers = list(getattr(state, "jokers", []) or [])
    class_name = type(joker).__name__

    if class_name == "BlueprintJoker":
        try:
            index = jokers.index(joker)
        except ValueError:
            return None, False
        if index + 1 >= len(jokers):
            return None, True
        candidate = jokers[index + 1]
    elif class_name == "BrainstormJoker":
        if not jokers:
            return None, True
        candidate = jokers[0]
        if candidate is joker:
            return None, True
    else:
        return joker, True

    if bool(getattr(candidate, "debuffed", False)):
        return None, True
    if id(candidate) in seen:
        return None, False
    if type(candidate).__name__ in COPY_JOKER_CLASS_NAMES:
        return _resolve_copy_target(candidate, state, seen=seen)
    return candidate, True


def project_independent_copy_jokers(jokers, state) -> list:
    """Replace validated copy Jokers with scorer-only delegating proxies."""

    projected = []
    for joker in jokers:
        if type(joker).__name__ not in COPY_JOKER_CLASS_NAMES:
            projected.append(joker)
            continue

        target, resolvable = resolve_copy_target(joker, state)
        if not resolvable or target is None:
            projected.append(joker)
            continue

        projected.append(_projected_copy_proxy(joker, target))

    return projected
