from types import SimpleNamespace

from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.playbook_joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.state import BalatroState


class _AlignedPlanner:
    def plan(self, state, candidate):
        return SimpleNamespace(
            candidate_value=SimpleNamespace(
                total_gain=1.6,
                active_alignment=True,
                strategy_tier="SILVER",
            ),
            alternatives=(),
        )


def test_aligned_joker_can_fill_last_free_slot_when_slot_penalty_is_only_blocker():
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.jokers = [object(), object(), object(), object()]
    state.joker_slots = 5

    decision = PlaybookJokerAcquisitionPolicy(_AlignedPlanner()).decide(
        state,
        JollyJoker(),
    )

    assert decision.action == "BUY"
    assert decision.selected is not None
    assert decision.selected.economics.slot_penalty > 0.0
    assert any("final free slot" in note for note in decision.rationale)
