from __future__ import annotations

"""Keep Judgement fail-closed until its random Joker pool is modeled exactly.

The shared pack policy deliberately defers Judgement because the repository does not
currently expose an authoritative eligible-Joker generation pool/distribution.  The
Red/White cartridge historically overrode that guard with a fixed ``5.0`` plus an
empty-slot bonus.  That number is neither literal Balatro value nor an expectation
from public outcomes, so it must not compete with visible pack choices.

This guard restores the shared deferred semantics without guessing unlocked Joker
rarities, duplicate eligibility, dynamic constructor state, or hidden RNG.
"""

from games.balatro.actions import SKIP_BOOSTER
from games.balatro.pack_policy import BalatroPackPolicy
from games.balatro.playbook.red_white.pack_policy import PlaybookBalatroPackPolicy


JUDGEMENT = "Judgement"


def install_judgement_pack_expectation_guard() -> None:
    if getattr(
        PlaybookBalatroPackPolicy,
        "_judgement_expectation_guard_installed",
        False,
    ):
        return

    original_score_action = PlaybookBalatroPackPolicy.score_action

    def score_action(self, state, action):
        if action.name != SKIP_BOOSTER:
            choice = getattr(action, "target", None)
            if (
                getattr(choice, "kind", None) == "TAROT"
                and getattr(choice, "label", None) == JUDGEMENT
            ):
                # Bypass the Red/White fixed option-value override and delegate to
                # the shared policy.  Its STOCHASTIC_DEFERRED_TAROTS contract keeps
                # Judgement below Skip until a complete public outcome model exists.
                return BalatroPackPolicy.score_action(self, state, action)
        return original_score_action(self, state, action)

    PlaybookBalatroPackPolicy.score_action = score_action
    PlaybookBalatroPackPolicy._judgement_expectation_guard_installed = True
