from games.balatro.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live_competence_guard_policy import install_live_competence_guard_policy


def test_live_competence_guard_does_not_wrap_canonical_d2_joker_admission(monkeypatch):
    def canonical_d2(self, state, candidate):
        return "canonical-d2-result"

    monkeypatch.setattr(PlaybookJokerAcquisitionPolicy, "decide", canonical_d2)
    monkeypatch.delattr(
        LiveBlindClearPlanner,
        "_rw_live_competence_guard_installed",
        raising=False,
    )

    install_live_competence_guard_policy()

    assert PlaybookJokerAcquisitionPolicy.decide is canonical_d2
