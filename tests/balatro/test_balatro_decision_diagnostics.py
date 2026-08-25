from __future__ import annotations

from games.balatro.actions import SELECT_PACK_CARD
from games.balatro.live.pack import LivePackChoice
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.bond_autonomous_runner import (
    BondAwareLiveMemoryInjectedSingleStepRunner,
)
from games.balatro.state import BalatroState


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class _Translator:
    def __init__(self, state):
        self.state = state

    def translate(self, snapshot):
        return self.state


def _choice():
    return LivePackChoice(
        area_index=0,
        address=0x1000,
        data={
            "area_index": 0,
            "address": 0x1000,
            "live_id": 501,
            "label": "Golden Joker",
            "ability_name": "Golden Joker",
            "ability_set": "Joker",
            "center": "j_golden",
        },
    )


def test_d9_decision_carries_actual_ranked_candidates_and_pack_threshold():
    snapshot = LiveBalatroSnapshot(
        sequence=7,
        phase="BUFFOON_PACK",
        state_complete=True,
        payload={},
    )
    state = BalatroState()
    state.phase = "BUFFOON_PACK"
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.joker_slots = 5
    state.jokers = []
    choice = _choice()

    runner = BondAwareLiveMemoryInjectedSingleStepRunner(
        _Observer(snapshot),
        translator=_Translator(state),
        pack_choice_reader=lambda: (choice,),
    )

    decision = runner.decide()

    assert decision.action.name == SELECT_PACK_CARD
    assert decision.source == "pack policy"
    diagnostics = decision.decision_diagnostics
    assert diagnostics is not None
    assert diagnostics["layer"] == "D9/D10"
    assert diagnostics["active_thresholds"] == {
        "pack_choice": {
            "skip_bias": runner.pack_policy.skip_bias,
        },
        "pack_target": {
            "minimum_total_gain": None,
            "minimum_contextual_delta": 0.0,
        },
    }

    # Buffoon packs with free Joker capacity intentionally suppress Skip: opening
    # the pack already spent the money, so one visible Joker must be taken rather
    # than throwing the pack away because an empty slot itself has temporary value.
    candidates = diagnostics["candidate_scores"]
    assert [candidate["action"] for candidate in candidates] == [SELECT_PACK_CARD]
    assert candidates[0]["area_index"] == 0
    assert candidates[0]["label"] == "Golden Joker"
