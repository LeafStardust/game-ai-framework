from __future__ import annotations

"""Final live authority for Joker ordering.

The standalone JokerOrderPolicy predates the current autonomous runner and can be
silently bypassed when the runner never asks it for an action.  This patch restores
ordering as a stable-checkpoint invariant and hardens two mechanical rules that
must not depend on approximate score projection:

* Blueprint must have a useful Joker immediately to its right when one exists.
* Brainstorm must have a useful leftmost Joker when one exists.

Ordinary XMult Jokers are also recognized from public identity when a dynamic
``x_mult`` field is not exposed, preserving the established additive-Mult-before-
XMult ordering tie-break.  BLIND_SELECT remains owned by the existing Ceremonial
Dagger pre-blind ordering logic.
"""

from time import perf_counter

from games.balatro.joker_order_policy import JokerOrderPolicy


_COPY_NAMES = frozenset({"blueprint", "blueprintjoker", "brainstorm", "brainstormjoker"})
_XMULT_NAMES = frozenset(
    {
        "acrobat", "acrobatjoker",
        "blackboard", "blackboardjoker",
        "campfire", "campfirejoker",
        "cardsharp", "cardsharpjoker",
        "cavendish", "cavendishjoker",
        "constellation", "constellationjoker",
        "driverslicense", "driverslicensejoker",
        "flowerpot", "flowerpotjoker",
        "glassjoker",
        "hologram", "hologramjoker",
        "hittheroad", "hittheroadjoker",
        "jokerstencil",
        "luckycat", "luckycatjoker",
        "madness", "madnessjoker",
        "obelisk", "obeliskjoker",
        "ramen", "ramenjoker",
        "seeingdouble", "seeingdoublejoker",
        "steeljoker",
        "theduo", "theduojoker",
        "thefamily", "thefamilyjoker",
        "theorder", "theorderjoker",
        "thetribe", "thetribejoker",
        "thetrio", "thetriojoker",
        "vampire", "vampirejoker",
        "yorick", "yorickjoker",
    }
)


def _token(value: object) -> str:
    raw = (
        getattr(value, "center", None)
        or getattr(value, "name", None)
        or getattr(value, "label", None)
        or type(value).__name__
    )
    return "".join(ch for ch in str(raw).lower() if ch.isalnum())


def _is_blueprint(joker: object) -> bool:
    return _token(joker) in {"blueprint", "blueprintjoker"}


def _is_brainstorm(joker: object) -> bool:
    return _token(joker) in {"brainstorm", "brainstormjoker"}


def _is_copy_joker(joker: object) -> bool:
    return _token(joker) in _COPY_NAMES


def _copy_order_violations(jokers, permutation: tuple[int, ...]) -> tuple[str, ...]:
    """Return mechanically dead copy placements for a resolved permutation.

    Copy-on-copy chains are treated as inferior whenever a concrete non-copy target
    is available.  If the roster contains only copy Jokers there is no useful target
    to enforce, so the ordering layer leaves the score projector in control.
    """

    ordered = tuple(jokers[index] for index in permutation)
    if not any(not _is_copy_joker(joker) for joker in ordered):
        return ()

    violations: list[str] = []
    for index, joker in enumerate(ordered):
        if _is_blueprint(joker):
            if index + 1 >= len(ordered):
                violations.append("Blueprint has no Joker immediately to its right")
            elif _is_copy_joker(ordered[index + 1]):
                violations.append("Blueprint targets another copy Joker despite a concrete target")
        elif _is_brainstorm(joker):
            if not ordered or ordered[0] is joker:
                violations.append("Brainstorm is leftmost and therefore has no concrete leftmost target")
            elif _is_copy_joker(ordered[0]):
                violations.append("Brainstorm targets another copy Joker despite a concrete target")
    return tuple(violations)


def _identity_xmult_factor(joker: object) -> float:
    """Recognize active/main Joker XMult even when public state omits ``x_mult``."""

    public = getattr(joker, "public_state", None)
    values = [
        getattr(joker, "x_mult", None),
        getattr(joker, "xmult", None),
        getattr(joker, "x_mult_mod", None),
    ]
    if isinstance(public, dict):
        values.extend(
            (
                public.get("x_mult"),
                public.get("xmult"),
                public.get("x_mult_mod"),
            )
        )
    for value in values:
        try:
            factor = float(value)
        except (TypeError, ValueError):
            continue
        if factor > 1.0:
            return factor

    # Identity is used only as an ordering tie-break when the exact live multiplier
    # is not exposed.  A neutral >1 marker is sufficient and does not alter scoring.
    return 1.5 if _token(joker) in _XMULT_NAMES else 1.0


def install_live_joker_order_authority() -> None:
    if getattr(JokerOrderPolicy, "_live_order_authority_installed", False):
        return

    original_score = JokerOrderPolicy._score
    original_xmult_factor = JokerOrderPolicy._xmult_factor

    def score_with_copy_constraints(self, state, permutation, *, phase: str):
        score, notes = original_score(self, state, permutation, phase=phase)
        # BLIND_SELECT is intentionally left to the existing Dagger sacrifice logic.
        if phase != "BLIND_SELECT":
            violations = _copy_order_violations(tuple(getattr(state, "jokers", ()) or ()), tuple(permutation))
            if violations:
                return float("-inf"), (*notes, *violations)
        return score, notes

    @staticmethod
    def xmult_factor_with_identity(joker: object) -> float:
        factor = original_xmult_factor(joker)
        if factor > 1.0:
            return factor
        return _identity_xmult_factor(joker)

    JokerOrderPolicy._score = score_with_copy_constraints
    JokerOrderPolicy._xmult_factor = xmult_factor_with_identity
    JokerOrderPolicy._live_order_authority_installed = True

    # Import lazily so package installation does not create a hard import cycle.
    from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
        AutonomousStepDecision,
        LiveMemoryInjectedSingleStepRunner,
    )

    if getattr(LiveMemoryInjectedSingleStepRunner, "_joker_order_authority_installed", False):
        return

    original_init = LiveMemoryInjectedSingleStepRunner.__init__
    original_decide = LiveMemoryInjectedSingleStepRunner.decide

    def init_with_joker_order(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.joker_order_policy = JokerOrderPolicy()

    def decide_with_joker_order(self):
        started = perf_counter()
        snapshot = self.observer.observe()
        observation_seconds = perf_counter() - started

        if snapshot.state_complete and str(snapshot.phase) in JokerOrderPolicy.STABLE_PHASES:
            translated_started = perf_counter()
            state = self.translator.translate(snapshot)
            translation_seconds = perf_counter() - translated_started
            policy_started = perf_counter()
            ordering = self.joker_order_policy.recommend(state, phase=str(snapshot.phase))
            policy_seconds = perf_counter() - policy_started
            if ordering is not None:
                self.last_observation_seconds = observation_seconds
                self.last_translation_seconds = translation_seconds
                self.last_policy_seconds = policy_seconds
                return AutonomousStepDecision(
                    snapshot=snapshot,
                    state=state,
                    action=ordering.to_action(),
                    source="Joker ordering invariant",
                    notes=ordering.rationale,
                )

        # No ordering correction is needed.  Let the canonical decision path make a
        # fresh observation rather than reusing a potentially aging checkpoint.
        return original_decide(self)

    LiveMemoryInjectedSingleStepRunner.__init__ = init_with_joker_order
    LiveMemoryInjectedSingleStepRunner.decide = decide_with_joker_order
    LiveMemoryInjectedSingleStepRunner._joker_order_authority_installed = True
