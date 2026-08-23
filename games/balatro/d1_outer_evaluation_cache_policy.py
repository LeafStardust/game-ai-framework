from __future__ import annotations

"""Memoize repeated top-level D1 evaluations for one immutable live state.

Live validation showed adaptive search itself completing inside its budget while the
surrounding PACE_RECOVERY stack spent many extra seconds re-evaluating the same play
and discard actions. The worst offender was discard valuation: every discard called
``_has_guaranteed_clearing_play`` which rescanned and rescored every playable subset.

The live translator supplies a fresh state object at each authoritative checkpoint,
and the existing decision evaluator already caches context by ``id(state)``. This
policy follows that same state-identity contract and keeps only the current state's
memoized values. No search ranking or scoring semantics are changed.
"""

from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


def _action_key(action) -> tuple[str, tuple[int, ...]]:
    cards = tuple(getattr(action, "cards", ()) or ())
    return (
        str(getattr(action, "name", "")),
        tuple(id(card) for card in cards),
    )


def _ensure_state_cache(evaluator: LiveHandDecisionEvaluator, state) -> None:
    state_id = id(state)
    if getattr(evaluator, "_outer_d1_cache_state_id", None) == state_id:
        return
    evaluator._outer_d1_cache_state_id = state_id
    evaluator._outer_d1_projection_cache = {}
    evaluator._outer_d1_evaluation_cache = {}
    evaluator._outer_d1_guaranteed_clear_cached = False
    evaluator._outer_d1_guaranteed_clear_value = False


def install_d1_outer_evaluation_cache_policy() -> None:
    if getattr(LiveHandDecisionEvaluator, "_outer_d1_cache_installed", False):
        return

    original_project_play = LiveHandDecisionEvaluator.project_play
    original_evaluate = LiveHandDecisionEvaluator.evaluate
    original_has_guaranteed = LiveHandDecisionEvaluator._has_guaranteed_clearing_play

    def project_play(self, state, action):
        _ensure_state_cache(self, state)
        key = _action_key(action)
        cache = self._outer_d1_projection_cache
        if key not in cache:
            cache[key] = original_project_play(self, state, action)
        return cache[key]

    def evaluate(self, state, action):
        _ensure_state_cache(self, state)
        key = _action_key(action)
        cache = self._outer_d1_evaluation_cache
        if key not in cache:
            cache[key] = original_evaluate(self, state, action)
        return cache[key]

    def has_guaranteed_clearing_play(self, state):
        _ensure_state_cache(self, state)
        if not self._outer_d1_guaranteed_clear_cached:
            self._outer_d1_guaranteed_clear_value = bool(
                original_has_guaranteed(self, state)
            )
            self._outer_d1_guaranteed_clear_cached = True
        return self._outer_d1_guaranteed_clear_value

    LiveHandDecisionEvaluator.project_play = project_play
    LiveHandDecisionEvaluator.evaluate = evaluate
    LiveHandDecisionEvaluator._has_guaranteed_clearing_play = has_guaranteed_clearing_play
    LiveHandDecisionEvaluator._outer_d1_cache_installed = True
