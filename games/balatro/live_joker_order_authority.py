from __future__ import annotations

"""Final live authority for Joker ordering.

The standalone JokerOrderPolicy predates the current autonomous runner and can be
silently bypassed when the runner never asks it for an action. This patch restores
ordering as a stable-checkpoint invariant and hardens mechanical rules that must
not depend on approximate score projection:

* Blueprint may not occupy the final slot when another Joker exists.
* Brainstorm may not occupy the leftmost slot when another Joker exists.
* Polychrome edition contributes its real x1.5 XMult to right-alignment.

Copy-to-copy chains remain legal because Blueprint/Brainstorm chains can be useful.
Ordinary XMult Jokers are also recognized from public identity when a dynamic
``x_mult`` field is not exposed, preserving the established additive-Mult-before-
XMult ordering tie-break. BLIND_SELECT remains owned by the existing Ceremonial
Dagger pre-blind ordering logic.
"""

from time import perf_counter

from games.balatro.actions import PLAY_CARDS
from games.balatro.joker_order_policy import JokerOrderPolicy


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


def _edition_token(joker: object) -> str:
    edition = getattr(joker, "edition", None)
    if isinstance(edition, dict):
        edition = next((name for name, enabled in edition.items() if bool(enabled)), "")
    if not edition:
        public = getattr(joker, "public_state", None)
        if isinstance(public, dict):
            edition = public.get("edition")
            if isinstance(edition, dict):
                edition = next((name for name, enabled in edition.items() if bool(enabled)), "")
    return "".join(ch for ch in str(edition or "").lower() if ch.isalnum())


def _is_blueprint(joker: object) -> bool:
    return _token(joker) in {"blueprint", "blueprintjoker"}


def _is_brainstorm(joker: object) -> bool:
    return _token(joker) in {"brainstorm", "brainstormjoker"}


def _copy_order_violations(jokers, permutation: tuple[int, ...]) -> tuple[str, ...]:
    ordered = tuple(jokers[index] for index in permutation)
    if len(ordered) < 2:
        return ()
    violations: list[str] = []
    for index, joker in enumerate(ordered):
        if _is_blueprint(joker) and index == len(ordered) - 1:
            violations.append("Blueprint has no Joker immediately to its right")
        if _is_brainstorm(joker) and index == 0:
            violations.append("Brainstorm is leftmost and therefore has no leftmost target")
    return tuple(violations)


def _identity_xmult_factor(joker: object) -> float:
    public = getattr(joker, "public_state", None)
    values = [
        getattr(joker, "x_mult", None),
        getattr(joker, "xmult", None),
        getattr(joker, "x_mult_mod", None),
    ]
    if isinstance(public, dict):
        values.extend((public.get("x_mult"), public.get("xmult"), public.get("x_mult_mod")))
    for value in values:
        try:
            factor = float(value)
        except (TypeError, ValueError):
            continue
        if factor > 1.0:
            return factor

    # Polychrome is always x1.5 Mult regardless of the Joker's native effect.
    if _edition_token(joker) == "polychrome":
        return 1.5

    return 1.5 if _token(joker) in _XMULT_NAMES else 1.0


class _ReplayObserver:
    def __init__(self, delegate, snapshot) -> None:
        self._delegate = delegate
        self._snapshot = snapshot
        self._used = False

    def observe(self):
        if not self._used:
            self._used = True
            return self._snapshot
        return self._delegate.observe()

    def __getattr__(self, name):
        return getattr(self._delegate, name)


def install_live_joker_order_authority() -> None:
    if getattr(JokerOrderPolicy, "_live_order_authority_installed", False):
        return

    original_score = JokerOrderPolicy._score
    original_xmult_factor = JokerOrderPolicy._xmult_factor

    def score_with_copy_constraints(self, state, permutation, *, phase: str):
        score, notes = original_score(self, state, permutation, phase=phase)
        if phase != "BLIND_SELECT":
            violations = _copy_order_violations(tuple(getattr(state, "jokers", ()) or ()), tuple(permutation))
            if violations:
                return float("-inf"), (*notes, *violations)
        return score, notes

    @staticmethod
    def xmult_factor_with_identity(joker: object) -> float:
        factor = original_xmult_factor(joker)
        if factor > 1.0:
            return max(factor, 1.5) if _edition_token(joker) == "polychrome" else factor
        return _identity_xmult_factor(joker)

    JokerOrderPolicy._score = score_with_copy_constraints
    JokerOrderPolicy._xmult_factor = xmult_factor_with_identity
    JokerOrderPolicy._live_order_authority_installed = True

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

        phase = str(snapshot.phase)
        translated_state = None
        if snapshot.state_complete and phase in JokerOrderPolicy.STABLE_PHASES:
            translated_started = perf_counter()
            state = self.translator.translate(snapshot)
            translated_state = state
            translation_seconds = perf_counter() - translated_started
            # SHOP and pre-blind Dagger ordering do not depend on a selected hand.
            # During SELECTING_HAND, only repair an immediately invalid copy
            # position before D1; otherwise wait for D1's exact play selection.
            current = tuple(range(len(tuple(getattr(state, "jokers", ()) or ()))))
            invalid_copy_position = bool(
                _copy_order_violations(
                    tuple(getattr(state, "jokers", ()) or ()),
                    current,
                )
            )
            if phase != "SELECTING_HAND" or invalid_copy_position:
                policy_started = perf_counter()
                ordering = self.joker_order_policy.recommend(state, phase=phase)
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

        original_observer = self.observer
        self.observer = _ReplayObserver(original_observer, snapshot)
        try:
            decision = original_decide(self)
        finally:
            self.observer = original_observer

        if (
            phase == "SELECTING_HAND"
            and translated_state is not None
            and decision.action.name == PLAY_CARDS
        ):
            policy_started = perf_counter()
            ordering = self.joker_order_policy.recommend_for_play(
                decision.state,
                decision.action.cards,
            )
            policy_seconds = perf_counter() - policy_started
            if ordering is not None:
                self.last_policy_seconds = policy_seconds
                return AutonomousStepDecision(
                    snapshot=decision.snapshot,
                    state=decision.state,
                    action=ordering.to_action(),
                    source="Joker ordering invariant",
                    notes=(
                        *ordering.rationale,
                        f"deferred D1 action={decision.action.name} until reordered checkpoint",
                    ),
                    pack_signature=decision.pack_signature,
                )
        return decision

    LiveMemoryInjectedSingleStepRunner.__init__ = init_with_joker_order
    LiveMemoryInjectedSingleStepRunner.decide = decide_with_joker_order
    LiveMemoryInjectedSingleStepRunner._joker_order_authority_installed = True
