from __future__ import annotations

"""Hard runtime bound for real visible-Joker whole-build scoring probes.

D2 remains authoritative for visible Joker acquisition/replacement, but its literal
whole-build evaluator must not scale as ``11 poker hands × every incumbent slot ×
multiple shop candidates``.  This module only bounds the representative scoring
probe set.  It does not bypass D2, replacement comparison, Bond projection,
economics, slot legality, or native execution guards.

When public hand-play history exists, the bounded set prefers hands the current run
actually plays.  Otherwise the original deterministic probe order is retained.
A full Joker roster is the expensive replacement case and receives one scoring
probe per build-value evaluation; a roster with room to add receives at most three.
"""

from .joker_strategy import JokerBuildValueEvaluator


MAX_FREE_SLOT_SCORING_PROBES = 3
MAX_REPLACEMENT_SCORING_PROBES = 1
_INSTALLED_ATTR = "_bounded_visible_joker_scoring_probes_installed"


def _probe_budget(state) -> int:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    try:
        slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    except (TypeError, ValueError):
        slots = 0
    if slots > 0 and len(jokers) >= slots:
        return MAX_REPLACEMENT_SCORING_PROBES
    return MAX_FREE_SLOT_SCORING_PROBES


def _bounded_scoring_probes(self: JokerBuildValueEvaluator, state):
    probes = tuple(self.PROBES)
    if not probes:
        return ()

    budget = min(len(probes), _probe_budget(state))
    observed = self._probe_weights(state)
    if not observed:
        return probes[:budget]

    indexed = tuple(enumerate(probes))
    ranked = sorted(
        indexed,
        key=lambda item: (
            -float(observed.get(self._hand_key(item[1][0].value), 0.0)),
            item[0],
        ),
    )
    return tuple(probe for _, probe in ranked[:budget])


def install_visible_joker_scoring_probe_bound() -> None:
    if getattr(JokerBuildValueEvaluator, _INSTALLED_ATTR, False):
        return
    JokerBuildValueEvaluator._scoring_probes = _bounded_scoring_probes
    setattr(JokerBuildValueEvaluator, _INSTALLED_ATTR, True)
