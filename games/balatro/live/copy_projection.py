from __future__ import annotations


COPY_JOKER_CLASS_NAMES = frozenset(
    {
        "BlueprintJoker",
        "BrainstormJoker",
    }
)

# Validated copier targets whose scoring-time delegation is side-effect safe.
# Burnt Joker is included because its copied ability activates on discard, so
# delegating it during score projection is intentionally a no-op; discard-time
# copy activation is handled by LiveDiscardJokerProjector. The generated-
# consumable Jokers below expose only deterministic signals during scoring; their
# actual Tarot/Spectral state transition is owned by the live outcome projector.
INDEPENDENT_COPY_TARGET_CLASS_NAMES = frozenset(
    {
        "AbstractJoker",
        "BurntJoker",
        "CavendishJoker",
        "EightBallJoker",
        "FlatMultJoker",
        "GlassJoker",
        "JollyJoker",
        "MatadorJoker",
        "MisprintJoker",
        "SeanceJoker",
        "StuntmanJoker",
        "SuperpositionJoker",
        "ToDoListJoker",
        "VagabondJoker",
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
    """Delegate one independent effect while retaining copier metadata.

    Blueprint/Brainstorm copy the target Joker's compatible ability, not the
    target's Edition, rarity, stickers or identity. The scorer therefore sees
    the copier's metadata for edition/Baseball ordering while ``apply`` delegates
    only the validated independent scoring effect to the resolved target.
    """

    def __init__(self, copier, target):
        self._target = target
        for field in _COPY_METADATA_FIELDS:
            if hasattr(copier, field):
                setattr(self, field, getattr(copier, field))

    def apply(self, context):
        return self._target.apply(context)


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

        projected.append(ProjectedIndependentCopyJoker(joker, target))

    return projected
