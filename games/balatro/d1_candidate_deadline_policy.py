from __future__ import annotations

"""Compatibility shim for the former D1 candidate-deadline monkeypatch.

Candidate-generation hard deadline checks and the bounded initial-root bootstrap now
live directly in ``LiveBlindClearPlanner``. Keep this module only so historical
imports do not fail; it must not install a second ``_candidate_actions`` authority.
"""

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


ROOT_BOOTSTRAP_SECONDS = LiveBlindClearPlanner.ROOT_CANDIDATE_BOOTSTRAP_SECONDS


def install_d1_candidate_deadline_policy() -> None:
    """No-op: deadline authority is canonical in ``LiveBlindClearPlanner``."""
    return None
